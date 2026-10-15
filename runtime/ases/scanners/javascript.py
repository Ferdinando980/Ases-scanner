"""Inert JS/TS syntax and conservative lexical/module binding. Never imports the target."""
from __future__ import annotations

from importlib.metadata import version
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit, urlunsplit
from tree_sitter import Language, Parser
import tree_sitter_javascript as js
import tree_sitter_typescript as ts

from .filesystem import iter_owned_files
from ..model import FactGraph, Node, Edge, Evidence
from ..source_roles import classify_source
from ..evidence import digest

EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"}
FUNCTIONS = {"function_declaration", "function_expression", "arrow_function", "method_definition", "generator_function_declaration"}
SCOPES = FUNCTIONS | {"program", "statement_block", "class_body", "catch_clause"}
MAX_BYTES = 5 * 1024 * 1024
MAX_NODES = 200000
MAX_BINDING_DEPTH = 128
LANGUAGES = {"js": Language(js.language()), "ts": Language(ts.language_typescript()), "tsx": Language(ts.language_tsx())}
HTTP = {x: x.upper() for x in ("get", "post", "put", "patch", "delete", "options", "head", "all")}
HTTP["all"] = "ANY"
# Exact npm package roots: an arbitrary imported utility is not a service client.
SERVICE_CLIENT_PACKAGES = {
    "openai", "@anthropic-ai/sdk", "stripe", "aws-sdk", "@supabase/supabase-js",
    "twilio", "@sendgrid/mail", "@sendgrid/client", "firebase", "firebase-admin",
}


def parser_profile():
    return {**{name: version(name) for name in ("tree-sitter", "tree-sitter-javascript", "tree-sitter-typescript")},
            "limits": {"source_bytes": MAX_BYTES, "named_nodes": MAX_NODES, "binding_depth": MAX_BINDING_DEPTH},
            "imported_calls": "module-call/2"}


def parse(text, suffix):
    language = "tsx" if suffix == ".tsx" else ("ts" if suffix in {".ts", ".mts", ".cts"} else "js")
    data = text.encode("utf-8")
    if len(data) > MAX_BYTES:
        raise ValueError("source_byte_limit")
    return Parser(LANGUAGES[language]).parse(data).root_node


def walk(node):
    stack = [node]
    count = 0
    while stack:
        current = stack.pop()
        count += 1
        if count > MAX_NODES:
            raise ValueError("syntax_node_limit")
        yield current
        stack.extend(reversed(current.named_children))


def text(node):
    return node.text.decode("utf-8") if node is not None else ""


def field(node, name):
    return node.child_by_field_name(name)


def key(node):
    return (node.type, node.start_byte, node.end_byte)


def scope(node, include_self=False):
    node = node if include_self else node.parent
    while node is not None and node.type not in SCOPES:
        node = node.parent
    return key(node) if node is not None else None


def ancestors(node):
    node = node.parent
    while node is not None:
        yield node
        node = node.parent


def pattern_names(pattern):
    """Only identifiers introduced by a binding pattern, excluding initializer expressions."""
    pending = [pattern] if pattern is not None else []
    while pending:
        node = pending.pop()
        if node.type in {"identifier", "shorthand_property_identifier_pattern"}:
            yield text(node)
        elif node.type in {"assignment_pattern", "object_assignment_pattern"}:
            left = field(node, "left")
            if left is not None:
                pending.append(left)
        elif node.type == "pair_pattern":
            value = field(node, "value")
            if value is not None:
                pending.append(value)
        elif node.type in {"object_pattern", "array_pattern", "rest_pattern"}:
            pending.extend(node.named_children)


def literal(node):
    if node is None or node.type not in {"string", "template_string"}:
        return None
    if any(n.type in {"template_substitution", "escape_sequence"} for n in node.named_children):
        return None
    return text(node)[1:-1]


def tokens(node):
    result, pending = [], [node] if node is not None else []
    while pending:
        current = pending.pop()
        if current.type == "comment":
            continue
        if current.type in {"string", "template_string"} and literal(current) is not None:
            result.append(("literal-sha256", digest(literal(current))))
        elif not current.children:
            result.append((current.type, text(current)))
        else:
            pending.extend(reversed(current.children))
    return result


def safe_endpoint(value):
    parts = urlsplit(value)
    host = parts.netloc.rsplit("@", 1)[-1]
    return urlunsplit((parts.scheme, host, parts.path, "", ""))


def args(node):
    arguments = field(node, "arguments")
    return arguments.named_children if arguments is not None else []


def decorators(node):
    rows = [n for n in node.named_children if n.type == "decorator"]
    # TS method decorators are siblings in the class body.
    previous = node.prev_named_sibling
    while previous is not None and previous.type == "decorator":
        rows.insert(0, previous)
        previous = previous.prev_named_sibling
    result = []
    for decorator in rows:
        expression = decorator.named_children[0] if decorator.named_children else None
        result.append((text(field(expression, "function")) if expression is not None and expression.type == "call_expression" else text(expression),
                       args(expression) if expression is not None and expression.type == "call_expression" else []))
    return result


