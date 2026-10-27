"""Public snapshot projection. Internal graph IDs remain private implementation details."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import PurePosixPath
import re

from .export import generic_context
from .scanners.filesystem import CODE_EXTS, FRONTEND_INPUTS

SCHEMA = "ases-consumer-context/2.0"
PROFILE = {"identity": "source-symbol/2", "relations": "static/2", "coverage": "scoped/2"}
RELATION_FAMILIES = {
    "declares": "declarations", "imports": "imports", "imports_type": "imports",
    "calls": "calls", "calls_api": "calls", "calls_dependency": "calls", "calls_method_name": "calls",
    "handled_by": "calls", "extends": "type_heritage", "implements": "type_heritage",
    "protects": "controls", "protects_or_validates": "controls", "session_affects": "controls",
    "tests": "tests", "test_candidate": "tests",
}
FAMILIES = {"declarations", "imports", "calls", "type_heritage", "controls", "tests"}
COVERAGE_STATES = {"ANALYZED", "PARTIAL", "UNKNOWN", "NOT_OBSERVED", "NOT_APPLICABLE"}


def relationship_coverage(files, sources):
    result = {}
    for path, file in files.items():
        families = file.pop("families", {})
        suffix = PurePosixPath(path).suffix.lower()
        source = sources.get(path, {})
        for family in sorted(FAMILIES):
            if family in families:
                continue
            status, method, admitted, reason = "UNKNOWN", "unsupported", "no admitted relation extractor", "relation_method_not_admitted"
            if suffix in {".py", ".java"}:
                status, method, admitted, reason = "PARTIAL", "legacy-static-heuristic", "extractor-supported source patterns", "legacy_relationship_resolution_partial"
            if suffix in FRONTEND_INPUTS and family in {"declarations", "calls"}:
                if family == "declarations":
                    status, method, admitted, reason = "PARTIAL", "frontend-heuristic", "template/script component classification", "template_or_component_grammar_partial"
                elif suffix not in {".vue", ".svelte"}:
                    status, method, admitted, reason = "PARTIAL", "literal-form-heuristic", "literal HTML form tags; native template grammar unparsed", "template_grammar_not_exhaustive"
                else:
                    reason = "embedded_script_grammar_not_admitted"
            if family == "controls" and suffix in {".kt", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"}:
                status, method, admitted, reason = "PARTIAL", "lexical-control-heuristic", "local control/session signals and admitted method decorators", "framework_global_enforcement_unverified"
            if family == "tests":
                if source.get("role") != "TEST":
                    status, method, admitted, reason = "NOT_APPLICABLE", "source-role-classification", "test source links", "not_classified_as_test_source"
                elif suffix in {".py", ".java", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"}:
                    status, method, admitted, reason = "PARTIAL", "static-and-name-test-links", "test imports/calls and separate nominal candidates", "test_execution_and_assertions_unverified"
            if file.get("status") == "UNKNOWN":
                status, reason = "UNKNOWN", str(file.get("basis", "extractor unavailable"))
            families[family] = {"status": status, "method": method,
                                "scope": {"path": path, "admitted": admitted},
                                "reasons": [reason], "omitted_count": None}
        result[path] = families
    return result


def digest(value) -> str:
    try:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("Value is not canonicalizable JSON") from exc
    return sha256(payload).hexdigest()


def location(value: str) -> dict:
    if "://" in value:
        return {"kind": "source", "path": value, "line": None}
    match = re.fullmatch(r"(.+):(\d+)", value)
    if match and PurePosixPath(match[1].replace("\\", "/")).suffix.lower() in CODE_EXTS.keys() | FRONTEND_INPUTS.keys():
        return {"kind": "source", "path": match[1].replace("\\", "/"), "line": int(match[2])}
    return {"kind": "source", "path": value.replace("\\", "/"), "line": None}


def _signature(node: dict, nodes: dict) -> list:
    owner = nodes.get(node.get("metadata", {}).get("owner"), {})
    meta = node.get("metadata", {})
    return [node["kind"], node.get("path"), owner.get("name"), node["name"],
            meta.get("normalized_params", re.sub(r"\s+", "", meta.get("params", ""))), meta.get("http_method"),
            meta.get("path"), meta.get("identity_scope")]


def public_context(model: dict, graph: dict, inventory: dict, manifest: dict) -> dict:
    context = deepcopy(generic_context(model, manifest))
    context["schema"] = SCHEMA
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    signatures = {key: _signature(node, nodes) for key, node in nodes.items()}
    counts = Counter(digest(sig) for sig in signatures.values())
    occurrences = Counter()
    mapping, identities = {}, {}
    for key, sig in signatures.items():
        base = digest(sig)
        index = occurrences[base]
        occurrences[base] += 1
        mapping[key] = "entity:" + digest([sig, index if counts[base] > 1 else None])[:24]
        identities[key] = {"strategy": PROFILE["identity"], "scope": "module",
                           "state": "ambiguous" if counts[base] > 1 else "unique",
                           "key": sig}
    # Derived rows have their own identities; observed source locations never include line IDs.
    derived = {}
    for family, rows in context.items():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict) or not row.get("id") or row["id"] in mapping:
                continue
            old = row["id"]
            if old.startswith("behavior:") and old[9:] in mapping:
                new = "behavior:" + mapping[old[9:]]
            elif row.get("nodes"):
                new = "sensitive-path:" + digest([mapping.get(x, x) for x in row["nodes"]])[:24]
            else:
                ev = row.get("provenance", {}).get("evidence", row.get("evidence", []))
                anchors = sorted({location(str(e))["path"] for e in ev})
                new = family + ":" + digest([row.get("fingerprint") or row.get("name") or
                                             row.get("statement") or old, row.get("kind"), anchors])[:24]
            derived[old] = new
    mapping.update(derived)

    def remap(value):
        if isinstance(value, dict):
            result = {k: remap(v) for k, v in value.items()}
            if value.get("id") in mapping:
                result["legacy_id"] = value["id"]
            return result
        if isinstance(value, list):
            return [remap(v) for v in value]
        return mapping.get(value, value) if isinstance(value, str) else value

    context = remap(context)
    for path in context.get("sensitive_paths", []):
        path["status"] = "INFERRED"
        path["basis"] = "static-reachability"
    for link in context.get("trace_links", []):
        if link.get("basis") == "name-hint":
            link["relation"] = "candidate_test_link"
    sources = {s["path"]: s for s in inventory.get("source_manifest", [])}
    observations = {}

    def observation(subject, predicate, evidence, state, authority, limitations, method="static", assumptions=None):
        locs = sorted((location(str(e)) for e in set(evidence)), key=lambda x: (x["path"], x["line"] or 0))
        paths = {x["path"] for x in locs}
        record = {"subject_ref": subject, "predicate": predicate, "locations": locs,
                  "source_hashes": {p: sources[p]["sha256"] for p in sorted(paths) if p in sources},
                  "source_roles": {p: sources[p].get("role", "UNKNOWN") for p in sorted(paths) if p in sources},
                  "state": state, "authority": authority, "limitations": limitations,
                  "assumptions": assumptions or [],
                  "confidence": "high" if authority == "source-syntax" and method == "tree-sitter" else "medium",
                  "source_descriptor": {"publisher": "ASES", "type": "first-party-project-tool", "independence": "same-ecosystem"},
                  "extractor": {"name": "ases", "version": model.get("ases_version"), "method": method}}
        oid = "observation:" + digest(record)
        observations[oid] = {"id": oid, **record}
        return oid

    context["entities"] = []
    for key, node in nodes.items():
        nid = mapping[key]
        oid = observation(nid, "entity.declared", node.get("provenance", {}).get("evidence", []),
                          node.get("provenance", {}).get("state", "OBSERVED"), "source-syntax",
                          ["Static declaration does not establish runtime execution."] + node.get("provenance", {}).get("limitations", []),
                          node.get("metadata", {}).get("extraction_method", "static-heuristic"),
                          node.get("provenance", {}).get("assumptions", []))
        properties = remap(node.get("metadata", {}))
        for volatile in ("start_byte", "end_byte", "params"):
            properties.pop(volatile, None)
        context["entities"].append({"id": nid, "legacy_id": key, "name": node["name"],
                                    "kind": node["kind"], "path": node.get("path"),
                                    "identity": identities[key], "properties": properties,
                                    "observation_refs": [oid]})
    context["structural_relations"] = []
    for edge in graph.get("edges", []):
        if edge["source"] not in nodes or edge["target"] not in nodes:
            continue  # symbolic markers are not public entity endpoints
        src, dst = mapping[edge["source"]], mapping[edge["target"]]
        meta = edge.get("metadata", {})
        relation = "test_candidate" if edge["relation"] == "tests" and meta.get("basis") == "name-hint" else edge["relation"]
        rid = "relation:" + digest([src, dst, relation])[:24]
        oid = observation(rid, relation, edge.get("evidence", []), "INFERRED",
                          "static-relationship", ["Static relationships do not prove execution or effectiveness."],
                          meta.get("basis", "scanner-static"))
        context["structural_relations"].append({"id": rid, "from": src, "to": dst,
                                               "relation": relation, "state": "INFERRED",
                                               "basis": meta.get("basis", "scanner-static"),
                                               "observation_refs": [oid]})
    context["observations"] = sorted(observations.values(), key=lambda x: x["id"])
    context["entities"].sort(key=lambda x: x["id"])
    context["structural_relations"].sort(key=lambda x: x["id"])
    context["identity_mapping"] = sorted(({"legacy_id": k, "canonical_id": v,
                                           "state": identities.get(k, {}).get("state", "unique")}
                                          for k, v in mapping.items()), key=lambda x: x["legacy_id"])
    context["analysis_profile"] = {**PROFILE, "ases_version": model.get("ases_version"),
                                    "source_mode": model.get("project", {}).get("source_mode", "REPOSITORY"),
                                    "parser": inventory.get("parser_profile", {}),
                                    "exclusions": inventory.get("exclusions", [])}
    files = deepcopy(graph.get("coverage", {}))
    for path, source in sources.items():
        if source.get("role") not in {"OWNED_SOURCE", "TEST"}:
            continue
        if path not in files:
            files[path] = {"status": "PARTIAL", "basis": "heuristic extraction or unsupported language",
                           "omitted_count": None, "limitations": ["No exhaustive declaration/relationship analysis."]}
    families = relationship_coverage(files, sources)
    context["coverage"] = {"files": files, "relationship_families": families, "paths": deepcopy(model.get("path_coverage", [])),
                           "dimensions": deepcopy(model.get("semantic_quality", {}).get("analysis_coverage", {}))}
    path_coverage = {row["entry_point"]: row for row in remap(context["coverage"]["paths"])}
    context["coverage"]["paths"] = list(path_coverage.values())
    entities_by_id = {row["id"]: row for row in context["entities"]}
    for behavior in context.get("behaviors", []):
        behavior["basis"] = "static-route-flow"
        behavior["provenance"]["state"] = "INFERRED"
        behavior["provenance"]["confidence"] = "medium"
        behavior["provenance"].setdefault("assumptions", []).append("Static route flow does not establish runtime execution.")
        behavior["observation_refs"] = sorted({ref for nid in behavior.get("main_flow", []) for ref in entities_by_id.get(nid, {}).get("observation_refs", [])})
    relations_by_pair = {}
    for row in context["structural_relations"]:
        relations_by_pair.setdefault((row["from"], row["to"]), []).append(row)
    for path in context.get("sensitive_paths", []):
        chain = path.get("nodes", [])
        support = [row for pair in zip(chain, chain[1:]) for row in relations_by_pair.get(pair, [])]
        support += [row for src, dst in zip(chain, chain[1:]) for row in relations_by_pair.get((dst, src), []) if row["relation"] == "implements"]
        path["relation_refs"] = sorted({row["id"] for row in support})
        path["observation_refs"] = sorted({ref for row in support for ref in row["observation_refs"]}
                                          | {ref for nid in chain for ref in entities_by_id.get(nid, {}).get("observation_refs", [])})
        path["coverage"] = path_coverage.get(path.get("entry_point"), {"status": "UNKNOWN", "omitted_count": None})
        path["basis"] = "static-reachability"
    if any(row.get("status") != "ANALYZED" for row in files.values()):
        for dimension in ("source_structure", "static_behavior", "architecture"):
            if context["coverage"]["dimensions"].get(dimension, {}).get("status") == "ANALYZED":
                context["coverage"]["dimensions"][dimension] = {"status": "PARTIAL", "basis": "See per-file extractor coverage and residual unknowns."}
    context["analysis_unknowns"] = remap(deepcopy(graph.get("unknowns", [])))
    context["source_manifest"] = deepcopy(inventory.get("source_manifest", []))
    context["source_scope"] = deepcopy(inventory.get("source_scope", {}))
    context["technical_relation_counts"] = dict(Counter(x["relation"] for x in context["structural_relations"]))
    context["validation"] = {"status": "PASS", "meaning": "Snapshot consistency only; source freshness and runtime are unverified."}
    context["untrusted_content"] = True
    seal_context(context)
    validate_context(context)
    return context


def seal_context(context: dict) -> dict:
    context["snapshot_id"] = "snapshot:" + digest({k: v for k, v in context.items() if k not in {"generated_at", "snapshot_id"}})
    return context


def validate_context(context: dict) -> None:
    if context.get("schema") != SCHEMA:
        raise ValueError("Unsupported public snapshot schema")
    for collection in ("entities", "observations", "structural_relations", "identity_mapping"):
        if not isinstance(context.get(collection), list):
            raise ValueError(f"Invalid snapshot collection: {collection}")
        if any(not isinstance(row, dict) for row in context[collection]):
            raise ValueError(f"Malformed snapshot record: {collection}")
    entities = [n.get("id") for n in context["entities"]]
    observations = [n.get("id") for n in context["observations"]]
    if any(not isinstance(value, str) for value in entities + observations) or len(set(entities)) != len(entities) or len(set(observations)) != len(observations):
        raise ValueError("Duplicate or missing snapshot identity")
    entity_ids, observation_ids = set(entities), set(observations)
    for name in ("analysis_unknowns", "behaviors", "components", "interfaces", "data_stores", "external_systems", "trust_boundaries", "controls", "sessions", "sensitive_paths", "frontend_findings", "cross_boundary_findings", "claims", "tests", "trace_links"):
        rows = context.get(name, [])
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError(f"Malformed snapshot collection: {name}")
        for row in rows:
            for key in ("id", "fingerprint", "path"):
                if row.get(key) is not None and not isinstance(row[key], str):
                    raise ValueError(f"Malformed snapshot {name}.{key}")
            if "provenance" in row:
                provenance = row["provenance"]
                if not isinstance(provenance, dict) or not isinstance(provenance.get("evidence", []), list) or any(not isinstance(e, str) for e in provenance.get("evidence", [])):
                    raise ValueError("Malformed snapshot provenance")
            for key in ("main_flow", "call_refs", "observation_refs"):
                if key in row and (not isinstance(row[key], list) or any(not isinstance(ref, str) for ref in row[key])):
                    raise ValueError(f"Malformed snapshot {name}.{key}")
    relation_ids = [row.get("id") for row in context["structural_relations"]]
    if any(not isinstance(value, str) for value in relation_ids) or len(set(relation_ids)) != len(relation_ids):
        raise ValueError("Duplicate or missing structural identity")
    subject_ids = entity_ids | set(relation_ids)
    for row in context["entities"]:
        if not isinstance(row.get("name"), str) or not isinstance(row.get("kind"), str) or not isinstance(row.get("identity"), dict) or row["identity"].get("state") not in {"unique", "ambiguous"}:
            raise ValueError("Malformed entity declaration/identity")
        if row.get("path") is not None and not isinstance(row["path"], str) or not isinstance(row.get("properties", {}), dict):
            raise ValueError("Malformed entity path/properties")
    for row in context["identity_mapping"]:
        if not isinstance(row.get("legacy_id"), str) or not isinstance(row.get("canonical_id"), str) or row.get("state") not in {"unique", "ambiguous"}:
            raise ValueError("Malformed identity mapping")
    for row in context["entities"] + context["structural_relations"]:
        if not isinstance(row.get("observation_refs"), list):
            raise ValueError("Invalid observation references")
        if any(not isinstance(ref, str) or ref not in observation_ids for ref in row.get("observation_refs", [])):
            raise ValueError("Dangling observation reference")
    for row in context["structural_relations"]:
        if not isinstance(row.get("from"), str) or not isinstance(row.get("to"), str) or row["from"] not in entity_ids or row["to"] not in entity_ids:
            raise ValueError("Dangling structural endpoint")
        if row.get("state") != "INFERRED" or not isinstance(row.get("relation"), str) or not isinstance(row.get("basis"), str):
            raise ValueError("Invalid static structural authority")
    if not isinstance(context.get("coverage"), dict) or not isinstance(context["coverage"].get("files"), dict) or not isinstance(context.get("analysis_profile"), dict):
        raise ValueError("Invalid snapshot profile/coverage")
    for path, row in context["coverage"]["files"].items():
        if not isinstance(path, str) or not isinstance(row, dict) or row.get("status") not in {"ANALYZED", "PARTIAL", "UNKNOWN", "NOT_OBSERVED", "NOT_APPLICABLE"}:
            raise ValueError("Malformed file coverage")
    families = context["coverage"].get("relationship_families")
    if context["analysis_profile"].get("coverage") == "scoped/2" and not isinstance(families, dict):
        raise ValueError("Missing relationship family coverage")
    if families is not None:
        if not isinstance(families, dict):
            raise ValueError("Malformed relationship family coverage")
        if context["analysis_profile"].get("coverage") == "scoped/2" and set(families) != set(context["coverage"]["files"]):
            raise ValueError("Missing relationship family coverage scope")
        for path, groups in families.items():
            if path not in context["coverage"]["files"] or not isinstance(groups, dict) or set(groups) != FAMILIES:
                raise ValueError("Malformed relationship family coverage scope")
            for row in groups.values():
                if (not isinstance(row, dict) or row.get("status") not in COVERAGE_STATES or
                    not isinstance(row.get("method"), str) or not row["method"] or
                    not isinstance(row.get("scope"), dict) or row["scope"].get("path") != path or
                    not isinstance(row["scope"].get("admitted"), str) or not row["scope"]["admitted"] or
                    not isinstance(row.get("reasons"), list) or any(not isinstance(reason, str) for reason in row["reasons"]) or
                    "omitted_count" not in row or row["omitted_count"] is not None and (type(row["omitted_count"]) is not int or row["omitted_count"] < 0)):
                    raise ValueError("Malformed relationship family coverage")
    if not isinstance(context.get("source_manifest"), list):
        raise ValueError("Malformed source manifest")
    for row in context["source_manifest"]:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str) or not isinstance(row.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            raise ValueError("Malformed source digest")
    for observation in context["observations"]:
        if observation.get("state") not in {"CONFIRMED", "OBSERVED", "INFERRED", "UNKNOWN", "CONFLICTING"} or not isinstance(observation.get("locations"), list):
            raise ValueError("Invalid observation authority/state/location")
        if not isinstance(observation.get("subject_ref"), str) or observation["subject_ref"] not in subject_ids or observation.get("authority") not in {"source-syntax", "static-relationship"}:
            raise ValueError("Invalid observation subject/authority")
        if observation.get("authority") == "static-relationship" and observation["state"] != "INFERRED":
            raise ValueError("Static relationship cannot claim observed runtime authority")
        for loc in observation["locations"]:
            if not isinstance(loc, dict) or not isinstance(loc.get("path"), str) or loc.get("line") is not None and (type(loc["line"]) is not int or loc["line"] < 1):
                raise ValueError("Malformed source location")
    expected = "snapshot:" + digest({k: v for k, v in context.items() if k not in {"generated_at", "snapshot_id"}})
    if context.get("snapshot_id") != expected:
        raise ValueError("Snapshot digest mismatch")
