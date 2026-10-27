from __future__ import annotations
from pathlib import Path
import ast
from collections import Counter
from .filesystem import iter_owned_files
from ..model import FactGraph, Node, Edge, Evidence

ROUTE_DECORATORS = {"get":"GET","post":"POST","put":"PUT","patch":"PATCH","delete":"DELETE","options":"OPTIONS","head":"HEAD"}
CONTROL_HINTS = {
    "login_required":"authentication",
    "permission_required":"authorization",
    "requires_auth":"authentication",
    "authorize":"authorization",
    "authenticated":"authentication",
    "validator":"validation",
    "validate":"validation",
}

def _name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = _name(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    if isinstance(node, ast.Call):
        return _name(node.func)
    return ""

def _str_arg(call):
    if not isinstance(call, ast.Call) or not call.args:
        return ""
    a = call.args[0]
    return a.value if isinstance(a, ast.Constant) and isinstance(a.value, str) else ""

def _literal_string(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _scope_nodes(tree):
    pending = list(reversed(tree.body))
    while pending:
        node = pending.pop()
        yield node
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            pending.extend(reversed(list(ast.iter_child_nodes(node))))


def _parameters(node):
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return set()
    args = node.args
    return {arg.arg for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs, args.vararg, args.kwarg] if arg}


def scoped_function_declarations(statements, context=()):
    """Index conditional declarations without asserting their runtime availability.

    Stop at callable/class boundaries: descendants belong to their own scope.
    Context is source syntax, not a solved predicate or an execution trace.
    """
    for statement in statements:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield statement, context
        elif isinstance(statement, ast.ClassDef):
            continue
        elif isinstance(statement, ast.If):
            for branch, body in (("then", statement.body), ("else", statement.orelse)):
                clause = {"kind": "if", "expression": ast.unparse(statement.test), "branch": branch,
                          "line": statement.lineno}
                yield from scoped_function_declarations(body, (*context, clause))
        else:
            # Loops, try handlers/finally, with and match arms are inventoried,
            # but their reachability, exception dispatch and iteration are unknown.
            for field_name, value in ast.iter_fields(statement):
                if not isinstance(value, list):
                    continue
                for child in value:
                    if isinstance(child, (ast.ExceptHandler, ast.match_case)):
                        body = child.body
                    elif isinstance(child, ast.stmt):
                        body = [child]
                    else:
                        continue
                    clause = {"kind": type(statement).__name__, "branch": field_name,
                              "line": statement.lineno}
                    yield from scoped_function_declarations(body, (*context, clause))


def _flask_bindings(tree, inherited_imports=None, inherited_bindings=None):
    """Literal Flask declarations in one lexical scope; target code is never executed."""
    imports = dict(inherited_imports or {})
    bindings = {name: {**value, "prefixes": list(value["prefixes"])}
                for name, value in (inherited_bindings or {}).items()}
    scope_nodes = list(_scope_nodes(tree))
    stores = Counter(n.id for n in scope_nodes if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store))
    stores.update(n.name for n in scope_nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
    stores.update(_parameters(tree))
    for name in stores:
        bindings.pop(name, None)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                imports.pop(name, None)
                bindings.pop(name, None)
                if node.module == "flask":
                    imports[name] = "flask." + alias.name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                imports.pop(name, None)
                bindings.pop(name, None)
                if alias.name == "flask":
                    imports[name] = alias.name
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)) or not isinstance(node.value, ast.Call):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        local, *members = _name(node.value.func).split(".")
        imported = imports.get(local)
        constructor = ".".join([imported, *members]) if imported and not stores[local] else ""
        if constructor not in {"flask.Flask", "flask.Blueprint"}:
            continue
        options = {k.arg: k.value for k in node.value.keywords}
        prefix = _literal_string(options["url_prefix"]) if "url_prefix" in options else ""
        if isinstance(options.get("url_prefix"), ast.Constant) and options["url_prefix"].value is None:
            prefix = ""
        if None in options or prefix and not prefix.startswith("/"):
            prefix = None
        for target in targets:
            if isinstance(target, ast.Name):
                bindings[target.id] = {"kind": constructor, "prefixes": [prefix if stores[target.id] == 1 else None]}
    registrations = {}
    for node in scope_nodes:
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != "register_blueprint" or not node.args:
            continue
        name = _name(node.args[0])
        if name not in bindings or bindings[name]["kind"] != "flask.Blueprint":
            continue
        options = {k.arg: k.value for k in node.keywords}
        prefixes = bindings[name]["prefixes"]
        if "url_prefix" in options and not (isinstance(options["url_prefix"], ast.Constant) and options["url_prefix"].value is None):
            prefixes = [_literal_string(options["url_prefix"])]
        parent = bindings.get(_name(node.func.value), {})
        if None in options or parent.get("kind") == "flask.Blueprint":
            prefixes = [None]  # Nested mounts or arbitrary registration options are not resolved.
        registrations.setdefault(name, []).extend(prefixes)
    for name, prefixes in registrations.items():
        bindings[name]["prefixes"] = list(dict.fromkeys(prefixes))
    return bindings, imports


