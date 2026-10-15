"""Deterministic read-only projections of a sealed public snapshot."""
from collections import defaultdict, deque
from .evidence import validate_context

COLLECTIONS = {"entities", "structural_relations", "observations", "analysis_unknowns", "behaviors", "controls", "tests", "external_systems"}
TRAVERSABLE = {"calls", "calls_api", "handled_by", "calls_dependency"}


def inspect_snapshot(context, *, collection=None, selector=None, offset=0, limit=64):
    validate_context(context)
    if offset < 0 or not 1 <= limit <= 1000:
        raise ValueError("offset must be non-negative and limit between 1 and 1000")
    result = {"schema": "ases-analysis-view/1.0", "parent_snapshot_id": context["snapshot_id"]}
    if collection is None:
        files = context["coverage"].get("files", {})
        result["summary"] = {"project": context["project"], "counts": {k: len(context.get(k, [])) for k in sorted(COLLECTIONS)},
                             "file_coverage": {s: sum(x.get("status") == s for x in files.values())
                                               for s in ("ANALYZED", "PARTIAL", "UNKNOWN")},
                             "analysis_profile": context["analysis_profile"],
                             "limitations": ["Static structure is not runtime execution or security assurance."]}
        return result
    if collection not in COLLECTIONS:
        raise ValueError("Unsupported snapshot collection")
    rows = context.get(collection, [])
    if selector is not None:
        rows = [r for r in rows if selector in (r.get("id"), r.get("name"), r.get("path"))]
    rows = sorted(rows, key=lambda r: (r.get("id", ""), str(r)))
    result.update({"collection": collection, "items": rows[offset:offset + limit],
                   "selection": "ambiguous" if selector and len(rows) > 1 else "exact" if rows else "not_found",
                   "pagination": {"offset": offset, "limit": limit, "total": len(rows),
                                  "next_offset": offset + limit if offset + limit < len(rows) else None},
                   "source_coverage": context["coverage"].get("dimensions", {}),
                   "delivery_only": True})
    if selector is not None:
        selected_ids = {row.get("id") for row in result["items"]}
        attached = [row for row in context["structural_relations"] if row["from"] in selected_ids or row["to"] in selected_ids or row["id"] in selected_ids]
        refs = {ref for row in result["items"] + attached for ref in row.get("observation_refs", [])}
        result["matching_basis"] = "exact ID/name/path in saved collection"
        result["relations"] = attached
        result["observations"] = [row for row in context["observations"] if row["id"] in refs]
    return result


def trace_snapshot(context, selector, *, direction="forward", max_nodes=10000):
    validate_context(context)
    if direction not in {"forward", "backward"} or not 1 <= max_nodes <= 10000:
        raise ValueError("Invalid trace direction or node limit")
    entities = {r["id"]: r for r in context["entities"]}
    seeds = sorted(k for k, r in entities.items() if selector in (k, r["name"], r.get("path")))
    if not seeds:
        for behavior in context.get("behaviors", []):
            if selector == behavior["id"]:
                seeds = sorted(n for n in behavior.get("main_flow", [])[:1] if n in entities)
        for system in context.get("external_systems", []):
            if selector in (system.get("id"), system.get("name")):
                seeds = sorted(n for n in system.get("call_refs", []) if n in entities)
    result = {"schema": "ases-feature-trace/1.0", "parent_snapshot_id": context["snapshot_id"],
              "selector": selector, "direction": direction, "seed_ids": seeds,
              "selection": "ambiguous" if len(seeds) > 1 else "exact" if seeds else "not_found",
              "limitations": ["Reachability in this static graph does not prove execution or data sensitivity."]}
    if len(seeds) != 1:
        result.update({"entities": [], "relations": [], "observations": [], "coverage": {"status": "UNKNOWN", "basis": "selector missing or ambiguous"}})
        return result
    adjacency = defaultdict(list)
    for relation in context["structural_relations"]:
        if relation["relation"] in TRAVERSABLE:
            adjacency[relation["from"] if direction == "forward" else relation["to"]].append(relation)
    queue, visited, relations = deque(seeds), set(), {}
    while queue and len(visited) < max_nodes:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        for relation in sorted(adjacency[node], key=lambda r: r["id"]):
            destination = relation["to"] if direction == "forward" else relation["from"]
            if destination not in visited:
                queue.append(destination)
            relations[relation["id"]] = relation
    # Keep attached control/test observations alongside the call subgraph without traversing them.
    for relation in context["structural_relations"]:
        if relation["to"] in visited and relation["relation"] in {"protects", "protects_or_validates", "tests", "session_affects"}:
            relations[relation["id"]] = relation
    represented = visited | {r[k] for r in relations.values() for k in ("from", "to")}
    paths = {entities[n].get("path") for n in visited}
    unknowns = [u for u in context.get("analysis_unknowns", []) if u.get("path") in paths]
    incomplete = any(context["coverage"]["files"].get(path, {}).get("relationships") != "ANALYZED" for path in paths if path)
    refs = {ref for n in represented for ref in entities[n].get("observation_refs", [])}
    refs |= {ref for r in relations.values() for ref in r["observation_refs"]}
    result.update({"entities": [entities[n] for n in sorted(represented)],
                   "relations": sorted(relations.values(), key=lambda r: r["id"]),
                   "observations": [o for o in context["observations"] if o["id"] in refs],
                   "residual_unknowns": unknowns,
                   "coverage": {"status": "PARTIAL" if queue or unknowns or incomplete else "ANALYZED",
                                "basis": "supported static relations only; max_nodes limits expanded entities, attached endpoints remain represented",
                                "max_expanded_nodes": max_nodes, "expanded_nodes": len(visited), "truncated": bool(queue),
                                "omitted_count": None if queue or unknowns or incomplete else 0}})
    return result
