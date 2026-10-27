"""Bounded branch-local syntax facts; no target execution or symbolic solver."""
from __future__ import annotations

import ast
import builtins


def declared_catch(error, handlers):
    if "*" in handlers:
        return True
    target = error.func if isinstance(error, ast.Call) else None
    if target is None:
        return False
    name = ast.unparse(target)
    for handler in handlers:
        try:
            tree = ast.parse(handler, mode="eval").body
        except SyntaxError:
            continue
        candidates = tree.elts if isinstance(tree, ast.Tuple) else [tree]
        for item in candidates:
            candidate = ast.unparse(item)
            if candidate == name:
                return True
            # Only trusted built-in names; custom/imported inheritance is unresolved.
            thrown, caught = getattr(builtins, name, None), getattr(builtins, candidate, None)
            if isinstance(thrown, type) and isinstance(caught, type) and issubclass(thrown, BaseException) and issubclass(caught, BaseException) and issubclass(thrown, caught):
                return True
    return False


class _NegatedCondition(str):
    def __new__(cls, value):
        result = super().__new__(cls, "not (" + value + ")")
        result.expression = value
        return result


def negate(value):
    return _NegatedCondition(value)


def condition_predicates(conditions):
    result = []
    for condition in conditions:
        negative = False
        while isinstance(condition, _NegatedCondition):
            negative, condition = not negative, condition.expression
        result.append({"expression":str(condition), "negated":negative})
    return result


def merge_paths(paths):
    paths = list(dict.fromkeys(tuple(p) for p in paths))
    changed = True
    while changed:
        changed = False
        for index, left in enumerate(paths):
            for right in paths[index + 1:]:
                if left and right and left[:-1] == right[:-1] and (left[-1] == negate(right[-1]) or right[-1] == negate(left[-1])):
                    paths = [p for p in paths if p not in {left, right}] + [left[:-1]]
                    changed = True
                    break
            if changed:
                break
    return paths[:64], len(paths) > 64


