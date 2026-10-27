"""Bounded behavioral interpretation: evidence-backed sentences, not recovered intent.

Facts describe supported syntax and branch-local expressions. The interpreter never
executes target code and never treats a method name as proof of a business effect.
"""
from __future__ import annotations

import ast
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re

BEHAVIOR_PROFILE = 'branch-local-flow/12'
EFFECT_NAMES = frozenset({'save', 'create', 'insert', 'update', 'delete', 'remove', 'write_text', 'write_bytes', 'commit'})
BODY_FACT_BUDGET = 50000

def identity(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]


def explain_expression(expression, language="it", source_language="python"):
    """Verbalize supported expression semantics without guessing the business goal."""
    it = language == "it"
    if it:
        from .prose import expression as describe
        return describe(expression, source_language)
    if source_language != "python":
        # Python precedence/literal rules are not an oracle for another language.
        return ("il valore di «" if it else "the value of “") + expression + ("»" if it else "”")
    try:
        node = ast.parse(expression, mode="eval").body
    except SyntaxError:
        return ("il valore di «" if it else "the value of “") + expression + ("»" if it else "”")
    def describe(node):
        if isinstance(node, ast.Name):
            return "«" + node.id + "»"
        if isinstance(node, ast.Constant):
            return repr(node.value)
        if isinstance(node, ast.BinOp):
            op = {ast.Add:("la somma", "the sum"), ast.Sub:("la differenza", "the difference"), ast.Mult:("il prodotto", "the product"), ast.Div:("il rapporto", "the ratio")}.get(type(node.op))
            if op and all(isinstance(part, ast.Constant) and type(part.value) in {int,float} for part in (node.left,node.right)):
                return op[0 if it else 1] + (" tra " if it else " of ") + describe(node.left) + (" e " if it else " and ") + describe(node.right)
        if isinstance(node, ast.List):
            if any(isinstance(part,ast.Starred) for part in node.elts):
                return "una lista con elementi espansi; lunghezza non ricostruita" if it else "a list with expanded elements; length not recovered"
            return ("una lista di " if it else "a list of ") + str(len(node.elts)) + (" elementi" if it else " elements")
        if isinstance(node, ast.Compare):
            return ("l’esito del confronto «" if it else "the result of comparison “") + ast.unparse(node) + ("»" if it else "”")
        return "«" + ast.unparse(node) + "»"
    return describe(node)


from .flow import python_facts, js_facts


from .java_flow import java_facts