def syntax_text(source, suffix, remove_strings=False):
    """Preserve offsets while withholding comments (and optionally literal contents) from legacy rules."""
    data = bytearray(source.encode("utf-8"))
    root = parse(source, suffix)
    for n in walk(root):
        if n.type == "comment" or (remove_strings and n.type in {"string", "template_string"}):
            for index in range(n.start_byte, n.end_byte):
                if data[index] not in {10, 13}:
                    data[index] = 32
    return data.decode("utf-8")


def request_site(node, method, target, occurrences):
    """Lexical callsite identity shared by backend/frontend; positions are evidence only."""
    owners = []
    for owner in ancestors(node):
        if owner.type == "class_declaration":
            owners.append(["class", text(field(owner, "name"))])
        elif owner.type in FUNCTIONS:
            name = text(field(owner, "name"))
            if owner.parent.type == "variable_declarator":
                name = text(field(owner.parent, "name"))
            if not name:
                call = next((n for n in ancestors(owner) if n.type == "call_expression"), None)
                name = "callback:" + re.sub(r"\s+", "", text(field(call, "function"))) if call else "anonymous"
                if call and args(call):
                    name += ":" + (literal(args(call)[0]) or "dynamic")
            owners.append([name, tokens(field(owner, "parameters") or field(owner, "parameter"))])
    anchor = digest([list(reversed(owners)), method, target])
    index = occurrences.get(anchor, 0)
    occurrences[anchor] = index + 1
    return f"request-site/2:{anchor}:{index}"


def api_calls(source, suffix):
    """Literal requests with lexical client authority; syntax never establishes execution."""
    root = parse(source, suffix)
    ast = list(walk(root))
    bindings, members = {}, {}
    missing = object()

    def bind(node, name, authority=None, where=None):
        bindings[(where if where is not None else scope(node), name)] = authority

    def lookup(node, name):
        for owner in ancestors(node):
            token = (key(owner), name)
            if owner.type in SCOPES and token in bindings:
                return bindings[token]
        return missing

    def client_import(source, symbol, type_only):
        if source == "@angular/common/http" and symbol == "HttpClient":
            return "angular-http-type"
        if not type_only and symbol in {"default", "*"}:
            return {"axios": "axios", "jquery": "jquery"}.get(source)
        return None

    for node in ast:
        if node.type == "import_statement":
            source_name = literal(field(node, "source"))
            typed = bool(re.match(r"import\s+type\b", text(node)))
            for child in walk(node):
                if child.type == "import_specifier":
                    local = text(field(child, "alias") or field(child, "name"))
                    bind(node, local, client_import(source_name, text(field(child, "name")), typed or text(child).startswith("type ")))
                elif child.type == "namespace_import":
                    bind(node, text(child.named_children[-1]), client_import(source_name, "*", typed))
                elif child.type == "import_clause":
                    for part in child.named_children:
                        if part.type == "identifier":
                            bind(node, text(part), client_import(source_name, "default", typed))
        elif node.type == "variable_declarator":
            for name in pattern_names(field(node, "name")):
                # var is function scoped, including declarations nested in blocks.
                owner = next((n for n in ancestors(node) if n.type in FUNCTIONS | {"program"}), None)
                bind(node, name, where=key(owner) if node.parent.type == "variable_declaration" and owner else None)
        elif node.type in FUNCTIONS | {"class_declaration", "catch_clause"}:
            name = field(node, "name")
            if name is not None and node.type != "method_definition":
                bind(node, text(name), where=key(node) if node.type == "function_expression" else None)
            params = field(node, "parameters") or field(node, "parameter")
            if params is not None:
                for parameter in (params.named_children if params.type == "formal_parameters" else [params]):
                    pattern = field(parameter, "pattern") or field(parameter, "name") or parameter
                    for name in pattern_names(pattern):
                        bind(node, name, where=key(node))
    # Constructor parameter properties and fields admit HttpClient through its imported type.
    for node in ast:
        cls = next((n for n in ancestors(node) if n.type == "class_declaration"), None)
        if cls is not None and node.type in {"required_parameter", "optional_parameter", "public_field_definition"}:
            name = field(node, "pattern") or field(node, "name")
            annotation = field(node, "type")
            type_name = text(annotation).lstrip(":").strip()
            property_parameter = node.type == "public_field_definition" or any(n.type == "accessibility_modifier" for n in node.named_children)
            if property_parameter and name is not None:
                members[(key(cls), text(name))] = "angular-http" if lookup(node, type_name) == "angular-http-type" else None
        if node.type == "variable_declarator":
            name, value = field(node, "name"), field(node, "value")
            if name is not None and name.type == "identifier" and value is not None and value.type == "call_expression" and text(field(value, "function")) == "require" and lookup(node, "require") is missing:
                imported = literal(args(value)[0]) if args(value) else None
                bind(node, text(name), client_import(imported, "*", False))
    # Any mutation invalidates the binding throughout this static snapshot, regardless of order.
    for node in ast:
        if node.type not in {"assignment_expression", "augmented_assignment_expression", "update_expression"}:
            continue
        left = field(node, "left") or field(node, "argument")
        if left is None:
            continue
        value = re.sub(r"\s+", "", text(left))
        if value.startswith("this."):
            cls = next((n for n in ancestors(node) if n.type == "class_declaration"), None)
            if cls is not None:
                members[(key(cls), value.split(".")[1])] = None
        else:
            name = value.split(".")[0].split("[")[0]
            for owner in ancestors(node):
                token = (key(owner), name)
                if owner.type in SCOPES and token in bindings:
                    bindings[token] = None
                    break
            else:
                bind(node, name, where=key(root))
    for node in ast:
        if node.type != "call_expression":
            continue
        fn = text(field(node, "function"))
        fn = re.sub(r"\s+", "", fn)
        arguments = args(node)
        target = literal(arguments[0]) if arguments else None
        method = "GET"
        if fn == "fetch":
            if lookup(node, "fetch") is not missing:
                continue
            if len(arguments) > 1 and arguments[1].type == "object":
                for pair in arguments[1].named_children:
                    if text(field(pair, "key")) in {"method", "'method'", '"method"'}:
                        method = literal(field(pair, "value")) or "UNKNOWN"
        else:
            member = re.fullmatch(r"((?:this\.)?[A-Za-z_$][\w$]*)\.(get|post|put|patch|delete|ajax)", fn)
            if member is None:
                continue
            receiver, operation = member.groups()
            if receiver.startswith("this."):
                cls = next((n for n in ancestors(node) if n.type == "class_declaration"), None)
                owners = list(ancestors(node))
                before_class = owners[:owners.index(cls)] if cls is not None else []
                rebound_this = any(n.type in FUNCTIONS - {"arrow_function", "method_definition"} or
                                   n.type == "method_definition" and n.parent.type != "class_body" for n in before_class)
                authority = members.get((key(cls), receiver[5:])) if cls is not None and not rebound_this else None
            else:
                authority = lookup(node, receiver)
            if operation == "ajax" and authority == "jquery" and arguments and arguments[0].type == "object":
                values = {text(field(p, "key")).strip("\"'"): literal(field(p, "value")) for p in arguments[0].named_children}
                target, method = values.get("url"), values.get("method") or values.get("type") or "GET"
            elif operation != "ajax" and authority in {"axios", "angular-http"}:
                method = operation.upper()
            else:
                continue
        if target is not None:
            yield node, method.upper(), safe_endpoint(target)


