from __future__ import annotations

import json
from pathlib import Path
from .evidence import location


def load_findings(path: Path) -> dict:
    if path.is_dir():
        path = path / "scanner-findings.json"
    return json.loads(path.read_text(encoding="utf-8"))


def diff_findings(before: dict, after: dict) -> dict:
    def keyed(payload):
        rows = payload.get("findings", []) + payload.get("hints", []) + payload.get("suppressed", [])
        return {r.get("fingerprint") or r.get("id"): r for r in rows}

    old, new = keyed(before), keyed(after)
    added_keys = sorted(new.keys() - old.keys())
    removed_keys = sorted(old.keys() - new.keys())
    unknown_keys = []
    modern = bool(before.get("analysis_profile") or after.get("analysis_profile"))
    if before.get("analysis_profile") != after.get("analysis_profile"):
        unknown_keys, removed_keys = removed_keys, []
    else:
        from .evidence import location
        confirmed = []
        for key in removed_keys:
            paths = {location(str(e))["path"] for e in old[key].get("evidence", [])}
            rule = old[key].get("rule_id")
            if not modern or paths and all(after.get("finding_coverage", {}).get(rule, {}).get(path, {}).get("status") == "ANALYZED" for path in paths):
                confirmed.append(key)
            else:
                unknown_keys.append(key)
        removed_keys = confirmed
    common = old.keys() & new.keys()
    changed = sorted(k for k in common if _meaning(old[k]) != _meaning(new[k]))
    unchanged = sorted(common - set(changed))
    return {
        "schema": "ases-finding-diff/2.0" if modern else "ases-finding-diff/1.0",
        "summary": {
            "new": len(added_keys), "resolved": len(removed_keys),
            "changed": len(changed), "unchanged": len(unchanged),
        },
        "new": [new[k] for k in added_keys],
        "resolved": [old[k] for k in removed_keys],
        "changed": [{"before": old[k], "after": new[k]} for k in changed],
        "unchanged": [new[k] for k in unchanged],
        "unknown": [{"before": old[k], "reason": "not observed in comparable complete source scope"} for k in unknown_keys],
        "unknown_count": len(unknown_keys),
        "resolution_authority": "supported-static-scope-only" if modern else "unverified-legacy",
    }


def _meaning(row: dict) -> tuple:
    normalized_evidence=tuple(sorted(location(str(x))["path"] for x in row.get("evidence", [])))
    return (
        row.get("status"), row.get("confidence"), row.get("message"),
        tuple(row.get("counter_evidence", [])), normalized_evidence,
    )
