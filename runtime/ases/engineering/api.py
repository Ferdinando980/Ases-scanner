"""Source interface recovery; declarations and comments, never runtime guarantees."""
from __future__ import annotations

import ast
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import re


def contracts(comment):
    result = []
    for line in comment.splitlines():
        match = re.search(r"(?:@|\b)(pre(?:condition)?|post(?:condition)?|invariant|requires|ensures)\s*:?\s+(.+)", line, re.I)
        if match:
            kind = match[1].lower()
            kind = "precondition" if kind in {"pre", "precondition", "requires"} else "postcondition" if kind in {"post", "postcondition", "ensures"} else "invariant"
            result.append({"kind": kind, "statement": match[2].strip(" */"), "status": "declared; not proved"})
    return result


def preceding_comment(text, offset):
    before = text[:offset].rstrip()
    if before.endswith("*/"):
        start = before.rfind("/**")
        if start >= 0:
            return before[start:]
    lines = before.splitlines()
    comment = []
    for line in reversed(lines):
        if line.strip().startswith(("//", "#")):
            comment.insert(0, line)
        else:
            break
    return "\n".join(comment)


def body_nodes(function):
    """Walk one callable body without attributing nested callables to its owner."""
    pending = list(function.body)
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        yield node
        pending.extend(ast.iter_child_nodes(node))


