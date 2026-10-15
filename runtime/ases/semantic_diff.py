"""Inventory changes with explicit absence authority; never a security verdict."""
from __future__ import annotations

import json
from pathlib import Path
from .evidence import location, RELATION_FAMILIES

DIMENSIONS = ("behaviors", "components", "interfaces", "data_stores", "external_systems",
              "trust_boundaries", "controls", "sessions", "sensitive_paths", "frontend_findings",
              "cross_boundary_findings", "claims", "tests", "trace_links", "entities", "structural_relations")
SUPPORTED_SCHEMAS = {f"ases-consumer-context/{v}" for v in ("1.3", "1.4", "1.5", "2.0")}
VOLATILE = {"generated_at", "project_fingerprint", "snapshot_id", "evidence_strength", "legacy_id",
            "observation_refs", "line", "lines", "source_hashes", "identity_mapping"}


def load_context(path: Path) -> dict:
    if path.is_dir():
        path = path / ("consumer-context.v2.json" if (path / "consumer-context.v2.json").is_file()
                       else "consumer-context.json")
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("Snapshot must be a bounded regular file")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("Malformed snapshot JSON") from exc
    if not isinstance(data, dict) or data.get("schema") not in SUPPORTED_SCHEMAS:
        raise ValueError(f"Unsupported ASES consumer context: {path}")
    for name in DIMENSIONS:
        if name not in data:
            continue
        rows = data[name]
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError(f"Malformed snapshot collection: {name}")
        for row in rows:
            for key in ("id", "fingerprint", "path"):
                if row.get(key) is not None and not isinstance(row[key], str):
                    raise ValueError(f"Malformed snapshot {name}.{key}")
    if data["schema"].endswith("/2.0"):
        from .evidence import validate_context
        validate_context(data)
    return data


def _key(row):
    return row.get("fingerprint") or row.get("id") or ("|".join(str(row[k]) for k in ("from", "to", "relation"))
                                                       if all(k in row for k in ("from", "to", "relation")) else None)


def _meaning(value, field=""):
    if isinstance(value, dict):
        return {k: _meaning(v, k) for k, v in value.items() if k not in VOLATILE and not (k == "params" and "normalized_params" in value)}
    if isinstance(value, list):
        rows = [_meaning(v, field) for v in value]
        if field == "evidence":
            unique = {json.dumps(row, sort_keys=True): row for row in rows}
            return [unique[key] for key in sorted(unique)]  # Several lines can share one source anchor.
        return rows if field in {"nodes", "main_flow", "alternatives", "key", "normalized_params"} else sorted(rows, key=lambda x: json.dumps(x, sort_keys=True))
    if isinstance(value, str) and field == "evidence":
        return location(value)["path"]
    return value


def _family_presence(context, reference, source, family):
    if not source or not family:
        return False
    current = context.get("coverage", {}).get("relationship_families", {}).get(source, {}).get(family, {})
    previous = (reference or {}).get("coverage", {}).get("relationship_families", {}).get(source, {}).get(family, {})
    return (current.get("status") == "ANALYZED" and bool(current.get("method")) and bool(current.get("scope")) and
            all(current.get(key) == previous.get(key) for key in ("method", "scope")))


def _presence(context, row, dimension, reference=None):
    if dimension not in {"entities", "structural_relations"} and context.get("coverage", {}).get("dimensions", {}).get(dimension, {}).get("status") != "ANALYZED":
        return False  # Declaration coverage does not establish exhaustive derived detection.
    paths = {row.get("path")} - {None}
    paths.update(location(e)["path"] for e in row.get("provenance", {}).get("evidence", []))
    if not paths:
        entities = {n["id"]: n for n in context.get("entities", [])}
        paths.update(entities[k].get("path") for k in (row.get("from"), row.get("to")) if k in entities)
        paths.discard(None)
    files = context.get("coverage", {}).get("files", {})
    if dimension == "structural_relations":
        # Relation extraction is scoped to its source endpoint; a target file's unrelated
        # methods cannot establish or deny that outgoing relation.
        entities = {n["id"]: n for n in context.get("entities", [])}
        source = entities.get(row.get("from"), {}).get("path")
        family = RELATION_FAMILIES.get(row.get("relation"))
        return _family_presence(context, reference, source, family)
    if dimension == "entities":
        family = {"route": "calls", "frontend_route": "calls", "external_api_call": "calls", "frontend_api_call": "calls",
                  "control": "controls", "session_operation": "controls", "test": "tests"}.get(row.get("kind"))
        if family:
            return _family_presence(context, reference, row.get("path"), family)
    return bool(paths) and all(files.get(p, {}).get("status") == "ANALYZED" for p in paths)


