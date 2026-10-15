from pathlib import Path
from ases.pipeline import scan_project

def test_typescript_fixture(tmp_path):
    fixture = Path(__file__).parent / "fixture_typescript"
    result = scan_project(fixture, tmp_path / "out")
    model = result["semantic_model"]

    assert "TypeScript" in model["project"]["languages"]
    assert any("NestJS" in x for x in model["project"]["frameworks"])
    assert any(b["name"] == "GET /users" for b in model["behaviors"])
    assert any(b["name"] == "POST /users" for b in model["behaviors"])
    assert any(b["name"] == "GET /health" for b in model["behaviors"])
    assert len(model["tests"]) >= 2
    assert any(a["name"] == "user" for a in model["assets"])
    assert len(model["trust_boundaries"]) >= 1
    assert (tmp_path / "out" / "docs" / "RAD.md").exists()
