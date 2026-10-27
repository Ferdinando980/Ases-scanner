from __future__ import annotations
from pathlib import Path
import tempfile, yaml, json
from .pipeline import scan_project, default_output

def _ids(model, section):
    return {x["id"] for x in model.get(section,[]) if "id" in x}

def audit_project(root: Path, *, scan_options: dict | None = None) -> dict:
    root=root.resolve()
    base=default_output(root)
    model_path=base/"semantic-model.yaml"
    manifest_path=base/"manifest.json"
    baseline=yaml.safe_load(model_path.read_text(encoding="utf-8")) if model_path.exists() else None
    old_manifest=json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None

    with tempfile.TemporaryDirectory(prefix="ases-audit-") as td:
        fresh_result=scan_project(root,Path(td), **(scan_options or {}))
        fresh=fresh_result["semantic_model"]
        new_manifest=fresh_result["manifest"]

    if baseline is None:
        return {"baseline_present":False,"status":"NO_BASELINE","drift":{},"source_fingerprint_changed":None}

    sections=("components","behaviors","tests","assets","controls","interfaces","trust_boundaries")
    drift={}
    for section in sections:
        old=_ids(baseline,section); new=_ids(fresh,section)
        added=sorted(new-old); removed=sorted(old-new)
        if added or removed:
            drift[section]={"added":added,"removed":removed}

    source_changed = None if old_manifest is None else old_manifest.get("project_fingerprint") != new_manifest.get("project_fingerprint")
    status="DRIFT" if drift or source_changed else "PASS"
    return {
        "baseline_present":True,
        "status":status,
        "source_fingerprint_changed":source_changed,
        "drift":drift,
        "conflicts":fresh.get("conflicts",[]),
        "unknowns":fresh.get("unknowns",[]),
    }
