from pathlib import Path
from ases.pipeline import scan_project

def test_asesignore(tmp_path):
    root=tmp_path/"repo"; root.mkdir()
    (root/".asesignore").write_text("ignored.py\n",encoding="utf-8")
    (root/"kept.py").write_text("def kept(): pass\n",encoding="utf-8")
    (root/"ignored.py").write_text("def ignored(): pass\n",encoding="utf-8")
    result=scan_project(root,tmp_path/"out")
    paths={n.get("path") for n in result["graph"]["nodes"]}
    assert "kept.py" in paths
    assert "ignored.py" not in paths
