from pathlib import Path
import shutil
from ases.pipeline import scan_project
from ases.audit import audit_project

def test_drift_audit(tmp_path):
    fixture = Path(__file__).parent / "fixture_python"
    work = tmp_path/"repo"
    shutil.copytree(fixture, work)
    scan_project(work)  # creates baseline
    report = audit_project(work)
    assert report["status"] == "PASS"
    with (work/"app"/"api.py").open("a", encoding="utf-8") as f:
        f.write('\n@app.post("/users")\ndef create_user():\n    return {}\n')
    report2 = audit_project(work)
    assert report2["status"] == "DRIFT"
    assert "behaviors" in report2["drift"]