def recover_behavior_facts(root, inventory, graph, progress=None):
    nodes_by_file = defaultdict(list)
    for node in graph["nodes"]:
        if node["kind"] in {"function", "method"} and node.get("path") and not node.get("metadata", {}).get("is_test_code"):
            nodes_by_file[node["path"]].append(node)
    source_hashes = {s["path"]: s["sha256"] for s in inventory.get("source_manifest", [])}
    http_handlers = {n.get("metadata", {}).get("handler") for n in graph["nodes"] if n["kind"] == "route"}
    response_bindings = defaultdict(list)
    for route in graph['nodes']:
        if route['kind'] == 'route' and route.get('metadata',{}).get('response_wrappers'):
            response_bindings[route['metadata']['handler']].append(route['metadata']['response_wrappers'])
    recovered, coverage = {}, []
    fact_count = 0
    def retain(node, value):
        nonlocal fact_count
        if fact_count + len(value) > BODY_FACT_BUDGET:
            coverage.append({'path':node['path'],'status':'partial','reason':f'{BODY_FACT_BUDGET} behavior-fact budget; body omitted: '+node['name']})
            return
        recovered[node['id']] = value
        fact_count += len(value)
    from .entry_selection import prioritize_body_files
    for path, nodes in prioritize_body_files(nodes_by_file, graph):
        if fact_count >= BODY_FACT_BUDGET:
            coverage.append({"path": path, "status": "partial", "reason": f"{BODY_FACT_BUDGET} behavior-fact budget reached; remaining bodies not interpreted"})
            break
        if progress:
            progress("behavior-interpretation")
        source = root / path
        try:
            size = source.stat().st_size
            data = source.read_bytes() if size <= 5 * 1024 * 1024 else b""
        except OSError:
            coverage.append({"path": path, "status": "failed", "reason": "source unavailable since inventory"})
            continue
        if size > 5 * 1024 * 1024:
            coverage.append({"path": path, "status": "partial", "reason": "behavior-source-byte-limit"})
            continue
        if sha256(data).hexdigest() != source_hashes.get(path):
            coverage.append({"path": path, "status": "failed", "reason": "source changed since inventory"})
            continue
        text = data.decode("utf-8", errors="replace")
        try:
            if path.endswith(".py"):
                tree = ast.parse(text)
                candidates = defaultdict(list)
                for item in ast.walk(tree):
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        candidates[(item.name, item.lineno)].append(item)
                for node in nodes:
                    line = node_line(node)
                    matches = candidates.get((node["name"], line), [])
                    if len(matches) == 1:
                        bindings = response_bindings.get(node['id'], [])
                        wrappers = bindings[0] if bindings and all(value == bindings[0] for value in bindings) else ()
                        retain(node, python_facts(matches[0], response_wrappers=wrappers))
            elif path.endswith(".java"):
                from ..scanners.java_syntax import parse, walk, field, text as syntax_text
                tree = parse(text)
                declarations = [n for n in walk(tree) if n.type == "method_declaration"]
                for node in nodes:
                    line = node_line(node)
                    matches = [n for n in declarations if syntax_text(field(n, "name")) == node["name"]
                               and n.start_point.row + 1 <= line <= field(n, "name").start_point.row + 1]
                    if len(matches) == 1:
                        retain(node, java_facts(field(matches[0], "body")))
                    else:
                        coverage.append({"path": path, "status": "partial", "reason": "Java declaration not uniquely located: " + node["name"]})
            elif Path(path).suffix in {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs", ".mts", ".cts"}:
                from ..scanners.javascript import parse, walk, FUNCTIONS
                tree = parse(text, Path(path).suffix)
                ast_nodes = {n.start_byte: n for n in walk(tree) if n.type in FUNCTIONS}
                for node in nodes:
                    syntax = ast_nodes.get(node.get("metadata", {}).get("start_byte"))
                    if syntax:
                        retain(node, js_facts(syntax, http_handler=node["id"] in http_handlers))
            coverage.append({"path": path, "status": "partial", "reason": "Bounded syntax interpretation, not symbolic execution or a business-intent oracle"})
        except (SyntaxError, ValueError, RecursionError):
            coverage.append({"path": path, "status": "failed", "reason": "unsupported syntax"})
    return recovered, coverage


def node_line(node):
    for item in node.get("provenance", {}).get("evidence", []):
        match = re.search(r":(\d+)$", item)
        if match:
            return int(match[1])
    return 1


def interpret_behavior(root, inventory, graph, semantic, api, progress=None):
    facts, coverage = recover_behavior_facts(root, inventory, graph, progress)
    nodes = {n["id"]: n for n in graph["nodes"]}
    stdlib_handlers = {n.get('metadata',{}).get('handler') for n in graph['nodes']
                       if n['kind']=='route' and n.get('metadata',{}).get('dispatch_profile')}
    adjacency = defaultdict(list)
    for edge in graph["edges"]:
        if edge["relation"] in {"calls", "calls_dependency", "calls_api", "calls_method_name"}:
            adjacency[edge["source"]].append(edge)
    def resolve(target):
        if target in nodes:
            return target
        match = re.fullmatch(r"method-name:([^#]+)#(.+)", target)
        if match:
            candidates = [n["id"] for n in nodes.values() if n["name"] == match[2] and n.get("metadata", {}).get("owner", "").split(".")[-1] == match[1]]
            return candidates[0] if len(candidates) == 1 else None
        return None
    def supported_call(source, edge, target):
        """Do not reintroduce dead calls through the broader structural graph."""
        path = nodes.get(source, {}).get("path", "")
        if source not in facts:
            return True  # Uninterpreted links retain their explicit partial scope.
        if path.endswith(".java"):
            # Structural Java edges point to declaration lines, not call-site lines.
            # Filter method links by retained call names, never reintroduce dead/nested calls.
            if edge["relation"] != "calls_method_name":
                return True
            return any(f["kind"] == "call" and f["callee"].rsplit(".", 1)[-1] == nodes[target]["name"]
                       for f in facts[source])
        lines = {int(match[1]) for loc in edge.get("evidence", [])
                 if (match := re.search(r":(\d+)$", loc))}
        name = edge.get("metadata", {}).get("callee") or nodes.get(target, {}).get("name")
        return any(f["kind"] == "call" and (not lines or f["line"] in lines)
                   and (not name or f["callee"] == name or f["callee"].rsplit(".", 1)[-1] == name)
                   for f in facts[source])
    hashes = {s["path"]: s["sha256"] for s in inventory.get("source_manifest", [])}
    api_by_id = {r["entity_ref"]: r for r in api if r.get("entity_ref")}
    def private_entry(row):
        name = row.get('name', '')
        return (row.get('visibility') in {'private', 'protected'} or
                (name.startswith('_') and not re.fullmatch(r'__[A-Za-z0-9_]+__', name)))

    def local_scope(row):
        if private_entry(row):
            return 'implementation-local', row.get('visibility') if row.get('visibility') in {'private', 'protected'} else 'private-convention'
        if row.get('conditional_declaration'):
            return 'conditional-local', row.get('visibility', 'undeclared')
        if row.get('is_nested') and row.get('visibility') == 'local-callable':
            return 'lexical-local', 'local-callable'
        if row.get('visibility') == 'package-private':
            return 'package-local', 'package-private'
        return None

    entries = [(b["id"], b["name"], b.get("entry_points", []), b) for b in semantic.get("behaviors", [])]
    semantic_entries_present = bool(entries)
    if not entries:
        # Library APIs have no HTTP actor. Summarize public callable behavior explicitly.
        selected_api = set()
        entries = [("api-behavior:" + r["id"], r["name"], [r["entity_ref"]], {}) for r in api
                   if r["kind"] in {"function", "method"} and not local_scope(r)
                   and r.get("entity_ref") in facts
                   and r.get("body_present") is not False
                   and not nodes.get(r["entity_ref"], {}).get("metadata", {}).get("is_test_code")]
        selected_api = {ref for _, _, refs, _ in entries for ref in refs}
        for row in api:
            if row.get("kind") not in {"function", "method"}:
                continue
            ref = row.get("entity_ref")
            if ref in selected_api:
                coverage.append({"path": row.get("path"), "status": "partial", "reason": "eligible and selected for library behavior summary",
                                 "entry": row.get("qualified_name", row.get("name")), "entity_ref": ref})
                continue
            if local_scope(row):
                reason = "excluded from public entries; considered for internal own-body summary"
            elif row.get("body_present") is False:
                reason = "excluded: declaration has no body"
            elif not ref:
                reason = "excluded: API declaration has no unique graph entity mapping"
            elif ref not in facts:
                reason = "excluded: body absent or unmapped"
            else:
                reason = "excluded: test-code declaration"
            coverage.append({"path": row.get("path"), "status": "partial", "reason": reason,
                             "entry": row.get("qualified_name", row.get("name")), "entity_ref": ref})
    elif semantic_entries_present:
        semantic_refs = {ref for _, _, refs, _ in entries for ref in refs}
        for row in api:
            if row.get("kind") not in {"function", "method"}:
                continue
            name, ref = row.get("name", ""), row.get("entity_ref")
            if ref in semantic_refs:
                reason = "selected: explicit semantic entry point"
            elif local_scope(row):
                reason = "excluded from semantic public entries; considered for internal own-body summary"
            elif row.get("body_present") is False:
                reason = "excluded: declaration has no body"
            elif not ref:
                reason = "excluded: API declaration has no unique graph entity mapping"
            elif ref not in facts:
                reason = "excluded: body absent or unmapped"
            elif nodes.get(ref, {}).get("metadata", {}).get("is_test_code"):
                reason = "excluded: test-code declaration"
            else:
                reason = "eligible but not selected: semantic entry points present"
            coverage.append({"path": row.get("path"), "status": "partial", "reason": reason,
                             "entry": row.get("qualified_name", name), "entity_ref": ref})
    from .entry_selection import prioritize
    entries = prioritize(entries, nodes)
    primary_entry_count = len(entries)
    primary_entries = entries[:1000]
    primary_refs = {ref for _, _, refs, _ in primary_entries for ref in refs}
    local_candidates = sorted(
        (row for row in api if local_scope(row)
         and row.get('entity_ref') not in primary_refs
         and row.get("entity_ref") in facts and facts.get(row.get("entity_ref"))
         and row.get("body_present") is not False
         and not nodes.get(row["entity_ref"], {}).get("metadata", {}).get("is_test_code")),
        key=lambda row: (row.get("path", ""), node_line(nodes[row["entity_ref"]]), row.get("qualified_name", ""), row["id"]),
    )
    local_slots = max(0, 1000 - len(primary_entries))
    local_entries = [("api-local-behavior:" + row["id"], row["name"], [row["entity_ref"]],
                      {"entry_scope": local_scope(row)[0], "entry_visibility": local_scope(row)[1]})
                     for row in local_candidates[:local_slots]]
    local_rows = [row for row in api if local_scope(row)]
    excluded_uninterpreted = sum(1 for row in local_rows
                                 if not facts.get(row.get("entity_ref")) or row.get("body_present") is False)
    excluded_budget = max(0, len(local_candidates) - local_slots)
    if local_rows:
        coverage.append({"path": None, "status": "partial",
                         "reason": ("Scoped local-callable selection: " + str(len(local_entries)) + " selected; "
                                    + str(excluded_uninterpreted) + " without admitted body evidence excluded; "
                                    + str(excluded_budget) + " excluded by the 1000-entry budget. "
                                    + "Empty or ambiguous bodies do not produce summaries.")})
    entries = primary_entries + local_entries
    selected_refs = {ref for _, _, refs, _ in entries for ref in refs}
    for row in api:
        if row.get('kind') not in {'function', 'method'}:
            continue
        ref = row.get('entity_ref')
        state = ('body-not-mapped' if ref not in facts else
                 'interpreted-with-admitted-facts' if facts[ref] else 'interpreted-no-admitted-facts')
        coverage.append({'path': row.get('path'), 'status': 'partial', 'entity_ref': ref,
                         'entry': row.get('qualified_name', row.get('name')),
                         'locations': row.get('locations', []), 'body_evidence_status': state,
                         'selected': ref in selected_refs,
                         'entry_scope': local_scope(row)[0] if local_scope(row) else 'primary-entry',
                         'reason': 'Body evidence inventory; no-admitted-facts is not proof of no behavior or effects'})
    records = []
    for entry_id, trigger, entry_points, behavior in entries:
        seen, frontier = set(), [(n, 0) for n in entry_points if n]
        while frontier and len(seen) < 40:
            current, depth = frontier.pop(0)
            if current in seen:
                continue
            seen.add(current)
            if behavior.get("entry_scope"):
                # A local summary stays on this callable's body; callers and callees
                # remain possible-call evidence without importing another body's facts.
                continue
            if depth < 4:
                frontier.extend((target, depth + 1) for edge in adjacency[current]
                                if (target := resolve(edge["target"])) and target not in seen
                                and supported_call(current, edge, target))
        evidence = []
        for ref in sorted(seen, key=lambda value: (value not in entry_points, value)):
            node = nodes.get(ref)
            if node and node.get("path") in hashes:
                evidence.append({"path": node["path"], "sha256": hashes[node["path"]], "line": node_line(node), "entity_ref": ref})
        interpreted = [{**fact, "entity_ref": ref} for ref in sorted(seen) for fact in facts.get(ref, [])]
        for fact in interpreted:
            fact["fact_id"] = "behavior-fact:" + identity([entry_id, fact])
        entry = next((api_by_id[n] for n in entry_points if n in api_by_id), None)
        if not interpreted:
            reason = ("Body is present, but no admitted return/error/effect evidence for " + trigger + "; no outcome or effect inferred"
                      if entry and entry.get("body_present") is True else
                      "No interpretable body for " + trigger + "; no reconstructed requirement invented")
            coverage.append({"path": next((loc["path"] for loc in evidence), None), "status": "partial", "reason": reason,
                             'entity_ref': entry_points[0] if len(entry_points) == 1 else None,
                             'locations': evidence, 'entry': trigger})
            continue
        returns = [f for f in interpreted if f["kind"] == "return" and not f.get("superseded_by_finally") and not f.get("withheld_by_partial_finally")]
        outward_returns = [f for f in returns if f["entity_ref"] in entry_points and f['entity_ref'] not in stdlib_handlers]
        if behavior:
            outward_returns += [f for f in interpreted if f["kind"] == "response" and f["entity_ref"] in entry_points]
        errors = [f for f in interpreted if f["kind"] == "throw" and not f.get("superseded_by_finally") and not f.get("caught_locally") and not f.get("withheld_by_partial_finally")]
        conditions = [f for f in interpreted if f["kind"] == "branch"]
        calls = [f for f in interpreted if f["kind"] == "call"]
        write_calls = [f for f in calls if f['callee'].rsplit('.', 1)[-1] in EFFECT_NAMES
                       and ('.' in f['callee'] or nodes.get(f['entity_ref'], {}).get('path', '').endswith('.java'))]
        record = {"id": "recovered-requirement:" + identity(entry_id), "kind": "reconstructed-functional-requirement",
                  "name": trigger,
                  "authority": "static-inference", "confidence": "medium" if interpreted else "low", "locations": evidence,
                  "entry_ref": entry_id, "entry_points": entry_points, "entry_path": next((nodes[n].get("path") for n in entry_points if n in nodes), None),
                  "entity_refs": sorted(seen), "actor": "caller; business role not established",
                  "inputs": entry.get("params") if entry else None, "conditions": conditions, "returns": returns, "errors": errors,
                  "external_outcomes": outward_returns,
                  "effects": write_calls, "facts": interpreted, "flow_limits": list(dict.fromkeys(f["expression"] for f in interpreted if f["kind"] == "unsupported-flow")),
                  "coverage": {"status": "partial", "method": BEHAVIOR_PROFILE, "max_call_depth": 4, "max_entities": 40},
                  "unknowns": ["Original stakeholder need, business role, historical intent and runtime satisfaction are not established.",
                               "Possible calls and return expressions do not prove execution order or reachability. Names alone do not prove persistence.",
                               "External calls, dynamic dispatch, compiler transformations and transitive exceptions remain partial."],
                  "test_ideas": [{"kind": "characterization-proposal", "condition": f["conditions"], "expected_from_implementation": f["expression"],
                                  "status": "proposed, not executed; independent requirement oracle needed"} for f in (returns + errors)[:20]]}
        if behavior.get("entry_scope"):
            record["entry_ref"] = entry_points[0] if entry_points else entry_id
            record["entry_scope"] = behavior["entry_scope"]
            record["entry_visibility"] = behavior["entry_visibility"]
            record["coverage"].update({"max_call_depth": 0, "max_entities": 1})
        if entry and entry.get('conditional_declaration'):
            record['conditional_declaration'] = True
            record['declaration_context'] = entry['declaration_context']
            record['unknowns'].append('Conditional declaration: runtime availability is not established; context is source syntax, not a solved predicate.')
        if behavior:
            declarations = []
            for item in behavior.get('provenance', {}).get('evidence', []):
                match = re.fullmatch(r'(.+):(\d+)', item)
                if match and match[1] in hashes:
                    declarations.append({'path':match[1], 'line':int(match[2]), 'sha256':hashes[match[1]]})
            record['entry_declaration_locations'] = declarations
        from .narrative import explain_behavior
        record["explanation"] = explain_behavior(record, explain_expression)
        record.update({key: record["explanation"][key] for key in ("statement_it", "statement_en")})
        record["statement"] = record["statement_it"]
        record["record_digest"] = identity(record)
        records.append(record)
    if primary_entry_count > 1000:
        coverage.append({"path": None, "status": "partial", "reason": f"1000-entry interpretation limit; {primary_entry_count - 1000} public or semantic entries omitted"})
    return records, coverage