def scan_python(root: Path) -> FactGraph:
    graph = FactGraph()
    module_nodes = {}
    symbol_nodes = {}
    parsed = {}
    function_nodes = {}
    class_nodes = {}

    py_files = [p for p in iter_owned_files(root) if p.suffix == ".py"]
    for p in py_files:
        rel = p.relative_to(root).as_posix()
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="ignore"), filename=rel)
        except OSError:
            from .filesystem import source_unavailable
            source_unavailable(root,p,graph)
            continue
        except SyntaxError:
            graph.coverage[rel] = {"status": "UNKNOWN", "basis": "Python syntax error", "omitted_count": None}
            graph.unknowns.append({"path": rel, "reason": "python_syntax_error", "state": "UNKNOWN"})
            continue
        graph.coverage[rel] = {"status": "ANALYZED", "basis": "Python AST declarations; scoped call resolution remains partial", "relationships": "PARTIAL", "omitted_count": 0}
        parsed[rel] = tree
        flask_bindings, flask_imports = _flask_bindings(tree)
        module_name = ".".join(Path(rel).with_suffix("").parts)
        mid = f"module:{module_name}"
        module_nodes[rel] = mid
        graph.add_node(Node(mid, "module", module_name, rel, {"language":"Python"}, Evidence(evidence=[rel])))

        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if isinstance(node, ast.ClassDef):
                    kind = "class"
                    decorators = [_name(d) for d in node.decorator_list]
                    bases = [_name(b) for b in node.bases]
                    nid = f"type:{module_name}:{node.name}"
                    class_nodes[(rel, id(node))] = nid
                    graph.add_node(Node(
                        nid, kind, node.name, rel,
                        {"decorators":decorators,"bases":bases,"language":"Python"},
                        Evidence(evidence=[f"{rel}:{node.lineno}"])
                    ))
                    symbol_nodes[(rel,node.name)] = nid
                    graph.add_edge(Edge(mid,nid,"declares",[f"{rel}:{node.lineno}"]))

                    for child in node.body:
                        if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef)):
                            fid = f"method:{module_name}:{node.name}#{child.name}"
                            function_nodes[(rel, id(child))] = fid
                            decs = [_name(d) for d in child.decorator_list]
                            graph.add_node(Node(
                                fid,"method",child.name,rel,
                                {"owner":nid,"decorators":decs,"async":isinstance(child,ast.AsyncFunctionDef)},
                                Evidence(evidence=[f"{rel}:{child.lineno}"])
                            ))
                            graph.add_edge(Edge(nid,fid,"declares",[f"{rel}:{child.lineno}"]))
                            _decorator_semantics(graph, fid, child.decorator_list, rel, child.lineno, flask_bindings)
                else:
                    fid = f"function:{module_name}:{node.name}"
                    function_nodes[(rel, id(node))] = fid
                    decs = [_name(d) for d in node.decorator_list]
                    graph.add_node(Node(
                        fid,"function",node.name,rel,
                        {"decorators":decs,"async":isinstance(node,ast.AsyncFunctionDef)},
                        Evidence(evidence=[f"{rel}:{node.lineno}"])
                    ))
                    symbol_nodes[(rel,node.name)] = fid
                    graph.add_edge(Edge(mid,fid,"declares",[f"{rel}:{node.lineno}"]))
                    _decorator_semantics(graph, fid, node.decorator_list, rel, node.lineno, flask_bindings)

        def nested_functions(parent, owner, qualified, inherited_bindings, inherited_imports, module_scope=False, inherited_context=()):
            bindings, imports = _flask_bindings(parent, inherited_imports, inherited_bindings)
            occurrences = Counter()
            for child, immediate_context in scoped_function_declarations(parent.body):
                declaration_context = (*inherited_context, *immediate_context)
                if module_scope and not declaration_context:
                    continue
                name = qualified + "." + child.name if qualified else child.name
                ordinal = occurrences[child.name]
                occurrences[child.name] += 1
                suffix = f":declaration:{child.lineno}" if declaration_context else (f":occurrence:{ordinal}" if ordinal else "")
                fid = f"function:{module_name}:{name}" + suffix
                function_nodes[(rel, id(child))] = fid
                graph.add_node(Node(
                    fid, "function", child.name, rel,
                    {"owner": owner, "identity_scope": qualified, "is_nested": not module_scope,
                     "conditional_declaration": bool(declaration_context), "declaration_context": list(declaration_context),
                     "decorators": [_name(d) for d in child.decorator_list],
                     "async": isinstance(child, ast.AsyncFunctionDef)},
                    Evidence(evidence=[f"{rel}:{child.lineno}"])
                ))
                graph.add_edge(Edge(owner, fid, "declares", [f"{rel}:{child.lineno}"]))
                if declaration_context:
                    graph.unknowns.append({'path': rel, 'line': child.lineno, 'entity_ref': fid,
                                           'reason': 'python_conditional_declaration_unresolved',
                                           'state': 'UNKNOWN',
                                           'basis': 'Body indexed; runtime availability and conditional registration unresolved'})
                if not declaration_context:
                    _decorator_semantics(graph, fid, child.decorator_list, rel, child.lineno, bindings, name)
                nested_functions(child, fid, name, bindings, imports, inherited_context=declaration_context)

        nested_functions(tree, mid, "", flask_bindings, flask_imports, module_scope=True)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nested_functions(node, function_nodes[(rel, id(node))], node.name, flask_bindings, flask_imports)
            elif isinstance(node, ast.ClassDef):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        nested_functions(child, function_nodes[(rel, id(child))], node.name + "." + child.name,
                                         flask_bindings, flask_imports)

        # ORM-ish entities: SQLAlchemy/Django model inheritance
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                bases = [_name(b) for b in node.bases]
                if any("Model" in b or "Base" == b.split(".")[-1] for b in bases):
                    nid = symbol_nodes.get((rel,node.name))
                    if nid:
                        for n in graph.nodes:
                            if n.id == nid:
                                n.kind = "entity"
                                n.metadata["orm_hint"] = bases
                                break

        # Pytest/unittest-style tests
        low = rel.lower()
        for node in ast.walk(tree):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and (
                node.name.startswith("test_") or "/test" in low or "/tests/" in low
            ):
                tid = f"test:{module_name}:{node.name}:{node.lineno}"
                graph.add_node(Node(
                    tid,"test",node.name,rel,{"framework":"pytest/unittest-like"},
                    Evidence(evidence=[f"{rel}:{node.lineno}"])
                ))

    # imports + calls
    name_to_node = {}
    nodes_by_id = {}
    for n in graph.nodes:
        if n.kind in {"class","entity","function","method","module"} and not n.metadata.get("is_nested") and not n.metadata.get("conditional_declaration"):
            name_to_node.setdefault(n.name, []).append(n.id)
        nodes_by_id[n.id] = n
    lexical_symbols = {}
    conditional_symbols = set()
    for edge in graph.edges:
        if edge.relation == "declares" and edge.target in nodes_by_id:
            target = nodes_by_id[edge.target]
            if target.metadata.get("conditional_declaration"):
                conditional_symbols.add((edge.source, target.name))
            else:
                lexical_symbols.setdefault((edge.source, target.name), []).append(target.id)

    for rel, tree in parsed.items():
        mid = module_nodes[rel]
        imports = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports[alias.asname or alias.name.split(".")[0]] = alias.name
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    imports[alias.asname or alias.name] = f"{mod}.{alias.name}".strip(".")
        # Full dotted import targets, including third-party ones that resolve to nothing in
        # this repo (the `imports` dict below only uses these to wire in-repo edges and drops
        # the rest) — kept here, same shape as the Java/TS scanners' node.metadata["imports"],
        # so a later pass (external systems) can allowlist-match without a new parser.
        nodes_by_id[mid].metadata["imports"] = sorted(set(imports.values()))
        for local, full in imports.items():
            simple = full.split(".")[-1]
            for target in name_to_node.get(simple, []):
                graph.add_edge(Edge(mid,target,"imports",[rel]))

        # Calls are attributed to nearest enclosing function/method when possible.
        class Visitor(ast.NodeVisitor):
            def __init__(self):
                self.scope = [mid]
                self.shadows = [set()]
            def visit_ClassDef(self, node):
                nid = class_nodes.get((rel, id(node)))
                if nid is None:
                    graph.unknowns.append({"path": rel, "line": node.lineno, "reason": "python_nested_class_scope_unresolved", "state": "UNKNOWN"})
                    return
                self.scope.append(nid)
                self.shadows.append(set())
                for ch in node.body: self.visit(ch)
                self.scope.pop()
                self.shadows.pop()
            def visit_FunctionDef(self, node):
                sid = function_nodes.get((rel, id(node)))
                if sid is None:
                    graph.unknowns.append({"path": rel, "line": node.lineno, "reason": "python_conditional_declaration_unresolved", "state": "UNKNOWN"})
                    return
                self.scope.append(sid)
                self.shadows.append(_parameters(node) | {n.id for n in _scope_nodes(node)
                                                        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)})
                for ch in node.body: self.visit(ch)
                self.scope.pop()
                self.shadows.pop()
            visit_AsyncFunctionDef = visit_FunctionDef
            def visit_Call(self, node):
                called = _name(node.func)
                simple = called.split(".")[-1]
                candidates = name_to_node.get(simple, [])
                if isinstance(node.func, ast.Name):
                    for owner, shadowed in reversed(list(zip(self.scope, self.shadows))):
                        if simple in shadowed:
                            candidates = []
                            graph.unknowns.append({"path": rel, "line": node.lineno, "reason": "python_shadowed_call", "state": "UNKNOWN"})
                            break
                        if (owner, simple) in conditional_symbols:
                            candidates = []
                            graph.unknowns.append({'path': rel, 'line': node.lineno,
                                                   'reason': 'python_conditional_call_binding_unresolved', 'state': 'UNKNOWN'})
                            break
                        if (owner, simple) in lexical_symbols:
                            candidates = lexical_symbols[(owner, simple)]
                            break
                if len(candidates) > 1:
                    graph.unknowns.append({"path": rel, "line": node.lineno, "reason": "python_ambiguous_call", "state": "UNKNOWN"})
                for target in candidates if len(candidates) == 1 else []:
                    if target != self.scope[-1]:
                        graph.add_edge(Edge(self.scope[-1],target,"calls",[f"{rel}:{getattr(node,'lineno',0)}"]))
                self.generic_visit(node)
        Visitor().visit(tree)
        from .python_http import recover_dispatch_tables
        recover_dispatch_tables(tree, graph, rel, ".".join(Path(rel).with_suffix("").parts), function_nodes)

    return graph

