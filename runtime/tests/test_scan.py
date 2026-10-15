from pathlib import Path
from ases.pipeline import scan_project

def test_spring_fixture(tmp_path):
    fixture = Path(__file__).parent / "fixture_spring"
    result = scan_project(fixture, tmp_path / "out")
    model = result["semantic_model"]
    kinds = {c["kind"] for c in model["components"]}
    assert "controller" in kinds
    assert "service" in kinds
    assert "repository" in kinds
    assert any(b["trigger"].startswith("POST") for b in model["behaviors"])
    assert len(model["tests"]) >= 1
    assert (tmp_path / "out" / "docs" / "SYSTEM-OVERVIEW.md").exists()
    assert (tmp_path / "out" / "docs" / "RAD.md").exists()
    assert len(model["trust_boundaries"]) >= 1
