from pathlib import Path
from ases.pipeline import scan_project

def test_manifest_is_stable_for_same_sources(tmp_path):
    fixture=Path(__file__).parent/"fixture_python"
    a=scan_project(fixture,tmp_path/"a")["manifest"]["project_fingerprint"]
    b=scan_project(fixture,tmp_path/"b")["manifest"]["project_fingerprint"]
    assert a==b