def _decorator_semantics(graph, owner_id, decorators, rel, lineno, flask_bindings=None, identity_scope=None):
    flask_bindings = flask_bindings or {}
    for d in decorators:
        name = _name(d)
        low = name.lower().split(".")[-1]
        receiver = _name(d.func.value) if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) else ""
        binding = flask_bindings.get(receiver)
        # Existing direct method decorators, plus imported Flask/Blueprint.route declarations.
        method = low
        if isinstance(d, ast.Call) and (method in ROUTE_DECORATORS or method == "route" and binding):
            options = {k.arg: k.value for k in d.keywords}
            rule = _literal_string(d.args[0]) if d.args else _literal_string(options.get("rule"))
            methods = [ROUTE_DECORATORS[method]] if method in ROUTE_DECORATORS else ["GET"]
            if method == "route" and "methods" in options:
                value = options["methods"]
                methods = [_literal_string(item) for item in value.elts] if isinstance(value, (ast.List, ast.Tuple, ast.Set)) else [None]
            prefixes = binding["prefixes"] if binding else [""]
            if (rule is None or not rule.startswith("/") or None in options or not methods or
                    any(not item or not item.isascii() or not item.isalpha() for item in methods)):
                graph.unknowns.append({"path": rel, "line": lineno, "reason": "python_flask_route_rule_or_methods_unresolved", "state": "UNKNOWN"})
                continue
            for prefix in prefixes:
                if prefix is None or prefix and not prefix.startswith("/"):
                    graph.unknowns.append({"path": rel, "line": lineno, "reason": "python_flask_blueprint_prefix_unresolved", "state": "UNKNOWN"})
                    continue
                path = prefix.rstrip("/") + rule
                for http_method in sorted({item.upper() for item in methods}):
                    route_id = f"route:{http_method}:{path}:{rel}:{lineno}"
                    graph.add_node(Node(
                        route_id, "route", f"{http_method} {path}", rel,
                        {"http_method": http_method, "path": path, "handler": owner_id,
                         "framework": "Flask" if binding else "Python web framework-like",
                         "route_scope": "declared-static", "implicit_methods": "not-expanded",
                         "registration_basis": "lexical declarations and literal local mounts; external mounts unverified",
                         **({"identity_scope": identity_scope} if identity_scope else {})},
                        Evidence(evidence=[f"{rel}:{lineno}"])
                    ))
                    graph.add_edge(Edge(route_id, owner_id, "handled_by", [f"{rel}:{lineno}"]))
        for hint, control in CONTROL_HINTS.items():
            if hint in low:
                cid = f"control:{control}:{owner_id}:{low}"
                graph.add_node(Node(
                    cid,"control",low,rel,
                    {"control_type":control,"target":owner_id},
                    Evidence(evidence=[f"{rel}:{lineno}"])
                ))
                graph.add_edge(Edge(cid,owner_id,"protects",[f"{rel}:{lineno}"]))
