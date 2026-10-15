from pathlib import Path
import subprocess
from ases.repo_source import repo_name_from_url, resolve_source

def test_repo_name_from_url():
    assert repo_name_from_url("https://github.com/LimeMoss/Progetto-JustInTime") == "Progetto-JustInTime"
    assert repo_name_from_url("https://github.com/LimeMoss/Progetto-JustInTime.git") == "Progetto-JustInTime"
    assert repo_name_from_url("git@github.com:LimeMoss/Progetto-JustInTime.git") == "Progetto-JustInTime"

def test_file_url_clone(tmp_path):
    src = tmp_path/"source"
    src.mkdir()
    subprocess.run(["git","init"], cwd=src, check=True, capture_output=True)
    subprocess.run(["git","config","user.email","ases@example.test"], cwd=src, check=True)
    subprocess.run(["git","config","user.name","ASES Test"], cwd=src, check=True)
    (src/"hello.py").write_text("def hello(): return 'hi'\n", encoding="utf-8")
    subprocess.run(["git","add","."], cwd=src, check=True)
    subprocess.run(["git","commit","-m","fixture"], cwd=src, check=True, capture_output=True)

    resolved = resolve_source(src.as_uri())
    try:
        assert resolved.is_remote is True
        assert (resolved.root/"hello.py").exists()
    finally:
        resolved.cleanup()
