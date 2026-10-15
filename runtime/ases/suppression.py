from __future__ import annotations
from pathlib import Path


def load_suppressions(root: Path) -> dict[str, str]:
    path = root / ".asesignore"
    if not path.exists():
        return {}
    out = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rule, sep, reason = line.partition("|")
        out[rule.strip()] = reason.strip() if sep else "Explicitly suppressed in .asesignore"
    return out


def apply_suppressions(items: list[dict], suppressions: dict[str, str]) -> list[dict]:
    for item in items:
        reason = suppressions.get(item.get("rule_id"))
        if not reason:
            continue
        item["original_status"] = item.get("status")
        item["status"] = "SUPPRESSED"
        item.setdefault("counter_evidence", []).append(f"Suppressed by project policy: {reason}")
        item["suppression_reason"] = reason
    return items
