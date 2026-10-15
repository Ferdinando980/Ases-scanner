from pathlib import Path
import subprocess
from ases.repo_source import resolve_source
from ases.pipeline import scan_project

def test_url_scan_pipeline(tmp_path):
    src = tmp_path/"remote"
    src.mkdir()
    subprocess.run(["git","init"], cwd=src, check=True, capture_output=True)
    subprocess.run(["git","config","user.email","ases@example.test"], cwd=src, check=True)
    subprocess.run(["git","config","user.name","ASES Test"], cwd=src, check=True)
    (src/"app.py").write_text(
        "from fastapi import FastAPI\napp=FastAPI()\n@app.get('/health')\ndef health(): return {'ok': True}\n",
        encoding="utf-8"
    )
    subprocess.run(["git","add","."], cwd=src, check=True)
    subprocess.run(["git","commit","-m","fixture"], cwd=src, check=True, capture_output=True)

    resolved = resolve_source(src.as_uri())
    try:
        out = tmp_path/"result"
        result = scan_project(resolved.root, out, source_uri=resolved.display_source)
        assert result["validation"]["status"] == "PASS"
        assert result["semantic_model"]["project"]["source_uri"].startswith("file://")
        assert any(b["name"] == "GET /health" for b in result["semantic_model"]["behaviors"])
    finally:
        resolved.cleanup()
