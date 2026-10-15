from pathlib import Path
from ases.pipeline import scan_project

def test_java_call_flow_recovered(tmp_path):
    fixture=Path(__file__).parent/"fixture_spring"
    result=scan_project(fixture,tmp_path/"out")
    edges=result["graph"]["edges"]
    assert any(e["relation"]=="calls_dependency" for e in edges)
    behavior=result["semantic_model"]["behaviors"][0]
    assert len(behavior["main_flow"]) >= 2

def test_typescript_call_flow_recovered(tmp_path):
    fixture=Path(__file__).parent/"fixture_typescript"
    result=scan_project(fixture,tmp_path/"out")
    assert any(e["relation"]=="calls_dependency" for e in result["graph"]["edges"])
