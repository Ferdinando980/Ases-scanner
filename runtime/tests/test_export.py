import json
from pathlib import Path
from ases.pipeline import scan_project
from ases.export import export_json

def test_export(tmp_path):
    fixture = Path(__file__).parent / "fixture_python"
    out = tmp_path/"scan"
    scan_project(fixture, out)
    target = tmp_path/"consumer.json"
    data = export_json(out, target)
    assert data["schema"] == "ases-consumer-context/1.5"
    assert target.exists()
    assert "behaviors" in data and "controls" in data
    assert "data_stores" in data
    assert "external_systems" in data
    assert data["ases_version"]
    assert data["generated_at"]

def test_export_forwards_manifest_fingerprint(tmp_path):
    fixture = Path(__file__).parent / "fixture_python"
    out = tmp_path/"scan2"
    scan_project(fixture, out)
    manifest = json.loads((out/"manifest.json").read_text())
    target = tmp_path/"consumer2.json"
    data = export_json(out, target, manifest)
    assert data["project_fingerprint"] == manifest["project_fingerprint"]

def test_export_without_manifest_omits_fingerprint(tmp_path):
    fixture = Path(__file__).parent / "fixture_python"
    out = tmp_path/"scan3"
    scan_project(fixture, out)
    target = tmp_path/"consumer3.json"
    data = export_json(out, target)
    assert data["project_fingerprint"] is None
