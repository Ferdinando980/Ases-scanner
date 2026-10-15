import json
from pathlib import Path
import pytest
import jsonschema
from ases.cli import main
from ases.pipeline import scan_project
from ases.semantic_diff import load_context, semantic_diff
from ases.artifacts import inspect_artifact, _seal
from ases.evidence import seal_context, validate_context
from ases.diffing import diff_findings

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"


def test_schema_and_cli_snapshot_roundtrip(tmp_path, capsys):
    root = tmp_path / "app"
    root.mkdir()
    (root / "server.mjs").write_text("function handler() { return 1; } app.get('/x', handler);")
    out = tmp_path / "scan.ases"
    scan_project(root, out)
    context = load_context(out)
    jsonschema.validate(context, json.loads((SCHEMAS / "consumer-context-v2.schema.json").read_text()))
    target = tmp_path / "public.json"
    assert main(["export", str(out), "--schema", "2.0", "--out", str(target)]) == 0
    capsys.readouterr()
    assert load_context(target)["snapshot_id"] == context["snapshot_id"]
    assert main(["inspect", str(out), "--collection", "entities", "--limit", "1"]) == 0
    assert json.loads(capsys.readouterr().out)["pagination"]["total"] > 1
    assert main(["trace", str(out), "GET /x"]) == 0
    assert json.loads(capsys.readouterr().out)["selection"] == "exact"
    artifact_out = tmp_path / "artifact.ases"
    assert main(["scan-artifact", str(root), "--out", str(artifact_out)]) == 0
    capsys.readouterr()
    jsonschema.validate(inspect_artifact(root), json.loads((SCHEMAS / "artifact-snapshot.schema.json").read_text()))
    assert main(["reconcile-artifact", str(out), str(artifact_out / "artifact-snapshot.json")]) == 0
    reconciliation = json.loads(capsys.readouterr().out)
    assert reconciliation["source_matches"][0]["status"] == "matched"
    jsonschema.validate(reconciliation, json.loads((SCHEMAS / "artifact-reconciliation.schema.json").read_text()))
    jsonschema.validate(semantic_diff(context, context), json.loads((SCHEMAS / "semantic-diff-v2.schema.json").read_text()))
    feed = json.loads((out / "scanner-findings.json").read_text())
    jsonschema.validate(diff_findings(feed, feed), json.loads((SCHEMAS / "finding-diff-v2.schema.json").read_text()))


def test_resealed_invalid_reference_or_location_is_rejected(tmp_path):
    (tmp_path / "a.mjs").write_text("function f() {}")
    out = tmp_path.parent / (tmp_path.name + ".ases")
    scan_project(tmp_path, out)
    context = load_context(out)
    context["observations"][0]["locations"][0]["line"] = "bad"
    seal_context(context)
    with pytest.raises(ValueError, match="location"):
        validate_context(context)


def test_move_is_an_inferred_remapping_and_duplicates_remain_candidates(tmp_path):
    source = tmp_path / "a.mjs"
    source.write_text("export function read() { return 1; }")
    first = tmp_path.parent / (tmp_path.name + "-before.ases")
    second = tmp_path.parent / (tmp_path.name + "-after.ases")
    scan_project(tmp_path, first)
    source.rename(tmp_path / "b.mjs")
    scan_project(tmp_path, second)
    report = semantic_diff(load_context(first), load_context(second))
    assert report["identity_remappings"][0]["state"] == "INFERRED"
    (tmp_path / "c.mjs").write_text("export function read() { return 1; }")
    scan_project(tmp_path, second)
    assert semantic_diff(load_context(first), load_context(second))["identity_candidates"]