def python_facts(node, response_wrappers=()):
    facts = []
    args = [*node.args.posonlyargs, *node.args.args]
    request = args[0].arg if args else None
    if any(isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and n.id == request for n in ast.walk(node)):
        response_wrappers = ()
    def expression(value):
        return ast.unparse(value)[:1200] if value is not None else "None"
    def emit(kind, syntax, conditions, catches=(), **data):
        if len(facts) < 499:
            facts.append({"kind":kind, "line":syntax.lineno, "conditions":[str(c) for c in conditions], "condition_predicates":condition_predicates(conditions), "catches":list(catches), **data})
        elif len(facts) == 499:
            facts.append({"kind":"unsupported-flow", "line":syntax.lineno, "conditions":[], "expression":"500 local-fact limit; remaining syntax not interpreted"})
    def expressions(value, conditions, catches):
        if value is None or len(facts) >= 500 or isinstance(value, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            return
        if isinstance(value, ast.IfExp):
            test = expression(value.test)
            expressions(value.test, conditions, catches)
            expressions(value.body, (*conditions, test), catches)
            expressions(value.orelse, (*conditions, negate(test)), catches)
        elif isinstance(value, ast.BoolOp):
            current = tuple(conditions)
            for part in value.values:
                expressions(part, current, catches)
                current += (expression(part) if isinstance(value.op, ast.And) else negate(expression(part)),)
        elif isinstance(value, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for generator in value.generators:
                expressions(generator.iter, conditions, catches)
            partial = (*conditions, "comprehension iteration/filter partial")
            for child in ast.iter_child_nodes(value):
                if not isinstance(child, ast.comprehension):
                    expressions(child, partial, catches)
            emit("unsupported-flow", value, conditions, expression="Comprehension cardinality/filter reachability unresolved")
        else:
            if isinstance(value, ast.Call):
                emit("call", value, conditions, catches, callee=expression(value.func), arguments=[expression(a) for a in value.args], keywords={k.arg or "**":expression(k.value) for k in value.keywords})
                for wrapper in response_wrappers:
                    if (isinstance(value.func,ast.Attribute) and isinstance(value.func.value,ast.Name)
                            and value.func.value.id==request and value.func.attr==wrapper['method']
                            and not value.keywords and len(value.args)==2):
                        payload = value.args[wrapper['payload_argument']]
                        status = value.args[wrapper['status_argument']]
                        emit('response',value,conditions,catches,expression=expression(payload),
                             output_fields=[k.value for k in payload.keys if isinstance(k,ast.Constant) and isinstance(k.value,str)] if isinstance(payload,ast.Dict) else [],
                             output_fields_complete=isinstance(payload,ast.Dict) and all(isinstance(k,ast.Constant) and isinstance(k.value,str) for k in payload.keys),
                             http_status=status.value if isinstance(status,ast.Constant) and type(status.value) is int else None,
                             wrapper_evidence=wrapper['evidence'],basis='declared local JSON serializer and HTTP writer; runtime unverified')
            for child in ast.iter_child_nodes(value):
                expressions(child, conditions, catches)
    def returned(value, statement, conditions, catches):
        if isinstance(value, ast.IfExp):
            test = expression(value.test)
            emit("branch", value, conditions, expression=test)
            expressions(value.test, conditions, catches)
            returned(value.body, statement, (*conditions, test), catches)
            returned(value.orelse, statement, (*conditions, negate(test)), catches)
            return
        emit("return", statement, conditions, catches, expression=expression(value),
             output_fields=[str(k.value) for k in value.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)] if isinstance(value, ast.Dict) else [],
             output_fields_complete=not isinstance(value, ast.Dict) or all(isinstance(k, ast.Constant) and isinstance(k.value, str) for k in value.keys))
        expressions(value, conditions, catches)
    def exits(statements):
        if not statements:
            return False
        last = statements[-1]
        return isinstance(last, (ast.Return, ast.Raise)) or isinstance(last, ast.If) and exits(last.body) and exits(last.orelse)
    def sequence(statements, paths, catches=()):
        for statement in statements:
            if not paths or len(facts) >= 500:
                break
            following = []
            for conditions in paths:
                if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    following.append(conditions)
                elif isinstance(statement, ast.If):
                    test = expression(statement.test)
                    expressions(statement.test, conditions, catches)
                    emit("branch", statement, conditions, expression=test)
                    constant = bool(statement.test.value) if isinstance(statement.test, ast.Constant) else None
                    if constant is not False:
                        following += sequence(statement.body, [(*conditions, test)], catches)
                    if constant is not True:
                        following += sequence(statement.orelse, [(*conditions, negate(test))], catches)
                elif isinstance(statement, ast.Return):
                    returned(statement.value, statement, conditions, catches)
                elif isinstance(statement, ast.Raise):
                    emit("throw", statement, conditions, catches, expression=expression(statement.exc) if statement.exc else "active exception (re-raise)",
                         caught_locally=declared_catch(statement.exc, catches), handling_basis="declared names/builtin hierarchy only; runtime binding unverified")
                    expressions(statement.exc, conditions, catches)
                elif isinstance(statement, (ast.Break, ast.Continue)):
                    pass
                elif isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
                    emit("unsupported-flow", statement, conditions, expression="Loop cardinality, termination and exit conditions unresolved")
                    source = statement.test if isinstance(statement, ast.While) else statement.iter
                    expressions(source, conditions, catches)
                    if not (isinstance(statement, ast.While) and isinstance(source, ast.Constant) and not source.value):
                        sequence(statement.body, [(*conditions, "loop: " + expression(source))], catches)
                    sequence(statement.orelse, [(*conditions, "loop completed without break; partial")], catches)
                    following.append((*conditions, "loop continuation partial; termination and breaks unresolved"))
                elif isinstance(statement, (ast.Try, ast.TryStar)):
                    first = len(facts)
                    handlers = tuple(expression(h.type) if h.type else "*" for h in statement.handlers)
                    normal = sequence(statement.body, [(*conditions, "try path; exception dispatch partial")] if handlers else [conditions], (*catches, *handlers))
                    if handlers:
                        emit("unsupported-flow", statement, conditions, expression="Exception dispatch/catch joins partial; matching declared names is not runtime binding proof")
                    normal = sequence(statement.orelse, normal, catches)
                    for handler in statement.handlers:
                        normal += sequence(handler.body, [(*conditions, "except " + expression(handler.type))], catches)
                    prior = facts[first:]
                    final_paths = sequence(statement.finalbody, [conditions], catches) if statement.finalbody else [conditions]
                    if exits(statement.finalbody):
                        for fact in prior:
                            if fact["kind"] in {"return", "throw"}:
                                fact["superseded_by_finally"] = True
                        following += final_paths
                    else:
                        if any(isinstance(n, (ast.Return, ast.Raise)) for s in statement.finalbody for n in ast.walk(s)):
                            emit("unsupported-flow", statement, conditions, expression="Conditional finally exit can override earlier exits; joins unresolved")
                            for fact in prior:
                                if fact["kind"] in {"return", "throw"}:
                                    fact["withheld_by_partial_finally"] = True
                            normal = [(*path, "finally continuation partial; earlier exits may be overridden") for path in normal]
                        following += normal
                elif isinstance(statement, (ast.With, ast.AsyncWith)):
                    for item in statement.items:
                        expressions(item.context_expr, conditions, catches)
                    following += sequence(statement.body, [conditions], catches)
                elif isinstance(statement, ast.Match):
                    emit("unsupported-flow", statement, conditions, expression="Match case reachability unresolved")
                    for case in statement.cases:
                        sequence(case.body, [(*conditions, "match case partial: " + expression(case.pattern))], catches)
                    following.append(conditions)
                else:
                    expressions(statement, conditions, catches)
                    following.append(conditions)
            paths, limited = merge_paths(following)
            if limited:
                emit("unsupported-flow", statement, (), expression="64 live-path limit; some continuations omitted")
        return paths
    sequence(node.body, [()])
    return facts


def js_facts(node, *, http_handler=False):
    from ..scanners.javascript import field, text, FUNCTIONS, walk
    facts = []
    body = field(node, "body")
    parameters = field(node, "parameters")
    response = None
    if http_handler and parameters and len(parameters.named_children) >= 2:
        parameter = parameters.named_children[1]
        pattern = field(parameter, "pattern") or parameter
        if pattern.type == "identifier":
            response = text(pattern)
    if response and body:
        # Reassignment/shadowing invalidates the simple response binding.
        for item in walk(body):
            bound = field(item, "left") if item.type in {"assignment_expression", "augmented_assignment_expression"} else field(item, "name") if item.type == "variable_declarator" else None
            if bound and text(bound) == response:
                response = None
                break
    def emit(kind, syntax, conditions, **data):
        if len(facts) < 499:
            facts.append({"kind":kind, "line":syntax.start_point.row + 1, "conditions":[str(c) for c in conditions], "condition_predicates":condition_predicates(conditions), **data})
        elif len(facts) == 499:
            facts.append({"kind":"unsupported-flow", "line":syntax.start_point.row + 1, "conditions":[], "expression":"500 local-fact limit; remaining syntax not interpreted"})
    def unwrap(value):
        while value and value.type == "parenthesized_expression" and len(value.named_children) == 1:
            value = value.named_children[0]
        return value
    # Admit only root-block const object bindings used as bare local returns.
    # Any other reference, shadowing, mutation or escape withholds the hint.
    object_bindings = {}
    if body and body.type == 'statement_block' and not node.has_error:
        candidates = []
        for declaration in body.named_children:
            if declaration.type != 'lexical_declaration' or declaration.children[0].type != 'const':
                continue
            for binding in declaration.named_children:
                name, value = field(binding, 'name'), unwrap(field(binding, 'value'))
                if name is None or name.type != 'identifier' or value is None or value.type != 'object':
                    continue
                candidates.append((name, binding, value))
        references, dynamic_eval = {}, False
        if candidates:
            for reference in walk(body):
                if reference.type in {'identifier', 'shorthand_property_identifier', 'shorthand_property_identifier_pattern'}:
                    references.setdefault(text(reference), []).append(reference)
                elif reference.type == 'call_expression' and text(field(reference, 'function')) == 'eval':
                    dynamic_eval = True
        if not dynamic_eval:
            for name, binding, value in candidates:
                valid = True
                for reference in references.get(text(name), []):
                    if reference == name:
                        continue
                    parent = reference.parent
                    owner = parent
                    while owner and owner.type not in FUNCTIONS:
                        owner = owner.parent
                    if owner != node or parent.type != 'return_statement':
                        valid = False
                        break
                if valid:
                    object_bindings[text(name)] = (binding, value)
    emitted_shapes = set()
    def response_payload(value):
        if not response or value is None or value.type != "call_expression":
            return None
        fn = field(value, "function")
        if fn is None or fn.type != "member_expression" or text(field(fn, "property")) not in {"json", "send"}:
            return None
        receiver = field(fn, "object")
        while receiver and receiver.type == "call_expression":
            chain = field(receiver, "function")
            if chain is None or chain.type != "member_expression" or text(field(chain, "property")) not in {"status", "code", "type", "header"}:
                return None
            receiver = field(chain, "object")
        if receiver is None or receiver.type != "identifier" or text(receiver) != response:
            return None
        arguments = field(value, "arguments")
        return unwrap(arguments.named_children[0]) if arguments and arguments.named_children else None
    def static_key(property):
        if property.type == 'shorthand_property_identifier':
            return text(property) if '\\' not in text(property) else None
        if property.type != 'pair':
            return None
        key = field(property, 'key')
        if key is None or key.type not in {'property_identifier', 'string'}:
            return None  # Numeric/computed keys need coercion or evaluation.
        raw = text(key)
        if '\\' in raw:
            return None  # Escapes are not decoded through another language.
        if key.type == 'string':
            if len(raw) < 2 or raw[0] not in {'\"', "'"} or raw[-1] != raw[0]:
                return None
            raw = raw[1:-1]
        return None if raw == '__proto__' else raw
    def fields(value):
        value = unwrap(value)
        if value is None or value.type != "object":
            return []
        return [key for p in value.named_children if (key := static_key(p)) is not None]
    def fields_complete(value):
        value = unwrap(value)
        if value is None or value.type != 'object':
            return False
        return all(p.type == 'comment' or static_key(p) is not None for p in value.named_children)
    def expressions(value, conditions, responses=True):
        if value is None or len(facts) >= 500 or value.type in FUNCTIONS | {"class_declaration"}:
            return
        value = unwrap(value)
        if value.type == "ternary_expression":
            test = text(field(value, "condition"))
            expressions(field(value, "condition"), conditions)
            expressions(field(value, "consequence"), (*conditions, test), responses)
            expressions(field(value, "alternative"), (*conditions, negate(test)), responses)
            return
        if value.type == "binary_expression" and text(field(value, "operator")) in {"&&", "||"}:
            left, right = field(value, "left"), field(value, "right")
            expressions(left, conditions, responses)
            guard = text(left) if text(field(value, "operator")) == "&&" else negate(text(left))
            expressions(right, (*conditions, guard), responses)
            return
        if value.type == "call_expression":
            args = field(value, "arguments")
            emit("call", value, conditions, callee=text(field(value, "function")), arguments=[text(a)[:1200] for a in args.named_children] if args else [])
            payload = response_payload(value)
            if responses and payload is not None:
                emit("response", value, conditions, expression=text(value)[:1200], output_fields=fields(payload), output_fields_complete=fields_complete(payload), basis="supported HTTP-handler response parameter call; execution unverified")
        for child in value.named_children:
            expressions(child, conditions, responses)
    def returned(value, syntax, conditions):
        value = unwrap(value)
        if value and value.type == "ternary_expression":
            test = text(field(value, "condition"))
            emit("branch", value, conditions, expression=test)
            expressions(field(value, "condition"), conditions)
            returned(field(value, "consequence"), syntax, (*conditions, test))
            returned(field(value, "alternative"), syntax, (*conditions, negate(test)))
            return
        payload = response_payload(value)
        shape, support = (payload if payload is not None else value), {}
        if value is not None and value.type == 'identifier' and text(value) in object_bindings:
            binding, initializer = object_bindings[text(value)]
            if binding.end_byte < syntax.start_byte:
                shape = initializer
                support = {'shape_source_line': binding.start_point.row + 1,
                           'shape_binding': text(value),
                           'shape_basis': 'root-block const object; no other binding/use, mutation or escape syntax observed'}
                if text(value) not in emitted_shapes:
                    emit('object-shape', binding, (), expression=text(initializer)[:1200], binding_name=text(value),
                         output_fields=fields(initializer), output_fields_complete=fields_complete(initializer))
                    emitted_shapes.add(text(value))
        emit("return", syntax, conditions, expression=text(value)[:1200] or "undefined", output_fields=fields(shape), output_fields_complete=fields_complete(shape), **support)
        expressions(value, conditions, payload is None)
    def exits(syntax):
        if syntax is None:
            return False
        if syntax.type in {"return_statement", "throw_statement"}:
            return True
        if syntax.type in {"statement_block", "else_clause", "finally_clause"}:
            children = [c for c in syntax.named_children if c.type != "comment"]
            return bool(children) and exits(children[-1])
        return syntax.type == "if_statement" and exits(field(syntax, "consequence")) and exits(field(syntax, "alternative"))
    def sequence(statements, paths):
        for statement in statements:
            if not paths or len(facts) >= 500:
                break
            following = []
            for conditions in paths:
                kind = statement.type
                if kind in {"statement_block", "else_clause", "catch_clause", "finally_clause"}:
                    following += sequence(statement.named_children, [conditions])
                elif kind == "if_statement":
                    test_node = field(statement, "condition")
                    test = text(test_node)
                    expressions(test_node, conditions)
                    emit("branch", statement, conditions, expression=test)
                    constant = text(unwrap(test_node))
                    if constant != "false":
                        following += sequence([field(statement, "consequence")], [(*conditions, test)])
                    alternative = field(statement, "alternative")
                    if constant != "true":
                        following += sequence([alternative], [(*conditions, negate(test))]) if alternative else [(*conditions, negate(test))]
                elif kind == "return_statement":
                    returned(statement.named_children[0] if statement.named_children else None, statement, conditions)
                elif kind == "throw_statement":
                    emit("throw", statement, conditions, expression=text(statement)[:1200])
                    for child in statement.named_children:
                        expressions(child, conditions)
                elif kind in {"break_statement", "continue_statement"}:
                    pass
                elif kind == "try_statement":
                    first = len(facts)
                    normal = sequence([field(statement, "body")], [(*conditions, "try path; exception dispatch partial")])
                    handler, finalizer = field(statement, "handler"), field(statement, "finalizer")
                    if handler:
                        for fact in facts[first:]:
                            if fact["kind"] == "throw": fact["caught_locally"] = True
                        normal += sequence([handler], [(*conditions, "catch path; dispatch partial")])
                    prior = facts[first:]
                    final_paths = sequence([finalizer], [conditions]) if finalizer else [conditions]
                    if exits(finalizer):
                        for fact in prior:
                            if fact["kind"] in {"return", "throw"}: fact["superseded_by_finally"] = True
                        following += final_paths
                    else:
                        if finalizer and any(n.type in {"return_statement", "throw_statement"} for n in walk(finalizer)):
                            emit("unsupported-flow", statement, conditions, expression="Conditional finally exit can override earlier exits; joins unresolved")
                            for fact in prior:
                                if fact["kind"] in {"return", "throw"}: fact["withheld_by_partial_finally"] = True
                            normal = [(*path, "finally continuation partial; earlier exits may be overridden") for path in normal]
                        following += normal
                elif kind in {"for_statement", "for_in_statement", "while_statement", "do_statement", "switch_statement"}:
                    emit("unsupported-flow", statement, conditions, expression="Loop/switch joins and reachability partial")
                    partial_path = (*conditions, "loop/switch path partial")
                    if kind != "switch_statement":
                        # Interpret only the loop body, never flatten switch cases or loop arms.
                        body = field(statement, "body")
                        if body:
                            sequence([body], [partial_path])
                        for name in ("condition", "initializer", "increment", "left", "right"):
                            expressions(field(statement, name), partial_path)
                    following.append((*conditions, "loop continuation partial; termination and breaks unresolved"))
                elif kind in FUNCTIONS | {"class_declaration"}:
                    following.append(conditions)
                else:
                    expressions(statement, conditions)
                    following.append(conditions)
            paths, limited = merge_paths(following)
            if limited:
                emit("unsupported-flow", statement, (), expression="64 live-path limit; some continuations omitted")
        return paths
    if body:
        if node.type == "arrow_function" and body.type != "statement_block":
            returned(body, body, ())
        else:
            sequence(body.named_children, [()])
    return facts
