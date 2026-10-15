from __future__ import annotations
import hashlib, json

def build_manifest(inventory: dict, model: dict, graph: dict) -> dict:
    stable={
        "analysis_profile": inventory.get("parser_profile", {}),
        "exclusions": inventory.get("exclusions", []),
        "sources":inventory.get("source_manifest",[]),
        "counts":{
            "nodes":len(graph.get("nodes",[])),
            "edges":len(graph.get("edges",[])),
            "behaviors":len(model.get("behaviors",[])),
            "components":len(model.get("components",[])),
            "tests":len(model.get("tests",[])),
            "controls":len(model.get("controls",[])),
        }
    }
    if model.get("site_observations"):
        stable["site_observations"] = model["site_observations"]
    raw=json.dumps(stable,sort_keys=True,separators=(",",":")).encode()
    return {
        "ases_version":model.get("ases_version"),
        "project_fingerprint":hashlib.sha256(raw).hexdigest(),
        **stable,
    }
