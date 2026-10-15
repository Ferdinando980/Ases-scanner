from pathlib import Path
from ases.pipeline import scan_project

def test_validation_passes(tmp_path):
    fixture=Path(__file__).parent/"fixture_python"
    result=scan_project(fixture,tmp_path/"out")
    assert result["validation"]["status"]=="PASS"
    assert (tmp_path/"out"/"manifest.json").exists()
    assert (tmp_path/"out"/"validation.json").exists()
