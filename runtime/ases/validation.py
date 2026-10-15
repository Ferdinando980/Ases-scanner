from __future__ import annotations
from pathlib import Path
import json

ALLOWED_STATES={"CONFIRMED","OBSERVED","INFERRED","UNKNOWN","CONFLICTING"}
SECTIONS = ("actors", "behaviors", "components", "interfaces", "assets", "trust_boundaries", "tests", "controls")

def _items(model: dict):
    for section in SECTIONS:
        for item in model.get(section, []):
            yield section, item

def validate_model(model: dict, schema_path: Path | None = None) -> dict:
    errors=[]
    warnings=[]

    if schema_path and schema_path.exists():
        try:
            import jsonschema
            schema=json.loads(schema_path.read_text(encoding="utf-8"))
            jsonschema.validate(model,schema)
        except Exception as e:
            errors.append(f"schema: {e}")

    for section, item in _items(model):
        p=item.get("provenance",{})
        state=p.get("state")
        if state not in ALLOWED_STATES:
            errors.append(f"{section}:{item.get('id')}: invalid provenance state {state}")
        if state in {"OBSERVED","INFERRED","CONFIRMED"} and not p.get("evidence"):
            warnings.append(f"{section}:{item.get('id')}: evidence missing")

    ids=set()
    for _, item in _items(model):
        iid=item.get("id")
        if iid in ids:
            errors.append(f"duplicate id: {iid}")
        ids.add(iid)

    return {"status":"PASS" if not errors else "FAIL","errors":errors,"warnings":warnings}