def recover_api(root, graph, inventory, progress=None):
    by_file = defaultdict(list)
    for node in graph.get("nodes", []):
        if node.get("path"):
            by_file[node["path"]].append(node)
    rows, coverage = [], []
    for source in inventory.get("source_manifest", []):
        rel = source["path"]
        if Path(rel).suffix not in {".py", ".java", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts"}:
            continue
        if progress:
            progress("document-api")
        path = root / rel
        try:
            size = path.stat().st_size
            data = path.read_bytes() if size <= 5 * 1024 * 1024 else b""
        except OSError:
            coverage.append({"path": rel, "status": "failed", "declarations": 0, "limits": "Source unavailable since inventory"})
            continue
        if size > 5 * 1024 * 1024:
            coverage.append({"path": rel, "status": "partial", "declarations": 0, "limits": "5 MiB API source limit; source not read"})
            continue
        if sha256(data).hexdigest() != source["sha256"]:
            coverage.append({"path": rel, "status": "failed", "declarations": 0, "limits": "Source changed since inventory"})
            continue
        text = data.decode("utf-8", errors="replace")
        nodes = by_file[rel]
        found = []
        def emit(name, kind, line, signature, map_to_graph=True, **extra):
            candidates = [n for n in nodes if n["name"] == name and (kind not in {"function", "method"} or n["kind"] in {"function", "method"})]
            if extra.get("is_nested"):
                scope = extra.get("identity_scope")
                candidates = [n for n in candidates if n.get("metadata", {}).get("is_nested")
                              and n.get("metadata", {}).get("identity_scope") == scope]
            if extra.get("syntax_start_byte") is not None:
                located = [n for n in nodes if n.get("metadata", {}).get("start_byte") == extra["syntax_start_byte"]
                           and n["kind"] in {"function", "method"}]
                if len(located) == 1:
                    candidates = located
            exact = [n for n in candidates if f"{rel}:{line}" in n.get("provenance", {}).get("evidence", [])]
            matches = (exact or candidates) if map_to_graph else []
            node = matches[0] if len(matches) == 1 else None
            identity = node["id"] if node and len(exact or candidates) == 1 else "api:" + sha256(f"{rel}:{extra.get('qualified_name', name)}:{signature}".encode()).hexdigest()[:24]
            if node and node.get('metadata', {}).get('conditional_declaration'):
                extra['conditional_declaration'] = True
                extra['declaration_context'] = node['metadata']['declaration_context']
            comment = extra.pop("comment", "")
            found.append({"id": identity, "entity_ref": node["id"] if node else None, "name": name, "kind": kind,
                          "path": rel, "language": source["language"], "authority": "source-syntax",
                          "locations": [{"path": rel, "sha256": source["sha256"], "line": line}],
                          "signature": signature, "responsibility": comment.strip() or None,
                          "contracts": contracts(comment), "visibility": extra.pop("visibility", "undeclared"),
                          "errors_declared": re.findall(r"@(?:throws|raise[sd]?)\s+([^\n*]+)", comment),
                          "limits": ["Static interface; effects, runtime contracts and transitive exceptions not verified"], **extra})
        try:
            if rel.endswith(".py"):
                tree = ast.parse(text)
                def visit(body, owner=""):
                    for node in body:
                        if isinstance(node, ast.ClassDef):
                            qualified = owner + node.name
                            emit(node.name, "class", node.lineno, "class " + node.name + ("(" + ", ".join(ast.unparse(b) for b in node.bases) + ")" if node.bases else ""),
                                 qualified_name=qualified, package=str(Path(rel).parent), owner=owner.rstrip("."),
                                 bases=[ast.unparse(b) for b in node.bases], comment=ast.get_docstring(node) or "",
                                 attributes=[{"name": n.target.id, "type": ast.unparse(n.annotation), "visibility": "private-convention" if n.target.id.startswith("_") else "public-convention"} for n in node.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)])
                            visit(node.body, qualified + ".")
                        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                            signature = prefix + "def " + node.name + "(" + ast.unparse(node.args) + ")" + (" -> " + ast.unparse(node.returns) if node.returns else "")
                            emit(node.name, "method" if owner else "function", node.lineno, signature,
                                 qualified_name=owner + node.name, owner=owner.rstrip("."), package=str(Path(rel).parent),
                                 params=ast.unparse(node.args), return_type=ast.unparse(node.returns) if node.returns else None,
                                 body_present=True,
                                 visibility="private-convention" if node.name.startswith("_") else "public-convention",
                                 async_operation=isinstance(node, ast.AsyncFunctionDef), comment=ast.get_docstring(node) or "",
                                 errors_observed=sorted({ast.unparse(n.exc) for n in body_nodes(node) if isinstance(n, ast.Raise) and n.exc}),
                                 guards_observed=[ast.unparse(n.test) for n in node.body if isinstance(n, ast.If)][:20])
                            visit_local_functions(node, owner + node.name)

                def visit_local_functions(parent, identity_scope):
                    """Expose only nested callables with a unique scanner entity."""
                    def walk(statements, lexical_scope):
                        for statement in statements:
                            if isinstance(statement, ast.ClassDef):
                                # Nested classes and their methods have a separate identity policy.
                                continue
                            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                qualified = lexical_scope + "." + statement.name
                                exact = [n for n in nodes
                                         if n.get("name") == statement.name
                                         and n.get("kind") in {"function", "method"}
                                         and n.get("metadata", {}).get("is_nested")
                                         and n.get("metadata", {}).get("identity_scope") == lexical_scope
                                         and f"{rel}:{statement.lineno}" in n.get("provenance", {}).get("evidence", [])]
                                if len(exact) == 1:
                                    prefix = "async " if isinstance(statement, ast.AsyncFunctionDef) else ""
                                    signature = prefix + "def " + statement.name + "(" + ast.unparse(statement.args) + ")" + (" -> " + ast.unparse(statement.returns) if statement.returns else "")
                                    emit(statement.name, "function", statement.lineno, signature,
                                         qualified_name=qualified, owner=lexical_scope,
                                         package=str(Path(rel).parent), params=ast.unparse(statement.args),
                                         return_type=ast.unparse(statement.returns) if statement.returns else None,
                                         visibility="local-callable", is_nested=True,
                                         body_present=True,
                                         identity_scope=lexical_scope,
                                         async_operation=isinstance(statement, ast.AsyncFunctionDef),
                                         comment=ast.get_docstring(statement) or "",
                                         errors_observed=sorted({ast.unparse(n.exc) for n in body_nodes(statement) if isinstance(n, ast.Raise) and n.exc}),
                                         guards_observed=[ast.unparse(n.test) for n in statement.body if isinstance(n, ast.If)][:20])
                                    walk(statement.body, qualified)
                                # Unindexed or ambiguous declarations remain unknown; do not
                                # manufacture an API row or attribute descendants to another scope.
                                continue
                            walk(ast.iter_child_nodes(statement), lexical_scope)
                    walk(parent.body, identity_scope)
                visit(tree.body)
                from ..scanners.python import scoped_function_declarations
                for declaration, context in scoped_function_declarations(tree.body):
                    if context:
                        visit([declaration])
            elif rel.endswith(".java"):
                from ..scanners.java import TYPE_RE, METHOD_RE, FIELD_RE, balanced_block, NON_CODE_RE
                masked = NON_CODE_RE.sub(lambda m: "".join("\n" if c == "\n" else " " for c in m[0]), text)
                for match in TYPE_RE.finditer(masked):
                    block = balanced_block(masked, match.end())
                    if not block:
                        continue
                    start, end = block
                    package_match = re.search(r"\bpackage\s+([\w.]+)", masked)
                    package = package_match[1] if package_match else ""
                    name = match["name"]
                    body = masked[start:end]
                    emit(name, match["kind"], text.count("\n", 0, match.start()) + 1, text[match.start():start].strip(),
                         qualified_name=package + "." + name, package=package, comment=preceding_comment(text, match.start()),
                         bases=[v for v in (match["extends"], match["implements"]) if v],
                         attributes=[{"name": f["name"], "type": f["type"].strip()} for f in FIELD_RE.finditer(body)])
                    for method in METHOD_RE.finditer(body):
                        offset = start + method.start()
                        # Ignore nested declarations/anonymous classes: do not assign them to this owner.
                        if body[:method.start()].count("{") - body[:method.start()].count("}") != 1:
                            continue
                        tail = masked[start + method.end():end]
                        throws = re.match(r"\s*throws\s+([^\{;]+)", tail)
                        signature = text[offset:start + method.end()].strip() + (" throws " + throws[1].strip() if throws else "")
                        emit(method["name"], "method", text.count("\n", 0, offset) + 1, signature,
                             qualified_name=package + "." + name + "." + method["name"], owner=name, package=package,
                             visibility=method["vis"], params=method["params"], return_type=method["ret"].strip(),
                             declared_throws=[v.strip() for v in throws[1].split(",")] if throws else [],
                             comment=preceding_comment(text, offset))
                # Use Java grammar ancestry to recover the exact nested owner and
                # declarations whose visibility is implicit in interfaces.
                from ..scanners.java_syntax import parse as parse_java, walk as walk_java, field as java_field, text as java_text
                syntax = parse_java(text)
                existing_lines = {(r["name"], r["locations"][0]["line"]) for r in found if r["kind"] == "method"}
                for declaration in (n for n in walk_java(syntax) if n.type == "method_declaration"):
                    name_node = java_field(declaration, "name")
                    method_name = java_text(name_node)
                    if not method_name:
                        continue
                    line = declaration.start_point.row + 1
                    chain = []
                    current = declaration.parent
                    enum_constant = None
                    while current:
                        if current.type == "enum_constant" and enum_constant is None:
                            enum_constant = current
                        if current.type in {"class_declaration", "interface_declaration", "enum_declaration", "record_declaration"}:
                            chain.append(java_text(java_field(current, "name")))
                        current = current.parent
                    chain.reverse()
                    if enum_constant:
                        chain.append(java_text(java_field(enum_constant, "name")))
                    owner = ".".join(chain)
                    if not owner:
                        continue
                    modifiers = java_text(next((c for c in declaration.named_children if c.type == "modifiers"), None))
                    ancestor = declaration.parent
                    while ancestor and ancestor.type not in {"interface_declaration", "class_declaration", "enum_declaration", "record_declaration"}:
                        ancestor = ancestor.parent
                    interface_owner = bool(ancestor and ancestor.type == "interface_declaration")
                    body_node = java_field(declaration, "body")
                    modifier_node = next((c for c in declaration.named_children if c.type == "modifiers"), None)
                    explicit_visibility = any(n.type in {"public", "protected", "private"}
                                              for n in walk_java(modifier_node)) if modifier_node else False
                    package_private_class = (bool(ancestor and ancestor.type == "class_declaration")
                                             and body_node is not None and not explicit_visibility)
                    if (method_name, line) in existing_lines and not enum_constant:
                        row = next(r for r in found if r["kind"] == "method" and r["name"] == method_name and r["locations"][0]["line"] == line)
                        row["qualified_name"] = (package + "." if package else "") + owner + "." + method_name
                        row["owner"] = owner
                        row["body_present"] = body_node is not None
                        continue
                    if not (enum_constant or (interface_owner and "private" not in modifiers) or package_private_class):
                        continue
                    byte_offset = declaration.start_byte
                    signature_end = body_node.start_byte if body_node else declaration.end_byte
                    signature = data[byte_offset:signature_end].decode("utf-8", errors="replace").strip().rstrip(";")
                    visibility = ("package-private" if package_private_class else "public" if interface_owner else next(
                        (v for v in ("private", "protected", "public") if v in modifiers), "undeclared"))
                    emit(method_name, "method", line, signature,
                         qualified_name=(package + "." if package else "") + owner + "." + method_name,
                         owner=owner, package=package, params=java_text(java_field(declaration, "parameters")),
                         return_type=java_text(java_field(declaration, "type")),
                         visibility=visibility, syntax_start_byte=declaration.start_byte,
                         body_present=body_node is not None,
                         comment=preceding_comment(text, len(data[:byte_offset].decode("utf-8", errors="replace"))))
                    existing_lines.add((method_name, line))
            else:
                from ..scanners.javascript import parse, walk, field, text as node_text, FUNCTIONS
                tree = parse(text, Path(rel).suffix)
                for node in walk(tree):
                    if node.type not in FUNCTIONS | {"class_declaration", "interface_declaration", "method_signature", "function_signature", "abstract_method_signature"}:
                        continue
                    name_node = field(node, "name")
                    if name_node is None and node.parent and node.parent.type == "variable_declarator":
                        name_node = field(node.parent, "name")
                    if name_node is None and node.parent and node.parent.type == "assignment_expression":
                        left = field(node.parent, "left")
                        if left and left.type == "identifier":
                            name_node = left
                        elif left and left.type == "member_expression":
                            prop = field(left, "property")
                            if prop and prop.type == "property_identifier":
                                name_node = left if node_text(left) == "module.exports" else prop
                    name = node_text(name_node)
                    if not name and node.parent and node.parent.type == "export_statement" and node_text(node.parent).startswith("export default"):
                        name = "default"
                    if not name:
                        continue
                    owner = node.parent
                    while owner and owner.type not in {"class_declaration", "interface_declaration", "program"}:
                        owner = owner.parent
                    owner_name = node_text(field(owner, "name")) if owner else ""
                    body = field(node, "body")
                    signature = text.encode()[node.start_byte:body.start_byte if body else node.end_byte].decode().rstrip(" {;\n")
                    kind = "class" if node.type == "class_declaration" else "interface" if node.type == "interface_declaration" else "method" if owner_name else "function"
                    emit(name, kind, node.start_point.row + 1, signature,
                         map_to_graph=node.type not in {"method_signature", "function_signature", "abstract_method_signature"},
                         syntax_start_byte=node.start_byte if node.type in FUNCTIONS else None,
                         qualified_name=(owner_name + "." if owner_name else "") + name, owner=owner_name,
                         package=str(Path(rel).parent), params=node_text(field(node, "parameters") or field(node, "parameter")),
                         return_type=node_text(field(node, "return_type")) or None,
                         async_operation=bool(re.match(r"async\b", signature)),
                         visibility=next((v for v in ("private", "protected", "public") if re.search(r"\b" + v + r"\b", signature)), "undeclared"),
                         comment=preceding_comment(text, len(text.encode()[:node.start_byte].decode())))
            rows.extend(found)
            coverage.append({"path": rel, "status": "partial", "declarations": len(found),
                             "limits": "Python AST / JS-TS syntax; Java bounded grammar ancestry for nested, interface, and enum-constant methods; constructors and generated APIs remain limited" if rel.endswith(".java") else "Declared syntax only; dynamic/generated APIs unresolved"})
        except (SyntaxError, ValueError, RecursionError):
            coverage.append({"path": rel, "status": "failed", "declarations": 0, "limits": "Syntax unsupported or malformed"})
    # A legacy graph can collapse overloads declared on the same line. Keep
    # distinct engineering records and expose the unresolved graph mapping.
    by_identity = defaultdict(list)
    for row in rows:
        by_identity[row["id"]].append(row)
    for identity, duplicates in by_identity.items():
        if len(duplicates) < 2:
            continue
        for index, row in enumerate(duplicates):
            row["id"] = "api:" + sha256(f"{row['path']}:{row.get('qualified_name', row['name'])}:{row['signature']}:{index}".encode()).hexdigest()[:24]
            row["entity_ref_candidates"] = [identity]
            row["entity_ref"] = None
            row["limits"].append("Graph identity shared by multiple declarations; mapping unresolved")
    return rows, coverage
