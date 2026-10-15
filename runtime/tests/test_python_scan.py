from pathlib import Path
from ases.pipeline import scan_project

def test_python_fixture(tmp_path):
    fixture = Path(__file__).parent / "fixture_python"
    result = scan_project(fixture, tmp_path/"out")
    model = result["semantic_model"]
    assert "Python" in model["project"]["languages"]
    assert any(b["name"] == "GET /users" for b in model["behaviors"])
    assert any(c.get("control_type") == "authentication" for c in model.get("controls",[]))
    assert any(a["name"] == "User" for a in model["assets"])
    assert len(model["tests"]) >= 1
