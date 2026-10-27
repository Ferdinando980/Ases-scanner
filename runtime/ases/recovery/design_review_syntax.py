"""Inert JS/TS/Java responsibility clues using the installed syntax parsers."""
from __future__ import annotations

from collections import defaultdict
import re

from ..scanners.javascript import EXTENSIONS, FUNCTIONS, parse as parse_js, walk
from ..scanners.java_syntax import parse as parse_java
from .design_review import _service_review, _strategy_review, _registry_review

OWNERS = FUNCTIONS | {'method_declaration', 'constructor_declaration', 'lambda_expression'}


def field(node, name):
    return node.child_by_field_name(name) if node is not None else None


def text(node):
    return node.text.decode('utf-8') if node is not None else ''


def local_walk(root):
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(c for c in reversed(node.named_children) if c.type not in OWNERS)


def owner(node):
    current = node.parent
    while current is not None and current.type not in OWNERS:
        current = current.parent
    return current


def name(node):
    if node is None: return ''
    if node.type in {'identifier','property_identifier','this'}: return text(node)
    if node.type in {'member_expression','field_access'}:
        obj = name(field(node,'object'))
        prop = field(node,'property') or field(node,'field')
        if obj and prop is not None and prop.type in {'identifier','property_identifier'}:
            return obj+'.'+text(prop)
    return ''


def call_parts(node):
    if node.type=='method_invocation':
        return name(field(node,'object')), text(field(node,'name'))
    if node.type=='call_expression':
        fn=field(node,'function')
        if fn is not None and fn.type=='member_expression':
            prop=field(fn,'property')
            if prop is not None and prop.type=='property_identifier':
                return name(field(fn,'object')),text(prop)
        if fn is not None and fn.type=='identifier': return '',text(fn)
    return '', ''


def response_call(node):
    receiver,method=call_parts(node)
    if receiver.rsplit('.',1)[-1] in {'res','response','reply','h'} and method in {'json','send','_json','sendResponse'}:
        return True
    if receiver=='ResponseEntity' and method in {'ok','badRequest','notFound'}: return True
    # Only admit explicit transport-builder chains; arbitrary receiver calls stay unknown.
    obj=field(node,'object') if node.type=='method_invocation' else field(field(node,'function'),'object')
    if obj is not None and obj.type in {'method_invocation','call_expression'}:
        base,builder=call_parts(obj)
        return (base in {'res','response','reply','ResponseEntity'} and builder in {'status','code'}
                and method in {'json','send','body'})
    return False


def choices(branch):
    if branch is None:return []
    if branch.type=='else_clause':
        branch=next(iter(branch.named_children),None)
        if branch is None:return []
    statements=branch.named_children if branch.type in {'block','statement_block'} else [branch]
    out=[]
    for statement in statements:
        rows=statement.named_children if statement.type in {'lexical_declaration','variable_declaration','local_variable_declaration'} else [statement]
        for node in rows:
            role=None;value=None
            if node.type=='return_statement':
                role='return';value=next(iter(node.named_children),None)
            elif node.type=='variable_declarator':
                continue  # Branch-local declarations do not share an output binding.
            else:
                assignment=next(iter(node.named_children),None) if node.type=='expression_statement' else node
                if assignment is not None and assignment.type=='assignment_expression':
                    target=field(assignment,'left');value=field(assignment,'right')
                    # Compound assignments have different effects; never combine them.
                    operator=field(assignment,'operator')
                    if target is not None and target.type=='identifier' and (operator is None or text(operator)=='='):
                        role=text(target)
            if value is not None and value.type=='await_expression':value=next(iter(value.named_children),None)
            if role is not None and value is not None:
                receiver,method=call_parts(value)
                if receiver and method:out.append((role,receiver,method,node.start_point[0]+1))
    return out


def finding(rule, review, evidence, positive, negative, *, observed=False):
    if observed:review['verdict']='REUSE_EXISTING'
    return dict(rule_id=rule,status='OBSERVED' if observed else 'HINT',confidence='medium' if observed else 'low',
                reason=review['problem']['en'],evidence=sorted(set(evidence)),guidance=review['simpler_alternative']['en'],
                scope='file',review=review,signals={'positive':positive,'negative':negative})


