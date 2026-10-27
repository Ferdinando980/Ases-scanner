from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import re
import ast
import io
import tokenize

from ..model import FactGraph
from ..epistemology import stable_fingerprint, evidence_strength
from ..scanners.filesystem import iter_owned_files
from ..source_roles import classify_source
from ..scanners.javascript import EXTENSIONS as JS_EXTENSIONS, syntax_text

CODE_EXTS={'.java','.kt','.py','.cs','.cpp','.cc','.cxx'} | JS_EXTENSIONS
TEST_MARKERS=('/test/','/tests/','src/test/','__tests__','.test.','.spec.')
PROFILE='pattern-opportunities/4'
AUXILIARY_PARTS=frozenset({'work','bench','benchmark','benchmarks','examples','samples','experiments','research'})

# Human-readable rule metadata is emitted with each finding through rule_id/signals.
# Rules are intentionally precision-first: weak signals become HINT, not OPPORTUNITY.
PATTERN_RULES={
    'review.service_responsibilities': ('ARCHITECTURAL','Service Layer'),
    'review.strategy_variants': ('BEHAVIORAL','Strategy'),
    'review.provider_registry': ('ARCHITECTURAL','Provider Registry'),
    'architecture.layered': ('ARCHITECTURAL','Layered Architecture'),
    'architecture.mvc': ('ARCHITECTURAL','MVC'),
    'architecture.repository': ('ARCHITECTURAL','Repository'),
    'architecture.service_layer': ('ARCHITECTURAL','Service Layer'),
    'behavior.state_family': ('BEHAVIORAL','State'),
    'behavior.strategy_family': ('BEHAVIORAL','Strategy'),
    'behavior.command_family': ('BEHAVIORAL','Command'),
    'creation.factory_idiom': ('CREATIONAL','Factory'),
    'opportunity.state_dispatch': ('BEHAVIORAL','State'),
    'opportunity.strategy_dispatch': ('BEHAVIORAL','Strategy'),
    'opportunity.command_dispatch': ('BEHAVIORAL','Command'),
    'opportunity.observer_fanout': ('BEHAVIORAL','Observer'),
    'opportunity.chain_handlers': ('BEHAVIORAL','Chain of Responsibility'),
    'opportunity.template_method': ('BEHAVIORAL','Template Method'),
    'structural.adapter_family': ('STRUCTURAL','Adapter'),
    'opportunity.adapter_boundary': ('STRUCTURAL','Adapter'),
    'opportunity.facade_repeated_orchestration': ('STRUCTURAL','Facade'),
    'opportunity.decorator_wrapping': ('STRUCTURAL','Decorator'),
    'opportunity.proxy_remote_concerns': ('STRUCTURAL','Proxy'),
}

_FACTORY_NOISE={
    'string','integer','long','double','float','boolean','date','atomiclong','bigdecimal','biginteger',
    'illegalargumentexception','illegalstateexception','runtimeexception','exception','error',
    'arraylist','linkedlist','hashmap','map','hashset','set','optional','modelandview','responseentity',
}
_FACTORY_SUFFIX_NOISE=('dto','request','response','exception','error','record','entity','model','value')
_RECEIVER_NOISE={
    'self','this','super','console','logger','log','math','json','path','os','re','str','list','dict','set',
    'system','collections','document','window','classlist','response','event','array','thread','optional',
}


def recover_pattern_findings(root: Path, graph: FactGraph, inventory: dict | None = None) -> list[dict]:
    findings=[]
    findings.extend(_architecture_findings(root, graph))
    findings.extend(_observed_design_patterns(root, graph))
    review_coverage=[]
    findings.extend(_code_opportunities(root, graph, review_coverage))
    if inventory is not None:
        inventory['design_review_coverage']=review_coverage
    for finding in findings:
        if finding['status']=='OPPORTUNITY' and any(
                {p.casefold() for p in Path(re.sub(r':\d+$','',ev)).parts[:-1]} & AUXILIARY_PARTS
                for ev in finding.get('evidence',[])):
            finding.update(status='HINT',confidence='low')
            finding['reason']+=' Evidence is in an auxiliary/experimental tree; application relevance requires confirmation.'
            finding['counter_evidence'].append('auxiliary/experimental source scope; not an application refactoring recommendation')
            finding['signals']['negative'].append('application relevance unverified')
    return _dedupe(findings)