def semantic_diff(before: dict, after: dict) -> dict:
    modern = before.get("schema") == after.get("schema") == "ases-consumer-context/2.0"
    profile_changed = before.get("analysis_profile") != after.get("analysis_profile")
    dimensions, totals, uncertainty = {}, {"added": 0, "removed": 0, "changed": 0}, []
    aliases = {r["legacy_id"]: r["canonical_id"] for r in after.get("identity_mapping", []) if r.get("state") == "unique"}
    remappings, remap_candidates = [], []
    if before.get("schema") != after.get("schema") and after.get("schema") == "ases-consumer-context/2.0":
        # Legacy contexts lack complete symbol signatures. Match only unique scoped rows.
        for dimension in DIMENSIONS:
            groups = []
            for context in (before, after):
                by_scope = {}
                for row in context.get(dimension, []):
                    if not isinstance(row, dict) or not _key(row) or not row.get("name"):
                        continue
                    anchors = {row.get("path")} - {None}
                    anchors.update(location(str(e))["path"] for e in row.get("provenance", {}).get("evidence", []))
                    if anchors:
                        shape = (row.get("kind"), row["name"], tuple(sorted(anchors)))
                        by_scope.setdefault(shape, []).append(_key(row))
                groups.append(by_scope)
            left, right = groups
            for shape in left.keys() & right.keys():
                if len(left[shape]) == len(right[shape]) == 1:
                    old_id, new_id = left[shape][0], right[shape][0]
                    aliases[old_id] = new_id
                    if old_id != new_id:
                        remappings.append({"dimension": dimension, "before": old_id, "after": new_id,
                                           "basis": "unique-legacy-family-name-source", "state": "INFERRED"})
                else:
                    remap_candidates.append({"dimension": dimension, "before": left[shape], "after": right[shape], "state": "AMBIGUOUS"})
    if modern:
        old_entities = {r["id"]: r for r in before.get("entities", [])}
        new_entities = {r["id"]: r for r in after.get("entities", [])}
        old_by_shape, new_by_shape = {}, {}
        for rows, groups in ((old_entities, old_by_shape), (new_entities, new_by_shape)):
            for entity in rows.values():
                shape = entity.get("properties", {}).get("structure_fingerprint")
                if shape:
                    groups.setdefault((entity["kind"], shape), []).append(entity["id"])
        for shape in sorted(old_by_shape.keys() & new_by_shape.keys()):
            left, right = old_by_shape[shape], new_by_shape[shape]
            if len(left) == len(right) == 1 and left[0] != right[0] and left[0] not in new_entities and right[0] not in old_entities:
                aliases[left[0]] = right[0]
                remappings.append({"before": left[0], "after": right[0], "basis": "unique-structural-fingerprint", "state": "INFERRED"})
            elif len(left) > 1 or len(right) > 1:
                remap_candidates.append({"before": left, "after": right, "state": "AMBIGUOUS"})
    def remap_meaning(value):
        if isinstance(value, dict):
            return {k: remap_meaning(v) for k, v in value.items()}
        if isinstance(value, list):
            return [remap_meaning(v) for v in value]
        return aliases.get(value, value) if isinstance(value, str) else value

    for dim in DIMENSIONS:
        old = {_key(r): r for r in before.get(dim, []) if isinstance(r, dict) and _key(r)}
        new = {_key(r): r for r in after.get(dim, []) if isinstance(r, dict) and _key(r)}
        if aliases and after.get("schema") == "ases-consumer-context/2.0":
            old = {aliases.get(k, k): r for k, r in old.items()}
        added, removed = [], []
        for key in sorted(new.keys() - old.keys()):
            if modern and not profile_changed and _presence(before, new[key], dim, after):
                added.append(new[key])
            elif not modern and before.get("schema") == after.get("schema"):
                added.append(new[key])
            else:
                uncertainty.append({"dimension": dim, "id": key, "presence": "only_after", "reason": "prior scope/profile insufficient"})
        for key in sorted(old.keys() - new.keys()):
            if modern and not profile_changed and _presence(after, old[key], dim, before):
                removed.append(old[key])
            elif not modern and before.get("schema") == after.get("schema"):
                removed.append(old[key])
            else:
                uncertainty.append({"dimension": dim, "id": key, "presence": "only_before", "reason": "current scope/profile insufficient"})
        changed = [{"before": old[k], "after": new[k]} for k in sorted(old.keys() & new.keys())
                   if _meaning(remap_meaning(old[k])) != _meaning(new[k])]
        if added or removed or changed:
            dimensions[dim] = {"added": added, "removed": removed, "changed": changed}
        totals["added"] += len(added)
        totals["removed"] += len(removed)
        totals["changed"] += len(changed)
    return {"schema": "ases-semantic-diff/2.0" if modern or before.get("schema") != after.get("schema") else "ases-semantic-diff/1.0",
            "before_fingerprint": before.get("project_fingerprint"), "after_fingerprint": after.get("project_fingerprint"),
            "summary": totals, "dimensions": dimensions, "uncertain": uncertainty,
            "identity_remappings": remappings, "identity_candidates": remap_candidates,
            "analysis_profile_changed": profile_changed,
            "absence_authority": "scoped-static" if modern else "unverified-legacy",
            "evidence_changed": before.get("observations") != after.get("observations"),
            "interpretation": "Inventory changes only; legacy presence deltas do not prove absence or resolution."}