def syntax_reviews(rel,source,suffix,max_nodes):
    """Return (findings, coverage reason); absent findings never imply sound design."""
    try:
        root=parse_java(source) if suffix=='.java' else parse_js(source,suffix)
        if root.has_error:return [],'syntax_unavailable'
        nodes=[]
        for node in walk(root):
            nodes.append(node)
            if len(nodes)>max_nodes:return [],'syntax_node_limit'
    except ValueError:return [],'syntax_node_limit'
    funcs=[n for n in nodes if n.type in OWNERS]
    out=[];handlers=[]
    for fn in funcs:
        calls=[n for n in local_walk(fn) if n.type in {'call_expression','method_invocation'}]
        responses=[n for n in calls if response_call(n)]
        operations=[n for n in calls if call_parts(n)[1] in {'ingest','mutate','query','execute','applyMutation','runQuery'}]
        persistence=[n for n in calls if call_parts(n)[1] in {'save','commit','persist'} or call_parts(n)[1].startswith(('persist_','persistMutation','persistIngest'))]
        if responses and operations and persistence:
            handlers.append((fn,[f'{rel}:{n.start_point[0]+1}' for n in responses+operations+persistence]))
        selected=[]
        for node in local_walk(fn):
            if node.type!='if_statement':continue
            condition=field(node,'condition')
            if condition is None:continue
            selectors={text(n) for n in local_walk(condition) if n.type in {'identifier','property_identifier'} }
            if not selectors & {'provider','backend','extractor_provider','extractorProvider','engine'}:continue
            for a in choices(field(node,'consequence')):
                for b in choices(field(node,'alternative')):
                    if a[:2]==b[:2] and a[2]!=b[2]:selected.extend([a,b])
        if selected:
            out.append(finding('review.strategy_variants',_strategy_review(),[f'{rel}:{s[3]}' for s in selected],
                ['syntax-local method alternatives with shared receiver and output role'],
                ['semantic equivalence, change pressure and benefit unverified']))
    if len(handlers)>=2:
        out.append(finding('review.service_responsibilities',_service_review(len(handlers)),
            [e for _,ev in handlers for e in ev], [f'{len(handlers)} transport/application/persistence mixtures'],
            ['roles partly name-based; duplicated use case and refactoring benefit unverified']))

    # Bind JS loader names only to unique top-level function definitions.
    definitions=defaultdict(list);rebound=set()
    for node in nodes:
        if node.type=='import_statement':
            rebound.update(text(n) for n in walk(node) if n.type=='identifier')
        if node.type in {'assignment_expression','augmented_assignment_expression','update_expression'}:
            target=field(node,'left') or field(node,'argument')
            if target is not None and target.type=='identifier':rebound.add(text(target))
        if suffix in EXTENSIONS and node.type in FUNCTIONS-{'method_definition'} and owner(node) is None:
            binding=field(node,'name')
            container=node.parent
            if container is not None and container.type=='variable_declarator':
                binding=field(container,'name');container=container.parent
                if container is not None and container.type in {'lexical_declaration','variable_declaration'}:container=container.parent
            if container is not None and container.type=='export_statement':container=container.parent
            if container is not None and container.type=='program' and binding is not None and binding.type=='identifier':definitions[text(binding)].append(node)
    registrations=defaultdict(list)
    for node in nodes:
        if node.type not in {'call_expression','method_invocation'}:continue
        receiver,method=call_parts(node)
        if method not in {'register_provider','registerProvider'}:continue
        args=field(node,'arguments')
        if args is None or len(args.named_children)<2:continue
        key,loader=args.named_children[:2]
        if key.type not in {'string','string_literal'}:continue
        # No interpolation, concatenation or computed provider keys.
        key_text=text(key)
        if not re.fullmatch(r'''["'][A-Za-z0-9_.-]+["']''',key_text):continue
        enclosing=owner(node);definition=None
        if suffix in EXTENSIONS and loader.type=='identifier':
            binding=text(loader);matches=definitions.get(binding,[])
            shadowed=set()
            if enclosing is not None:
                params=field(enclosing,'parameters') or field(enclosing,'parameter')
                if params is not None:shadowed.update(text(n) for n in local_walk(params) if n.type=='identifier')
                for child in local_walk(enclosing):
                    if child.type=='variable_declarator':shadowed.add(text(field(child,'name')))
                    for nested in child.named_children:
                        if nested.type in FUNCTIONS|{'class_declaration'}:
                            shadowed.add(text(field(nested,'name')))
            if len(matches)==1 and binding not in rebound|shadowed:definition=matches[0]
        elif suffix=='.java' and loader.type=='method_reference':
            cls=enclosing.parent if enclosing is not None else None
            while cls is not None and cls.type!='class_declaration':
                if cls.type=='class_body' and cls.parent is not None and cls.parent.type=='object_creation_expression':
                    cls=None;break
                cls=cls.parent
            reference=re.fullmatch(r'(this|[A-Za-z_]\w*)::([A-Za-z_]\w*)',text(loader))
            if cls is not None and reference and reference[1] in {'this',text(field(cls,'name'))}:
                body=field(cls,'body')
                matches=[n for n in body.named_children if n.type=='method_declaration' and text(field(n,'name'))==reference[2]] if body is not None else []
                if len(matches)==1:definition=matches[0]
        if definition is not None:
            registrations[(enclosing.start_byte if enclosing is not None else -1,receiver)].append((key_text[1:-1],node,definition))
    for group in registrations.values():
        if len({key for key,_,_ in group})<2:continue
        out.append(finding('review.provider_registry',_registry_review(),
            [f'{rel}:{n.start_point[0]+1}' for _,call,definition in group for n in (call,definition)],
            ['literal provider registrations and unique local loader definitions'],
            ['runtime contract and interchangeability not verified'],observed=True))
    return out,'bounded_rules_applied'
