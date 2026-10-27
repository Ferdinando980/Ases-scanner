from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import yaml, json

def load_model(path: Path) -> dict:
    if path.is_dir():
        path = path / "semantic-model.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))

def generic_context(model: dict, manifest: dict | None = None) -> dict:
    # v1.5 is additive over v1.4 (which was additive over v1.3): every older key keeps its old
    # shape, nothing removed or renamed. A consumer that only knows an older version can keep
    # reading this and ignore the new keys. `manifest` is optional because `ases export` can
    # run standalone on a semantic-model.yaml with no manifest.json alongside it (see cli.py);
    # project_fingerprint is then omitted rather than guessed.
    context = {
        "schema":"ases-consumer-context/1.5",
        "ases_version":model.get("ases_version"),
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "project_fingerprint":(manifest or {}).get("project_fingerprint"),
        "project":model.get("project",{}),
        "actors":model.get("actors",[]),
        "behaviors":model.get("behaviors",[]),
        "components":model.get("components",[]),
        "interfaces":model.get("interfaces",[]),
        "data_stores":model.get("data_stores",[]),
        "external_systems":model.get("external_systems",[]),
        "assets":model.get("assets",[]),
        "frontend":model.get("frontend",{}),
        "trust_boundaries":model.get("trust_boundaries",[]),
        "sensitive_paths":model.get("sensitive_paths",[]),
        "controls":model.get("controls",[]),
        "sessions":model.get("sessions",[]),
        "documentation_artifacts":model.get("documentation_artifacts",[]),
        "source_classification":model.get("source_classification",{}),
        "pattern_findings":model.get("pattern_findings",[]),
        "conformance_findings":model.get("conformance_findings",[]),
        "frontend_findings":model.get("frontend_findings",[]),
        "cross_boundary_findings":model.get("cross_boundary_findings",[]),
        "architecture_patterns":model.get("architecture_patterns",[]),
        "pattern_candidates":model.get("pattern_candidates",[]),
        "pattern_opportunities":model.get("pattern_opportunities",[]),
        "pattern_hints":model.get("pattern_hints",[]),
        "semantic_quality":model.get("semantic_quality",{}),
        "claim_states":model.get("claim_states",[]),
        "claims":model.get("claims",[]),
        "assumptions":model.get("assumptions",[]),
        "tests":model.get("tests",[]),
        "trace_links":model.get("trace_links",[]),
        "conflicts":model.get("conflicts",[]),
        "unknowns":model.get("unknowns",[]),
    }
    if model.get("site_observations") is not None:
        context["site_observations"] = model["site_observations"]
    if "design_review_coverage" in model:
        context["design_review_coverage"] = model["design_review_coverage"]
    return context

def export_json(model_path: Path, out: Path, manifest: dict | None = None, schema: str = "1.5", *, max_snapshot_bytes=64 * 1024 * 1024):
    if schema == "2.0":
        from .semantic_diff import load_context
        snapshot_path = model_path if model_path.is_dir() or model_path.suffix == ".json" else model_path.parent
        data = load_context(snapshot_path, max_bytes=max_snapshot_bytes)
        if data["schema"] != "ases-consumer-context/2.0":
            raise ValueError("Public v2 export requires an existing v2 snapshot; source is never reread implicitly")
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    if schema != "1.5":
        raise ValueError("Unsupported export schema")
    data = generic_context(load_model(model_path), manifest)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data