def scan_javascript(root: Path) -> FactGraph:
    root = root.absolute().resolve()
    graph = FactGraph()
    id_counts = {}
    records, bindings, exports, callable_nodes, classes, instance_types = {}, {}, {}, {}, {}, {}
    star_exports = {}
    export_limits = set()
    module_cache = {}
    pubsub_instances, pubsub_constructors, mutated_members = {}, {}, set()

    def unknown(rel, node, reason):
        graph.unknowns.append({"path": rel, "line": node.start_point.row + 1 if node else None,
                               "reason": reason, "state": "UNKNOWN"})

    def evidence(rel, node):
        return [f"{rel}:{node.start_point.row + 1}"]

    def bind(rel, ast_node, name, value, where=None):
        bindings[(rel, where if where is not None else scope(ast_node), name)] = value

    def binding_key(rel, ast_node, name):
        scopes = [key(n) for n in ancestors(ast_node) if n.type in SCOPES]
        for sk in scopes:
            if (rel, sk, name) in bindings:
                return (rel, sk, name)

    def lookup(rel, ast_node, name):
        token = binding_key(rel, ast_node, name)
        return (bindings[token] or "<unresolved-binding>") if token is not None else None

    def module(source, rel):
        cache_key = (source, rel)
        if cache_key in module_cache:
            return module_cache[cache_key]
        if not source.startswith("."):
            return None
        # Resolve only against the admitted inventory, never through the filesystem.
        import os
        base = Path(os.path.normpath(root / PurePosixPath(rel).parent / source))
        if not base.is_relative_to(root):
            return None
        candidates = {base}
        if base != root and base.suffix in {".js", ".mjs", ".cjs"}:
            candidates.add(base.with_suffix({".js": ".ts", ".mjs": ".mts", ".cjs": ".cts"}[base.suffix]))
        elif base == root or base.suffix not in EXTENSIONS:
            candidates |= {Path(str(base) + ext) for ext in EXTENSIONS}
            candidates |= {base / ("index" + ext) for ext in EXTENSIONS}
        # Appending an extension to the repository root produces a sibling, not a module.
        candidates = {path.relative_to(root).as_posix() for path in candidates if path.is_relative_to(root)}
        found = sorted(candidates & records.keys())
        module_cache[cache_key] = found[0] if len(found) == 1 else None
        return module_cache[cache_key]

    def export_candidates(target, symbol, seen):
        token = (target, symbol)
        if len(seen) >= MAX_BINDING_DEPTH:
            if token not in export_limits:
                export_limits.add(token)
                unknown(target, None, "export_resolution_limit")
            return {None}
        if token in seen:
            return set()
        seen = seen | {token}
        if token in exports:  # An explicit export shadows every star, even when unresolved.
            value = exports[token]
            if isinstance(value, tuple):
                source, remote, typed = value
                destination = module(source, target)
                return export_candidates(destination, remote, seen) if destination and not typed else {None}
            return {value}
        if symbol == "default":
            return set()
        candidates = set()
        for source in star_exports.get(target, []):
            destination = module(source, target)
            candidates.update(export_candidates(destination, symbol, seen) if destination else {None})
        return candidates

    def resolve(value, rel, seen=None):
        seen = set() if seen is None else seen
        if not isinstance(value, tuple):
            return value
        source, symbol, type_only = value
        if type_only:
            return None
        target = module(source, rel)
        token = (target, symbol)
        if target is None or token in seen or symbol == "*":
            return None
        candidates = export_candidates(target, symbol, seen)
        return next(iter(candidates)) if len(candidates) == 1 else None

    # Inventory and parsing are bounded independently of query delivery.
    for path in sorted(iter_owned_files(root)):
        if path.suffix.lower() not in EXTENSIONS:
            continue
        rel = path.relative_to(root).as_posix()
        try:
            if path.stat().st_size > MAX_BYTES:
                raise ValueError("source_byte_limit")
            source = path.read_bytes().decode("utf-8")
            tree = parse(source, path.suffix.lower())
            ast = list(walk(tree))
        except (ValueError, UnicodeError) as exc:
            graph.coverage[rel] = {"status": "UNKNOWN", "basis": str(exc), "omitted_count": None}
            unknown(rel, None, str(exc))
            continue
        meta = classify_source(rel, root)
        mid = f"module:javascript:{rel}"
        graph.add_node(Node(mid, "javascript_module", path.stem, rel,
                            {"language": "TypeScript" if path.suffix in {".ts", ".tsx", ".mts", ".cts"} else "JavaScript",
                             "scope": meta["scope"], "source_role": meta["role"], "is_test_code": meta["role"] == "TEST",
                             "extraction_method": "tree-sitter"}, Evidence(evidence=[rel])))
        graph.coverage[rel] = {"status": "PARTIAL" if tree.has_error else "ANALYZED",
                               "basis": "Tree-sitter declarations in admitted syntax; runtime unverified",
                               "relationships": "PARTIAL", "omitted_count": None if tree.has_error else 0}
        if tree.has_error:
            unknown(rel, tree, "parser_recovery")
        records[rel] = {"tree": tree, "ast": ast, "mid": mid, "source": source, "meta": meta}

    for rel, record in records.items():
        imports = []
        for node in record["ast"]:
            if node.type == "import_statement":
                source = literal(field(node, "source"))
                if source is None:
                    continue
                imports.append(source)
                type_only = bool(re.match(r"import\s+type\b", text(node)))
                for child in walk(node):
                    if child.type == "import_specifier":
                        local = text(field(child, "alias") or field(child, "name"))
                        bind(rel, node, local, (source, text(field(child, "name")), type_only or text(child).startswith("type ")))
                    elif child.type == "namespace_import":
                        bind(rel, node, text(child.named_children[-1]), (source, "*", type_only))
                    elif child.type == "import_clause":
                        for item in child.named_children:
                            if item.type == "identifier":
                                bind(rel, node, text(item), (source, "default", type_only))
            elif node.type == "variable_declarator":
                name, value = field(node, "name"), field(node, "value")
                for local in pattern_names(name):
                    bind(rel, node, local, None)
                if name is not None and name.type == "identifier":
                    bind(rel, node, text(name), None)
                    if value is not None and value.type == "call_expression" and text(field(value, "function")) == "require":
                        source = literal(args(value)[0]) if args(value) else None
                        if source:
                            imports.append(source)
                            bind(rel, node, text(name), (source, "*", False))
                elif name is not None and name.type == "object_pattern" and value is not None and value.type == "call_expression" and text(field(value, "function")) == "require":
                    source = literal(args(value)[0]) if args(value) else None
                    if source:
                        imports.append(source)
                        for part in name.named_children:
                            remote = text(field(part, "key")) if part.type == "pair_pattern" else text(part)
                            local = text(field(part, "value")) if part.type == "pair_pattern" else remote
                            bind(rel, node, local, (source, remote, False))
            elif node.type in {"class_declaration", "interface_declaration"}:
                name = text(field(node, "name"))
                decs = decorators(node)
                kind = next(({"Controller": "controller", "Injectable": "service", "Module": "module"}[d]
                             for d, _ in decs if d in {"Controller", "Injectable", "Module"}), "class")
                if node.type == "interface_declaration":
                    kind = "interface"
                if record["meta"]["scope"] == "frontend":
                    kind = "frontend_class"
                if record["meta"]["role"] == "TEST":
                    kind = "test_class"
                cid = f"type:{rel}:{name}"
                id_counts[cid] = id_counts.get(cid, 0) + 1
                if id_counts[cid] > 1:
                    cid += f":duplicate:{id_counts[cid]}"
                graph.add_node(Node(cid, kind, name, rel, {"annotations": [d for d, _ in decs],
                                   "scope": record["meta"]["scope"], "is_test_code": record["meta"]["role"] == "TEST",
                                   "extraction_method": "tree-sitter"}, Evidence(evidence=evidence(rel, node))))
                bind(rel, node, name, cid if id_counts[f"type:{rel}:{name}"] == 1 else None)
                classes[(rel, key(node))] = cid
        next(n for n in graph.nodes if n.id == record["mid"]).metadata["imports"] = imports

        for node in record["ast"]:
            if node.type not in FUNCTIONS:
                continue
            name = text(field(node, "name"))
            if node.parent.type == "variable_declarator":
                name = text(field(node.parent, "name"))
            if not name:
                parent_call = next((n for n in ancestors(node) if n.type == "call_expression"), None)
                name = "callback:" + (text(field(parent_call, "function")) if parent_call else "anonymous")
                if parent_call and args(parent_call):
                    name += ":" + (literal(args(parent_call)[0]) or "dynamic")
            cls = next((n for n in ancestors(node) if n.type == "class_declaration"), None)
            owner = classes.get((rel, key(cls))) if cls is not None else record["mid"]
            enclosing = [text(field(n, "name")) for n in ancestors(node) if n.type in FUNCTIONS]
            identity_scope = "/".join(reversed(enclosing))
            fid = f"{'method' if cls is not None else 'function'}:{rel}:{owner}#{identity_scope}:{name}"
            id_counts[fid] = id_counts.get(fid, 0) + 1
            if id_counts[fid] > 1:
                fid += f":duplicate:{id_counts[fid]}"
            params = field(node, "parameters") or field(node, "parameter")
            graph.add_node(Node(fid, "method" if cls is not None else "function", name, rel,
                                {"owner": owner, "params": text(params), "identity_scope": identity_scope,
                                 "start_byte": node.start_byte, "end_byte": node.end_byte,
                                 "normalized_params": tokens(params), "structure_fingerprint": digest(tokens(node)),
                                 "scope": record["meta"]["scope"], "is_test_code": record["meta"]["role"] == "TEST",
                                 "annotations": [d for d, _ in decorators(node)], "extraction_method": "tree-sitter"},
                                Evidence(evidence=evidence(rel, node))))
            callable_nodes[(rel, key(node))] = fid
            graph.add_edge(Edge(owner, fid, "declares", evidence(rel, node)))
            declaration = node.parent if node.parent.type == "variable_declarator" else node
            if not name.startswith("callback:"):
                duplicate = ":duplicate:" in fid
                bind(rel, declaration, name, None if duplicate else fid, key(node) if node.type == "function_expression" and node.parent.type != "variable_declarator" else None)
            if params is not None:
                for parameter in (params.named_children if params.type == "formal_parameters" else [params]):
                    pattern = field(parameter, "pattern") or field(parameter, "name") or parameter
                    for local in pattern_names(pattern):
                        bind(rel, node, local, None, key(node))
                    typ = field(parameter, "type")
                    if name == "constructor" and cls is not None and typ is not None:
                        instance_types[(owner, text(pattern))] = text(typ).lstrip(": ")
            for dec, _ in decorators(node):
                control_type = {"UseGuards": "authentication", "Auth": "authentication", "Authorize": "authorization",
                                "PreAuthorize": "authorization", "Secured": "authorization", "RolesAllowed": "authorization",
                                "Valid": "validation", "Validated": "validation", "Throttle": "rate_limit"}.get(dec)
                if control_type:
                    control_id = f"control:decorator:{fid}:{dec}"
                    graph.add_node(Node(control_id, "control", dec, rel,
                                        {"control_type": control_type, "scope_basis": "method-decorator",
                                         "enforcement_layer": "CLIENT" if record["meta"]["scope"] == "frontend" else "SERVER",
                                         "target": fid}, Evidence(state="INFERRED", confidence="medium", evidence=evidence(rel, node))))
                    graph.add_edge(Edge(control_id, fid, "protects", evidence(rel, node), {"basis": "method-decorator-candidate"}))
            if cls is not None and record["meta"]["scope"] != "frontend" and record["meta"]["role"] != "TEST":
                base = next((literal(a[0]) for d, a in decorators(cls) if d == "Controller" and a), "") or ""
                for dec, arguments in decorators(node):
                    if dec.lower() in HTTP:
                        route_path = "/" + "/".join(x.strip("/") for x in (base, literal(arguments[0]) if arguments else "") if x)
                        rid = f"route:{HTTP[dec.lower()]}:{route_path}:{rel}:{name}"
                        graph.add_node(Node(rid, "route", f"{HTTP[dec.lower()]} {route_path}", rel,
                                            {"handler": fid, "http_method": HTTP[dec.lower()], "path": route_path, "framework": "NestJS"},
                                            Evidence(evidence=evidence(rel, node))))
                        graph.add_edge(Edge(rid, fid, "handled_by", evidence(rel, node)))
        # Export identities are resolved after all local callable bindings exist.
        for node in record["ast"]:
            if node.type != "export_statement":
                continue
            source = literal(field(node, "source"))
            declaration = field(node, "declaration")
            if source and any(child.type == "*" for child in node.children) and not any(child.type in {"namespace_export", "ERROR"} for child in node.named_children):
                star_exports.setdefault(rel, []).append(source)
            if declaration is not None:
                for child in [declaration] + list(declaration.named_children):
                    name_node = field(child, "name")
                    if name_node is not None:
                        name = text(name_node)
                        exported = "default" if text(node).startswith("export default") else name
                        exports[(rel, exported)] = bindings.get((rel, key(record["tree"]), name))
            for child in walk(node):
                if child.type == "export_specifier":
                    name = text(field(child, "name"))
                    alias = text(field(child, "alias")) or name
                    type_only = bool(re.match(r"export\s+type\b", text(node))) or text(child).startswith("type ")
                    exports[(rel, alias)] = (source, name, type_only) if source else None if type_only else bindings.get((rel, key(record["tree"]), name))
        for node in record["ast"]:
            if node.type == "assignment_expression":
                left, right = field(node, "left"), field(node, "right")
                match = re.fullmatch(r"(?:module\.)?exports\.([A-Za-z_]\w*)", text(left))
                if match:
                    exports[(rel, match[1])] = callable_nodes.get((rel, key(right))) if right is not None and right.type in FUNCTIONS else lookup(rel, node, text(right))

    node_map = {n.id: n for n in graph.nodes}
    for rel, record in records.items():
        for node in record["ast"]:
            if node.type != "class_declaration":
                continue
            owner = classes[(rel, key(node))]
            for heritage in (n for n in node.named_children if n.type == "class_heritage"):
                for clause in heritage.named_children:
                    relation = "implements" if clause.type == "implements_clause" else "extends"
                    for base in clause.named_children:
                        value = lookup(rel, node, text(base))
                        # Type imports support declared heritage, never executable calls.
                        value = (value[0], value[1], False) if isinstance(value, tuple) else value
                        target = resolve(value, rel)
                        if isinstance(target, str) and target in node_map and node_map[target].kind in {"interface", "class", "service", "controller", "frontend_class"}:
                            graph.add_edge(Edge(owner, target, relation, evidence(rel, clause), {"basis": "declared-type-heritage"}))
                        else:
                            unknown(rel, clause, "heritage_target_unresolved")
    for (rel, binding_scope, name), value in bindings.items():
        if isinstance(value, tuple):
            target_module = module(value[0], rel)
            if target_module:
                graph.add_edge(Edge(records[rel]["mid"], records[target_module]["mid"],
                                    "imports_type" if value[2] else "imports", [rel],
                                    {"basis": "literal-module-resolution"}))
    for rel, record in records.items():
        for node in record["ast"]:
            if node.type not in {"import_statement", "export_statement"}:
                continue
            source = literal(field(node, "source"))
            target = module(source, rel) if source else None
            if target:
                typed = bool(re.match(r"(?:import|export)\s+type\b", text(node)))
                specifiers = [part for part in walk(node) if part.type in {"import_specifier", "export_specifier"}]
                default_import = any(part.type == "import_clause" and any(c.type == "identifier" for c in part.named_children) for part in node.named_children)
                if specifiers and all(text(part).startswith("type ") for part in specifiers) and not default_import and not any(part.type in {"namespace_import", "namespace_export"} for part in walk(node)):
                    typed = True
                graph.add_edge(Edge(record["mid"], records[target]["mid"], "imports_type" if typed else "imports",
                                    evidence(rel, node), {"basis": "literal-module-resolution"}))
    for rel, record in records.items():
        for node in record["ast"]:
            if node.type == "new_expression":
                constructor = field(node, "constructor")
                parent = node.parent
                if parent.type == "variable_declarator":
                    variable = text(field(parent, "name"))
                    value = lookup(rel, node, text(constructor))
                    if constructor is not None and constructor.type == "member_expression":
                        base = lookup(rel, node, text(field(constructor, "object")))
                        if isinstance(base, tuple) and base[1] in {"*", "default"}:
                            value = (base[0], text(field(constructor, "property")), base[2])
                    bind(rel, parent, variable, value)
                    if (isinstance(value, tuple) and value[0] in {"events", "node:events"}
                            and value[1] in {"EventEmitter", "default", "*"} and not value[2]
                            and lookup(rel, node, "require") is None):
                        token = binding_key(rel, node, variable)
                        pubsub_instances[token] = token
                        pubsub_constructors[token] = binding_key(
                            rel, node, text(field(constructor, "object")) if constructor.type == "member_expression" else text(constructor))
            elif node.type == "variable_declarator" and field(node, "value") is not None and field(node, "value").type == "identifier":
                original = binding_key(rel, node, text(field(node, "value")))
                bind(rel, node, text(field(node, "name")), lookup(rel, node, text(field(node, "value"))))
                if original in pubsub_instances:
                    pubsub_instances[binding_key(rel, node, text(field(node, "name")))] = pubsub_instances[original]
    # Invalidate all changing bindings before resolving callers in any module.
    for rel, record in records.items():
        for node in record["ast"]:
            if node.type in {"assignment_expression", "augmented_assignment_expression", "update_expression"}:
                left = field(node, "left") or field(node, "argument")
                if left is not None and left.type in {"member_expression", "subscript_expression"}:
                    token = binding_key(rel, node, text(field(left, "object")))
                    mutated_members.add(pubsub_instances.get(token, token))
                if left is not None and left.type == "identifier":
                    name = text(left)
                    for lexical in ancestors(node):
                        token = (rel, key(lexical), name)
                        if lexical.type in SCOPES and token in bindings:
                            previous = bindings[token]
                            if lexical.type == "program" and previous is not None:
                                for exported, exported_value in list(exports.items()):
                                    if exported[0] == rel and exported_value == previous:
                                        exports[exported] = None
                            bindings[token] = None
                            unknown(rel, node, "binding_reassigned")
                            break
    for rel, record in records.items():
        requests = list(api_calls(record["source"], Path(rel).suffix))
        request_keys = {key(node) for node, _, _ in requests}
        for node in record["ast"]:
            if node.type != "call_expression":
                continue
            if key(node) in request_keys:
                continue  # One shared request extraction, no duplicate generic SDK call.
            fn = field(node, "function")
            fn_text = re.sub(r"\s+", "", text(fn))
            enclosing = next((n for n in ancestors(node) if n.type in FUNCTIONS), None)
            caller = callable_nodes.get((rel, key(enclosing)), record["mid"]) if enclosing else record["mid"]
            ev = evidence(rel, node)
            arguments = args(node)
            if record["meta"]["role"] == "TEST" and fn_text in {"test", "it"} and arguments:
                test_name = literal(arguments[0])
                if test_name:
                    tid = f"test:{rel}:{test_name}"
                    test_fn = next((a for a in arguments[1:] if a.type in FUNCTIONS), None)
                    graph.add_node(Node(tid, "test", test_name, rel,
                                        {"framework": "Jest/Vitest/Mocha-like", "is_test_code": True,
                                         "test_callable": callable_nodes.get((rel, key(test_fn))) if test_fn else None}, Evidence(evidence=ev)))
            method = text(field(fn, "property")) if fn is not None and fn.type == "member_expression" else ""
            receiver = text(field(fn, "object")) if method else ""
            if (method in HTTP and receiver in {"app", "router", "server"} and record["meta"]["scope"] != "frontend"
                    and record["meta"]["role"] != "TEST" and len(arguments) >= 2 and literal(arguments[0]) is not None):
                route_path = literal(arguments[0])
                rid = f"route:{HTTP[method]}:{route_path}:{rel}"
                handlers = []
                for argument in arguments[1:]:
                    target = callable_nodes.get((rel, key(argument))) if argument.type in FUNCTIONS else resolve(lookup(rel, node, text(argument)), rel)
                    if isinstance(target, str) and target in node_map:
                        handlers.append(target)
                    else:
                        unknown(rel, argument, "route_handler_or_middleware_unresolved")
                handler = handlers[-1] if handlers else None
                graph.add_node(Node(rid, "route", f"{HTTP[method]} {route_path}", rel,
                                    {"handler": handler, "http_method": HTTP[method], "path": route_path, "framework": "Express/Fastify-like"}, Evidence(evidence=ev)))
                if handler:
                    graph.add_edge(Edge(rid, handler, "handled_by", ev))
                continue
            target, value = None, None
            if fn is not None and fn.type == "identifier":
                value = lookup(rel, node, fn_text)
                if isinstance(value, tuple) and value[2]:
                    unknown(rel, node, "type_only_import_called")
                    continue
                target = resolve(value, rel)
            elif receiver == "this" and caller in node_map:
                owner = node_map[caller].metadata.get("owner")
                candidates = [n.id for n in graph.nodes if n.metadata.get("owner") == owner and n.name == method]
                target = candidates[0] if len(candidates) == 1 else None
            elif receiver.startswith("this.") and caller in node_map:
                owner = node_map[caller].metadata.get("owner")
                typ = instance_types.get((owner, receiver[5:]))
                cls = resolve(lookup(rel, node, typ), rel) if typ else None
                if isinstance(cls, str) and cls in node_map:
                    graph.add_edge(Edge(caller, cls, "calls_dependency", ev, {"basis": "static-di-receiver"}))
                    graph.add_edge(Edge(caller, f"method-name:{node_map[cls].name}#{method}", "calls_method_name", ev))
                    matches = [n.id for n in graph.nodes if n.metadata.get("owner") == cls and n.name == method]
                    target = matches[0] if len(matches) == 1 else None
            elif receiver:
                value = lookup(rel, node, receiver.split(".")[0])
                if isinstance(value, tuple) and value[1] == "*" and not value[2]:
                    target = resolve((value[0], method, False), rel)
                elif isinstance(value, str):
                    matches = [n.id for n in graph.nodes if n.metadata.get("owner") == value and n.name == method]
                    target = matches[0] if len(matches) == 1 else None
            if isinstance(value, tuple) and not value[0].startswith(".") and not value[2] and value[0] not in {"axios", "jquery"}:
                package = "/".join(value[0].split("/")[:2]) if value[0].startswith("@") else value[0].split("/")[0]
                operation = method if receiver else value[1]
                node_http = value[0] in {"http", "https", "node:http", "node:https"} and operation in {"get", "request"}
                client = package in SERVICE_CLIENT_PACKAGES or package.startswith("@aws-sdk/") or node_http
                xid = f"{'external' if client else 'library'}-call:{rel}:{caller}:{fn_text}"
                meta = {"imports": [value[0]], "owner": caller, "receiver": receiver,
                        "client_call_observed": client, "network_effect": "unverified"}
                token = binding_key(rel, node, receiver)
                origin = pubsub_instances.get(token)
                constructor_token = pubsub_constructors.get(origin)
                if (method == "emit" and token in pubsub_instances
                        and origin not in mutated_members and constructor_token not in mutated_members
                        and isinstance(bindings.get(constructor_token), tuple)):
                    meta["pubsub_receiver"] = "node-events"
                graph.add_node(Node(xid, "external_api_call" if client else "library_call", fn_text, rel, meta, Evidence(evidence=ev)))
                graph.add_edge(Edge(caller, xid, "calls", ev, {"basis": "imported-client-call" if client else "imported-module-call"}))
                continue
            if isinstance(target, str) and target in node_map:
                graph.add_edge(Edge(caller, target, "calls", ev, {"basis": "lexical-module-binding"}))
            elif fn_text not in {"require", "test", "it", "expect"} and not fn_text.startswith(("console.", "JSON.", "Object.", "Array.", "Math.")):
                unknown(rel, node, "call_target_unresolved")
            prisma = re.fullmatch(r"prisma\.([A-Za-z_]\w*)\.([A-Za-z_]\w*)", fn_text)
            if prisma:
                store = f"datastore:prisma:{prisma[1]}"
                graph.add_node(Node(store, "entity", prisma[1], rel, {"orm": "Prisma", "observed_operation": prisma[2]}, Evidence(evidence=ev)))
                graph.add_edge(Edge(caller, store, "calls", ev, {"basis": "literal-prisma-member"}))
            elif fn_text == "mongoose.model" and arguments and literal(arguments[0]) is not None:
                name = literal(arguments[0])
                store = f"datastore:mongoose:{name}"
                graph.add_node(Node(store, "entity", name, rel, {"orm": "Mongoose"}, Evidence(evidence=ev)))
                graph.add_edge(Edge(caller, store, "calls", ev, {"basis": "literal-mongoose-model"}))
        request_occurrences = {}
        for node, method, target in requests:
            enclosing = next((n for n in ancestors(node) if n.type in FUNCTIONS), None)
            caller = callable_nodes.get((rel, key(enclosing)), record["mid"]) if enclosing else record["mid"]
            # Shadowed request APIs are not ambient network observations.
            fn = text(field(node, "function"))
            if fn == "fetch" and lookup(rel, node, "fetch") is not None:
                continue
            frontend = record["meta"]["scope"] == "frontend"
            site = request_site(node, method, target, request_occurrences)
            cid = f"{'frontend' if frontend else 'external'}-call:{rel}:{site}"
            graph.add_node(Node(cid, "frontend_api_call" if frontend else "external_api_call", f"{method} {target}", rel,
                                {"scope": record["meta"]["scope"], "http_method": method, "path": target,
                                 "external": target.startswith(("http://", "https://")), "owner": caller,
                                 "identity_scope": site, "client_call_observed": True,
                                 "extraction_method": "tree-sitter"}, Evidence(evidence=evidence(rel, node))))
            graph.add_edge(Edge(caller, cid, "calls_api" if frontend else "calls", evidence(rel, node), {"basis": "literal-request-syntax"}))
        # Separate coverage for each relation method; declaration coverage cannot certify calls.
        failures = {row["reason"] for row in graph.unknowns if row["path"] == rel}
        syntax_reasons = ["parser_recovery"] if record["tree"].has_error else []
        imports = [literal(field(node, "source")) for node in record["ast"] if node.type in {"import_statement", "export_statement"} and field(node, "source") is not None]
        imports += [literal(args(node)[0]) if args(node) else None for node in record["ast"]
                    if node.type == "call_expression" and text(field(node, "function")) == "require"]
        import_reasons = syntax_reasons + (["module_outside_inventory_or_ambiguous"] if any(not source or not module(source, rel) for source in imports) else [])
        heritage_reasons = syntax_reasons + sorted(failures & {"heritage_target_unresolved"})
        if any(node.type == "extends_type_clause" for node in record["ast"]):
            heritage_reasons.append("interface_heritage_not_admitted")
        def coverage(method, admitted, reasons):
            return {"status": "PARTIAL" if reasons else "ANALYZED", "method": method,
                    "scope": {"path": rel, "admitted": admitted}, "reasons": reasons,
                    "omitted_count": None if reasons else 0}
        graph.coverage[rel]["families"] = {
            "declarations": coverage("tree-sitter", "named classes/interfaces/functions and admitted callbacks", syntax_reasons),
            "imports": coverage("literal-module-resolution", "static imports/re-exports between uniquely inventoried modules", import_reasons),
            "calls": coverage("lexical-module-binding", "direct lexical calls, admitted receivers and literal HTTP requests; runtime dispatch unverified",
                              syntax_reasons + sorted(failures - {"heritage_target_unresolved"}) + ["runtime_and_dynamic_dispatch_unverified"]),
            "type_heritage": coverage("declared-type-heritage", "class extends/implements with unique declared target", heritage_reasons),
        }
    for node in graph.nodes:
        node.metadata.setdefault("extraction_method", "tree-sitter")
    return graph