def pattern_views(findings: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Compatibility projections for older ASES consumers."""
    observed=[]
    opportunities=[]
    hints=[]
    for f in findings:
        if f['status']=='OBSERVED' and f['category']!='ARCHITECTURAL':
            observed.append({
                'id':f['id'], 'name':f['pattern'], 'candidate_patterns':(['Simple Factory / Factory idiom'] if f['pattern']=='Factory' else [f['pattern']]),
                'status':'OBSERVED', 'reason':f['reason'], 'evidence':f['evidence'],
                'confidence':f['confidence'], 'rule_id':f['rule_id'],
            })
        elif f['status']=='OPPORTUNITY':
            opportunities.append(_legacy_opportunity(f))
        elif f['status']=='HINT':
            hints.append(_legacy_opportunity(f))
    return observed, opportunities, hints


def _legacy_opportunity(f):
    return {
        'id':f['id'], 'category':f['category'], 'pattern':f['pattern'], 'status':f['status'],
        'smell':f.get('smell'), 'reason':f['reason'], 'evidence':f['evidence'],
        'confidence':f['confidence'], 'guidance':f.get('guidance',''), 'rule_id':f['rule_id'],
        'scope':f.get('scope','project'), 'signals':f.get('signals',{}),
        **({'design_review':f['design_review']} if 'design_review' in f else {}),
    }


def _finding(rule_id, status, confidence, reason, evidence, *, smell=None, guidance='', signals=None, scope='project', counter_evidence=None, assumptions=None):
    category,pattern=PATTERN_RULES[rule_id]
    evidence=sorted(set(evidence))
    fingerprint=stable_fingerprint(rule_id, pattern, evidence)
    return {
        'id':f"pattern:{fingerprint}",
        'fingerprint':fingerprint,
        'rule_id':rule_id,
        'category':category,
        'level':_pattern_level(rule_id, pattern),
        'pattern':pattern,
        'status':status,
        'confidence':confidence,
        'scope':scope,
        'smell':smell,
        'reason':reason,
        'evidence':evidence,
        'evidence_strength':evidence_strength(evidence),
        'counter_evidence':counter_evidence if counter_evidence is not None else (signals or {}).get('negative',[]),
        'assumptions':assumptions or [],
        'signals':signals or {'positive':[],'negative':[]},
        'guidance':guidance,
    }


def _pattern_level(rule_id: str, pattern: str) -> str:
    if rule_id.startswith('architecture.') or rule_id in {'review.service_responsibilities','review.provider_registry'}:
        return 'ARCHITECTURE' if pattern in {'Layered Architecture','MVC'} else 'APPLICATION_PATTERN'
    if pattern == 'Factory':
        return 'DESIGN_IDIOM'
    return 'GOF'


def _architecture_findings(root: Path, graph: FactGraph) -> list[dict]:
    by_id={n.id:n for n in graph.nodes}
    prod={n.id:n for n in graph.nodes if not n.metadata.get('is_test_code')}
    deps=[e for e in graph.edges if e.relation=='depends_on' and e.source in prod and e.target in prod]
    pairs=Counter((prod[e.source].kind, prod[e.target].kind) for e in deps)
    out=[]

    c2s=pairs[('controller','service')]
    s2r=pairs[('service','repository')]
    c2r=pairs[('controller','repository')]
    if c2s and s2r:
        evidence=[ev for e in deps if (prod[e.source].kind,prod[e.target].kind) in {('controller','service'),('service','repository')} for ev in e.evidence]
        conf='high' if c2s>=2 and s2r>=2 and not c2r else 'medium'
        out.append(_finding('architecture.layered','OBSERVED',conf,
            f"Dependency edges show controller→service ({c2s}) and service→repository ({s2r}) layers" + (f", with {c2r} controller→repository shortcut(s)." if c2r else '.'),
            evidence,
            guidance='Treat this as observed structure, not proof that every dependency obeys the layering rule.',
            signals={'positive':[f'{c2s} controller→service dependencies',f'{s2r} service→repository dependencies'], 'negative':([f'{c2r} controller→repository shortcuts'] if c2r else [])}))

    repositories=[n for n in prod.values() if n.kind=='repository']
    if repositories:
        out.append(_finding('architecture.repository','OBSERVED','high',
            f"{len(repositories)} production repository component(s) isolate persistence-facing access.",
            [ev for n in repositories for ev in n.provenance.evidence],
            guidance='This records the repository role observed in code; it does not assert a specific GoF pattern.',
            signals={'positive':[f'{len(repositories)} repository components'], 'negative':[]}))

    services=[n for n in prod.values() if n.kind=='service']
    service_callers=sum(1 for e in deps if prod[e.target].kind=='service' and prod[e.source].kind=='controller')
    if len(services)>=2 and service_callers:
        out.append(_finding('architecture.service_layer','OBSERVED','high',
            f"{len(services)} service components form an application service layer used by controllers ({service_callers} dependency edge(s)).",
            [ev for n in services for ev in n.provenance.evidence],
            guidance='Observed service-layer structure does not imply every business rule belongs in a service.',
            signals={'positive':[f'{len(services)} services',f'{service_callers} controller→service dependencies'],'negative':[]}))

    controllers=[n for n in prod.values() if n.kind=='controller']
    models=[n for n in prod.values() if n.kind in {'entity','domain_object'}]
    views=[p for p in iter_owned_files(root) if p.suffix.lower() in {'.jsp','.html','.htm','.hbs','.ejs','.pug','.twig'} and classify_source(p.relative_to(root).as_posix(), root)['role'] == 'OWNED_SOURCE']
    if controllers and models and views:
        out.append(_finding('architecture.mvc','OBSERVED','medium',
            f"Controllers ({len(controllers)}), model/domain types ({len(models)}), and view templates ({len(views)}) were all observed, consistent with MVC structure.",
            [*(ev for n in controllers[:5] for ev in n.provenance.evidence), *(p.relative_to(root).as_posix() for p in views[:5])],
            guidance='Static structure supports MVC, but request/view responsibility boundaries still require behavioral evidence.',
            signals={'positive':['controller layer present','model/domain types present','view templates present'],'negative':[]}))
    return out


def _observed_design_patterns(root: Path, graph: FactGraph) -> list[dict]:
    out=[]
    by_id={n.id:n for n in graph.nodes}
    implemented=defaultdict(list)
    for e in graph.edges:
        if e.relation=='implements' and not by_id.get(e.source, type('x',(),{'metadata':{}})) .metadata.get('is_test_code'):
            implemented[e.target].append(e.source)

    for target,impls in implemented.items():
        if len(impls)<2:
            continue
        node=by_id.get(target)
        if not node: continue
        name=node.name.lower()
        evidence=[ev for e in graph.edges if e.target==target and e.relation=='implements' for ev in e.evidence]
        if name.endswith('state'):
            out.append(_finding('behavior.state_family','OBSERVED','high',
                f"{len(impls)} production types implement the State-named contract {node.name}; this is strong structural evidence of State.", evidence,
                guidance='Runtime transition ownership is not proven by interface structure alone.',
                signals={'positive':['State-named common contract',f'{len(impls)} implementations'],'negative':[]}))
        elif name.endswith('strategy'):
            out.append(_finding('behavior.strategy_family','OBSERVED','high',
                f"{len(impls)} production types implement the Strategy-named contract {node.name}; this is strong structural evidence of Strategy.", evidence,
                guidance='Runtime interchangeability is inferred from structure and naming, not dynamically verified.',
                signals={'positive':['Strategy-named common contract',f'{len(impls)} implementations'],'negative':[]}))
        elif name.endswith('command'):
            out.append(_finding('behavior.command_family','OBSERVED','high',
                f"{len(impls)} production types implement the Command-named contract {node.name}; this is strong structural evidence of Command.", evidence,
                guidance='Queueing, undo, or invoker semantics are not assumed unless separately observed.',
                signals={'positive':['Command-named common contract',f'{len(impls)} implementations'],'negative':[]}))

    # Adapter is observed only when a named adapter contract is implemented at a real external boundary.
    for target,impls in implemented.items():
        node=by_id.get(target)
        if not node or not node.name.lower().endswith('adapter'):
            continue
        prod_impls=[by_id[i] for i in impls if i in by_id and not by_id[i].metadata.get('is_test_code')]
        boundary=[]
        for impl in prod_impls:
            try:
                text=(root/impl.path).read_text(encoding='utf-8',errors='ignore') if impl.path else ''
            except OSError:
                text=''
            if re.search(r'(?i)https?://|HttpURLConnection|RestTemplate|WebClient|HttpClient|fetch\s*\(|axios\.',text):
                boundary.append(impl)
        if boundary:
            evidence=[ev for impl in boundary for ev in impl.provenance.evidence]
            out.append(_finding('structural.adapter_family','OBSERVED','high',
                f"Adapter-named contract {node.name} is implemented by {len(prod_impls)} production type(s), with an external protocol/API boundary observed in {len(boundary)} implementation(s).",
                evidence, guidance='This establishes structural Adapter evidence; semantic equivalence of every mapped field is not dynamically verified.',
                signals={'positive':['Adapter-named contract','implements relation','external boundary evidence'],'negative':[]}))

    for n in graph.nodes:
        if n.metadata.get('is_test_code') or n.kind!='factory':
            continue
        targets=_meaningful_creations(n.metadata.get('creation_targets') or [])
        if len(targets)>=2:
            out.append(_finding('creation.factory_idiom','OBSERVED','medium',
                f"Factory-named production type {n.name} centralizes creation of multiple meaningful concrete targets ({', '.join(targets[:6])}).",
                n.provenance.evidence,
                guidance='This establishes a factory idiom, not necessarily GoF Factory Method or Abstract Factory.',
                signals={'positive':['Factory-named type',f'{len(targets)} meaningful creation targets'],'negative':[]}))
    return out


def _code_opportunities(root: Path, graph: FactGraph, review_coverage=None) -> list[dict]:
    from .design_review import responsibility_reviews, coverage_record
    review_coverage=review_coverage if review_coverage is not None else []
    files=[]
    for path in iter_owned_files(root):
        if path.suffix.lower() not in CODE_EXTS:
            continue
        rel=path.relative_to(root).as_posix()
        if _is_test(rel):
            continue
        if graph.coverage.get(rel,{}).get('status')=='UNKNOWN':
            review_coverage.append(coverage_record(rel,'UNKNOWN','source_structure_unavailable'))
            continue
        try:
            if path.suffix.lower() in JS_EXTENSIONS:
                from ..scanners.javascript import MAX_BYTES
                if path.stat().st_size > MAX_BYTES or graph.coverage.get(rel, {}).get('status') == 'UNKNOWN':
                    review_coverage.append(coverage_record(rel,'NOT_SUPPORTED','language_not_supported'))
                    continue  # Never bypass the admitted parser scope through a textual fallback.
            text=path.read_text(encoding='utf-8',errors='ignore')
        except OSError:
            from ..scanners.filesystem import source_unavailable
            source_unavailable(root,path,graph)
            review_coverage.append(coverage_record(rel,'UNKNOWN','source_unavailable_during_scan'))
            continue
        files.append((path,rel,text))

    # Index proven emission sites once; never silence other direct calls in the file.
    emitters = {node.id: node for node in graph.nodes if node.path and node.name.endswith(".emit")}
    emission_sites = defaultdict(set)
    for node in emitters.values():
        for location in node.provenance.evidence:
            emission_sites[(node.metadata.get("receiver"), location)].add(node.metadata.get("pubsub_receiver") == "node-events")
    for edge in graph.edges:
        if edge.relation == "calls" and edge.target in emitters:
            node = emitters[edge.target]
            for location in edge.evidence:
                emission_sites[(node.metadata.get("receiver"), location)].add(node.metadata.get("pubsub_receiver") == "node-events")
    proven_emissions = {site for site, states in emission_sites.items() if states == {True}}
    out=[]
    # Local, evidence-backed rules.
    for path,rel,text in files:
        out.extend(_dispatch_findings(rel,text))
        out.extend(_factory_findings(rel,text,path.stem))
        observer_text = _notification_text(rel,text)
        out.extend(_observer_findings(rel,observer_text,proven_emissions))
        out.extend(_chain_findings(rel,text))
        out.extend(_template_findings(rel,text,path.stem))
        out.extend(_adapter_findings(rel,text,path.stem))
        out.extend(_decorator_findings(rel,text,path.stem))
        out.extend(_proxy_findings(rel,text,path.stem))

    for assessment in responsibility_reviews(files,coverage=review_coverage):
        review = assessment.pop('review')
        finding = _finding(**assessment)
        finding['design_review'] = review
        out.append(finding)

    # Facade is intentionally project-level: many collaborators in one file is not enough.
    facade=_facade_finding(graph)
    if facade: out.append(facade)
    return out


def _notification_text(rel,source):
    """Remove comments/literals before looking for notification call spellings."""
    suffix=Path(rel).suffix.lower()
    if suffix in JS_EXTENSIONS:return syntax_text(source,suffix,remove_strings=True)
    if suffix=='.py':
        lines=source.splitlines(keepends=True);offsets=[0]
        for line in lines:offsets.append(offsets[-1]+len(line))
        masked=list(source)
        try:
            for token in tokenize.generate_tokens(io.StringIO(source).readline):
                if token.type not in {tokenize.STRING,tokenize.COMMENT,getattr(tokenize,'FSTRING_MIDDLE',-1),getattr(tokenize,'TSTRING_MIDDLE',-1)}:continue
                begin=offsets[token.start[0]-1]+token.start[1]
                end=offsets[token.end[0]-1]+token.end[1]
                for index in range(begin,end):
                    if masked[index] not in '\r\n':masked[index]=' '
        except (tokenize.TokenError,IndentationError):return ''
        return ''.join(masked)
    if suffix=='.java':
        from ..scanners.java_syntax import parse,walk
        data=bytearray(source.encode('utf-8'))
        try:
            for node in walk(parse(source)):
                if node.type not in {'line_comment','block_comment','string_literal','character_literal'}:continue
                for index in range(node.start_byte,node.end_byte):
                    if data[index] not in {10,13}:data[index]=32
        except ValueError:return ''
        return data.decode('utf-8')
    return source


def _dispatch_sites(rel,source):
    """Count direct cases in real syntax nodes; never scan an arbitrary text window."""
    suffix=Path(rel).suffix.lower()
    sites=[]
    if len(source.encode('utf-8'))>5*1024*1024:return sites
    try:
        if suffix=='.py':
            tree=ast.parse(source)
            parents={child:node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
            for node in ast.walk(tree):
                if not isinstance(node,ast.Match):continue
                labels=tuple(sorted(ast.dump(case.pattern,include_attributes=False) for case in node.cases
                                    if not isinstance(case.pattern,ast.MatchAs) or case.pattern.pattern is not None))
                owner=parents.get(node)
                while owner is not None and not isinstance(owner,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    owner=parents.get(owner)
                sites.append((ast.unparse(node.subject),labels,node.lineno,id(owner) if owner else None,'match'))
        elif suffix in JS_EXTENSIONS or suffix=='.java':
            if suffix=='.java':
                from ..scanners.java_syntax import parse,walk
                tree=parse(source)
                owners={'method_declaration','constructor_declaration'}
            else:
                from ..scanners.javascript import parse,walk,FUNCTIONS
                tree=parse(source,suffix);owners=FUNCTIONS
            if tree.has_error:return []
            for node in walk(tree):
                if node.type not in {'switch_statement','switch_expression'}:continue
                body=node.child_by_field_name('body')
                value=node.child_by_field_name('value') or node.child_by_field_name('condition')
                if body is None or value is None:continue
                labels=[]
                for group in body.named_children:
                    if group.type=='switch_case':
                        label=group.child_by_field_name('value')
                        if label:labels.append(label.text.decode('utf-8'))
                    elif group.type in {'switch_block_statement_group','switch_rule'}:
                        labels.extend(c.text.decode('utf-8') for c in group.named_children
                                      if c.type=='switch_label' and c.text.startswith(b'case'))
                owner=node.parent
                while owner is not None and owner.type not in owners:owner=owner.parent
                sites.append((value.text.decode('utf-8').strip('()'),tuple(sorted(labels)),
                              node.start_point[0]+1,owner.start_byte if owner else None,'switch'))
    except (SyntaxError,ValueError,RecursionError):
        return []
    return sites


def _dispatch_findings(rel,text):
    out=[]
    switches=_dispatch_sites(rel,text)
    for selector,labels,line,owner,kind in switches:
        cases=len(labels)
        if cases<3:continue
        low=selector.lower()
        if re.search(r'\b(state|status|phase)\b',low):
            rule='opportunity.state_dispatch'; smell='state-dispatch'
        elif re.search(r'\b(command|action|operation)\b',low):
            rule='opportunity.command_dispatch'; smell='operation-dispatch'
        else:
            rule='opportunity.strategy_dispatch'; smell='variant-dispatch'
        repeated=[site for site in switches if site[1]==labels and site[0].lower()==low
                  and site[3] is not None and owner is not None and site[3]!=owner]
        supported=bool(repeated) and (cases>=4 or rule!='opportunity.strategy_dispatch')
        status='OPPORTUNITY' if supported else 'HINT'
        conf='medium' if status=='OPPORTUNITY' else 'low'
        out.append(_finding(rule,status,conf,
            f"A {cases}-branch {kind} selects behavior from {selector.strip()!r}. The branching shape may benefit from {PATTERN_RULES[rule][1]} if variants keep growing or recur elsewhere.",
            [f'{rel}:{line}',*[f'{rel}:{site[2]}' for site in repeated]], smell=smell,
            guidance='Keep the conditional when variants are few, local, and stable; introduce the pattern only when behavior varies independently or dispatch is duplicated.',
            signals={'positive':[f'{cases} direct syntax cases',f'selector={selector.strip()}']+(['same selector/cases in distinct callables'] if repeated else []),
                     'negative':(['only 3 branches'] if cases==3 and rule=='opportunity.strategy_dispatch' else [])+([] if repeated else ['no repeated selector/case set across distinct callables'])},
            counter_evidence=['business equivalence, variation pressure and refactoring benefit not established'],
            assumptions=['Repeated syntax is an indication of duplicated selection policy, not proof of semantic equivalence.'],scope='file'))
    return out


def _factory_findings(rel,text,stem):
    if 'factory' in stem.lower(): return []
    suffix=Path(rel).suffix.lower()
    if suffix not in JS_EXTENSIONS|{'.java'}:return []
    try:
        if suffix=='.java':
            from ..scanners.java_syntax import parse,walk
            tree=parse(text);owners={'method_declaration','constructor_declaration'}
        else:
            from ..scanners.javascript import parse,walk,FUNCTIONS
            tree=parse(text,suffix);owners=FUNCTIONS
        if tree.has_error:return []
        groups=defaultdict(list)
        for node in walk(tree):
            if node.type not in {'new_expression','object_creation_expression'}:continue
            constructor=node.child_by_field_name('constructor') or node.child_by_field_name('type')
            if constructor is None or constructor.type not in {'identifier','type_identifier'}:continue
            name=constructor.text.decode('utf-8')
            if not _meaningful_creation(name):continue
            parent=node.parent
            if parent.type=='return_statement':role='return'
            elif parent.type in {'assignment_expression','variable_declarator'}:
                target=parent.child_by_field_name('left') or parent.child_by_field_name('name')
                if target is None or target.type not in {'identifier'}:continue
                role='assign:'+target.text.decode('utf-8')
            else:continue
            ancestor=parent.parent;conditional=False
            while ancestor is not None and ancestor.type not in owners:
                conditional |= ancestor.type in {'if_statement','switch_case','switch_rule','switch_block_statement_group'}
                ancestor=ancestor.parent
            if conditional and ancestor is not None:
                groups[(ancestor.start_byte,role)].append((name,node.start_point[0]+1))
    except ValueError:return []
    out=[]
    for (_,role),sites in groups.items():
        names=sorted({name for name,line in sites})
        if len(names)<2:continue
        out.append(_finding('creation.factory_idiom','OPPORTUNITY','medium',
            f"Conditional branches in one callable construct {len(names)} alternative concrete products ({', '.join(names[:6])}) for the same {role} role. A factory may help if this policy is duplicated or independently changing.",
            [f'{rel}:{line}' for name,line in sites],smell='conditional-alternative-construction',
            guidance='Keep constructors direct when selection is local and stable; introduce a factory only for one product role with repeated/configurable creation policy.',
            signals={'positive':['syntax-local conditional creation in one callable',f'{len(names)} alternative products',f'common role: {role}'],
                     'negative':['independent variation or duplication of this creation policy not established']},scope='file'))
    return out

def _observer_findings(rel,text,proven_emissions=()):
    # Require distinct listener/subscriber targets or distinct notification endpoints.
    matches = list(re.finditer(r'\b([A-Za-z_]\w*)\.(notify|update|on[A-Z]\w*|publish|emit)\s*\(',text))
    occurrences = Counter((match.group(1), f'{rel}:{_line(text,match.start())}') for match in matches)
    notify_receivers=set()
    for match in matches:
        receiver = match.group(1)
        if match.group(2)=='update' and not re.search(r'listener|subscriber|observer',receiver,re.I):
            continue  # Mapping/data updates do not establish notification consumers.
        site = (receiver, f'{rel}:{_line(text,match.start())}')
        if site not in proven_emissions or occurrences[site] != 1 or not re.match(re.escape(receiver) + r'\.emit\s*\(', match.group(0)):
            notify_receivers.add(receiver)
    direct_notify=set(m.group(1) for m in re.finditer(r'(?i)\b((?:notify|publish|emit|send)[A-Z_]\w*)\s*\(',text))
    consumers={x for x in notify_receivers|direct_notify if x.lower() not in _RECEIVER_NOISE}
    if len(consumers)<3: return []
    pos=min((text.lower().find(x.lower()) for x in consumers if text.lower().find(x.lower())>=0),default=0)
    return [_finding('opportunity.observer_fanout','OPPORTUNITY','medium',
        f"One module directly coordinates notifications to {len(consumers)} distinct listener/subscriber-like consumers. Observer may decouple subscriber membership from the producer.",
        [f'{rel}:{_line(text,pos)}'],smell='direct-notification-fanout',
        guidance='Keep direct calls when the subscriber set, ordering, and failure semantics are deliberately fixed; use Observer when subscribers vary independently.',
        signals={'positive':[f'{len(consumers)} distinct notification consumers'],'negative':[]},scope='file')]


def _chain_findings(rel,text):
    hits=list(re.finditer(r'(?i)\bif\b[^;{}\n]{1,260}?\breturn\s+([A-Za-z_]\w*handler\w*)\s*\(([^)]*)\)',text))
    hits += list(re.finditer(r'(?im)^\s*if\s+[^:\n]+:\s*\n\s*return\s+([A-Za-z_]\w*handler\w*)\s*\(([^)]*)\)',text))
    handlers={m.group(1).lower() for m in hits}
    if len(handlers)<3: return []
    return [_finding('opportunity.chain_handlers','OPPORTUNITY','medium',
        f"At least {len(handlers)} distinct handler-like branches are tried sequentially with early return. A Chain of Responsibility may make ordering and extension explicit.",
        [f'{rel}:{_line(text,min(m.start() for m in hits))}'],smell='sequential-handler-dispatch',
        guidance='Keep guard clauses when conditions encode unrelated business rules; use a chain only when handlers share one request/decision contract.',
        signals={'positive':[f'{len(handlers)} distinct handler branches','early-return dispatch'],'negative':[]},scope='file')]


def _template_findings(rel,text,stem):
    lifecycle=[name for name in ('prepare','validate','execute','process','finalize','cleanup') if re.search(rf'(?i)\b{name}\s*\(',text)]
    abstractish=bool(re.search(r'(?i)\babstract\s+class\b|\bclass\s+\w*(?:base|template)\b|\bABC\b',text))
    if abstractish and len(lifecycle)>=3:
        pos=min(text.lower().find(x) for x in lifecycle if text.lower().find(x)>=0)
        orchestrated=sum(len(re.findall(rf'(?i)\b{name}\s*\(',text))>=2 for name in lifecycle)>=3
        status='OPPORTUNITY' if orchestrated else 'HINT'
        conf='medium' if orchestrated else 'low'
        return [_finding('opportunity.template_method',status,conf,
            (f"A base/abstract type defines and invokes a {len(lifecycle)}-step lifecycle ({', '.join(lifecycle)}), suggesting an invariant algorithm skeleton with overridable steps." if orchestrated else f"A base/abstract type exposes a {len(lifecycle)}-step lifecycle ({', '.join(lifecycle)}), but an invariant orchestration sequence was not established."),
            [f'{rel}:{_line(text,pos)}'],smell='base-lifecycle-skeleton',
            guidance='Prefer composition when steps need runtime replacement; use Template Method only when the sequence is invariant and subclasses customize defined hooks.',
            signals={'positive':['base/abstract type',f'{len(lifecycle)} lifecycle steps'] + (['lifecycle orchestration observed'] if orchestrated else []),'negative':([] if orchestrated else ['invariant orchestration not proven'])},scope='file')]
    return []


def _adapter_findings(rel,text,stem):
    lname=stem.lower()
    boundary=any(x in lname for x in ('client','integration','gateway','connector','external','mapper'))
    external=bool(re.search(r'(?i)\b(fetch|axios|requests\.|resttemplate|webclient|grpc|httpclient|vendor|external|client\.)',text))
    pairs=re.findall(r'(?m)\b([A-Za-z_]\w*)\s*[:=]\s*(?:[A-Za-z_]\w*\.)+([A-Za-z_]\w*)',text)
    renamed=[(a,b) for a,b in pairs if a.lower()!=b.lower()]
    if boundary and external and len(renamed)>=3 and 'adapter' not in lname:
        m=re.search(r'\b[A-Za-z_]\w*\s*[:=]\s*(?:[A-Za-z_]\w*\.)+[A-Za-z_]\w*',text)
        return [_finding('opportunity.adapter_boundary','OPPORTUNITY','medium',
            f"A boundary module performs {len(renamed)} renamed field translations while talking to an external/client API. Adapter may isolate the external model from the internal contract.",
            [f'{rel}:{_line(text,m.start() if m else 0)}'],smell='external-shape-translation',
            guidance='Keep mapping inline for one stable provider; use Adapter when provider shapes change independently or multiple providers must satisfy one internal interface.',
            signals={'positive':['boundary-oriented module','external client/API evidence',f'{len(renamed)} renamed field mappings'],'negative':[]},scope='file')]
    if boundary and len(renamed)>=3:
        m=re.search(r'\b[A-Za-z_]\w*\s*[:=]\s*(?:[A-Za-z_]\w*\.)+[A-Za-z_]\w*',text)
        return [_finding('opportunity.adapter_boundary','HINT','low',
            'Boundary-like naming and shape translation were observed, but no external/provider boundary was confirmed.',
            [f'{rel}:{_line(text,m.start() if m else 0)}'],smell='shape-translation',
            guidance='Do not introduce Adapter solely for object mapping; require an independently changing boundary or substitutable provider.',
            signals={'positive':['boundary-oriented name',f'{len(renamed)} renamed mappings'],'negative':['external boundary not confirmed']},scope='file')]
    return []


def _decorator_findings(rel,text,stem):
    if 'decorator' in stem.lower(): return []
    nested=re.search(r'new\s+([A-Z]\w*)\s*\(\s*new\s+([A-Z]\w*)\s*\(\s*new\s+([A-Z]\w*)\s*\(',text)
    if not nested: return []
    names=nested.groups()
    common=_common_suffix(names)
    status='OPPORTUNITY' if common else 'HINT'
    conf='medium' if common else 'low'
    return [_finding('opportunity.decorator_wrapping',status,conf,
        f"Three nested wrappers are constructed ({' → '.join(names)}). " + (f"Their shared naming role ({common}) strengthens the case for composable Decorator semantics." if common else 'A common component contract was not established.'),
        [f'{rel}:{_line(text,nested.start())}'],smell='nested-behavior-wrapping',
        guidance='Keep one-off nesting when wrappers are not independently interchangeable; use Decorator only when wrappers share a component contract and combine in multiple ways.',
        signals={'positive':['three nested wrappers'] + ([f'common suffix {common}'] if common else []),'negative':([] if common else ['shared contract not established'])},scope='file')]


def _proxy_findings(rel,text,stem):
    if 'proxy' in stem.lower(): return []
    code=re.sub(r'/\*[\s\S]*?\*/|(?m:^\s*//[^\n]*)', '', text)
    call_pattern=r'(?i)\bfetch\s*\(|\baxios\.(?:get|post|put|patch|delete)\s*\(|\b(?:this\.)?http\s*\.\s*(?:get|post|put|patch|delete)(?:<[^\n]{0,160}?>)?\s*\('
    calls=list(re.finditer(call_pattern,code))
    concerns=[x for x in ('cache','retry','auth','authorize','token','timeout') if re.search(rf'(?i)\b{x}\w*\b',code)]
    if len(calls)>=2 and len(concerns)>=2:
        native_client=bool(re.search(r'\bHttpClient\b',code))
        status,confidence=('HINT','low') if native_client else ('OPPORTUNITY','medium')
        reason=(f"{len(calls)} remote calls coexist with {len(concerns)} access concerns ({', '.join(concerns)}). "
                + ("The framework HTTP client already offers interceptors; a separate Proxy is not established."
                   if native_client else "A shared boundary may help if callers repeat this behavior."))
        pos=text.find(calls[0].group(0))
        return [_finding('opportunity.proxy_remote_concerns',status,confidence,
            reason,[f'{rel}:{_line(text,max(pos,0))}'],smell='remote-access-cross-cutting-concerns',
            guidance="Use native HTTP middleware/interceptors first; consider Proxy only when callers need a stable domain-facing interface around repeated remote access.",
            signals={'positive':[f'{len(calls)} remote calls',f"access concerns: {', '.join(concerns)}"],
                     'negative':['framework-native interception available'] if native_client else []},scope='file')]
    return []


def _facade_finding(graph: FactGraph):
    by_id={n.id:n for n in graph.nodes}
    prod={n.id:n for n in graph.nodes if not n.metadata.get('is_test_code')}
    owner_of={n.id:n.metadata.get('owner') for n in graph.nodes if n.kind=='method'}
    called=defaultdict(set); sequences=defaultdict(lambda:defaultdict(list)); evidence=defaultdict(list)
    # The Java scanner inserts these edges in source call order within each method.
    for e in graph.edges:
        if e.relation!='calls_dependency' or e.source not in owner_of or e.target not in prod: continue
        owner=owner_of[e.source]
        if owner not in prod or prod[e.target].kind not in {'service','repository','component','factory','configuration','interface'}: continue
        called[owner].add(e.target); evidence[owner].extend(e.evidence)
        sequences[owner][e.source].append(e.target)
    sources=[s for s,targets in called.items() if len(targets)>=3]
    best=None
    for i,a in enumerate(sources):
        for b in sources[i+1:]:
            shared=called[a]&called[b]
            if len(shared)<3: continue
            workflow=None
            for method_a,calls_a in sequences[a].items():
                ordered_a=tuple(target for target in calls_a if target in shared)
                if len(ordered_a)<3: continue
                for method_b,calls_b in sequences[b].items():
                    ordered_b=tuple(target for target in calls_b if target in shared)
                    if ordered_a==ordered_b:
                        workflow=(method_a,method_b,ordered_a)
                        break
                if workflow: break
            candidate=(a,b,shared,workflow)
            score=(len(workflow[2]) if workflow else 0,len(shared))
            best_score=(len(best[3][2]) if best and best[3] else 0,len(best[2]) if best else 0)
            if best is None or score>best_score:
                best=candidate
    if not best: return None
    a,b,shared,workflow=best
    if workflow:
        method_a,method_b,ordered=workflow
        names=' → '.join(prod[x].name for x in ordered)
        return _finding('opportunity.facade_repeated_orchestration','OPPORTUNITY','medium',
            f"Methods {by_id[method_a].name} and {by_id[method_b].name} call the same {len(ordered)} subsystem collaborators in the same order ({names}). This repeated orchestration may benefit from a Facade.",
            evidence[a]+evidence[b],smell='repeated-multi-subsystem-calls',
            guidance='Confirm the matching call sequences represent the same workflow before extracting a Facade; collaborator overlap alone is not sufficient.',
            signals={'positive':['matching ordered collaborator sequence across production methods',f'{len(ordered)} shared called dependencies'],'negative':['business-workflow equivalence is not dynamically verified']},
            assumptions=['Matching ordered calls are structural evidence, not proof of identical business intent.'])
    names=', '.join(sorted(prod[x].name for x in shared)[:6])
    return _finding('opportunity.facade_repeated_orchestration','HINT','low',
        f"Two production components ({prod[a].name}, {prod[b].name}) actively call the same {len(shared)} subsystem collaborators ({names}), but a matching ordered call sequence was not established.",
        evidence[a]+evidence[b],smell='shared-multi-subsystem-dependencies',
        guidance='Treat shared collaborators as a lead only; consider a Facade when methods show repeated ordered orchestration of the same workflow.',
        signals={'positive':['same actively-called collaborator set used by multiple components',f'{len(shared)} shared called dependencies'],'negative':['matching ordered workflow sequence not established']})

def _meaningful_creations(names):
    return sorted({n for n in names if _meaningful_creation(n)})


def _meaningful_creation(name):
    low=name.lower()
    if low in _FACTORY_NOISE: return False
    if re.fullmatch(r'(?:u?int(?:8|16|32)|uint8clamped|float(?:16|32|64)|bigint64|biguint64)array',low):return False
    if low.endswith(_FACTORY_SUFFIX_NOISE): return False
    return True


def _common_suffix(names):
    words=[re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+',n) for n in names]
    if not words or any(not w for w in words): return ''
    suffixes=[w[-1].lower() for w in words]
    return suffixes[0] if len(set(suffixes))==1 and len(suffixes[0])>2 else ''


def _is_test(rel):
    low='/'+rel.lower().replace('\\','/')
    return classify_source(rel)['role'] == 'TEST' or any(x in low for x in TEST_MARKERS) or Path(rel).stem.lower().endswith('test')


def _line(text,pos):
    return text.count('\n',0,max(0,pos))+1


def _dedupe(items):
    # One stable rule/file fingerprint, retaining all evidence locations.
    state_rank={'OBSERVED':3,'OPPORTUNITY':2,'HINT':1}
    conf_rank={'high':3,'medium':2,'low':1}
    chosen={}
    for item in items:
        key=item['fingerprint']
        prev=chosen.get(key)
        if prev is None:
            chosen[key]=item
            continue
        if (state_rank[item['status']],conf_rank[item['confidence']]) > (state_rank[prev['status']],conf_rank[prev['confidence']]):
            winner,other=item,prev
        else:winner,other=prev,item
        for field in ('evidence','counter_evidence','assumptions'):
            winner[field]=sorted(set(winner.get(field,[])+other.get(field,[])))
        winner['signals']={direction:sorted(set(winner.get('signals',{}).get(direction,[])+other.get('signals',{}).get(direction,[])))
                           for direction in ('positive','negative')}
        winner['evidence_strength']=evidence_strength(winner['evidence'])
        chosen[key]=winner
    return sorted(chosen.values(), key=lambda x:(x['category'],x['pattern'],x['status'],x['evidence'][0] if x['evidence'] else ''))
