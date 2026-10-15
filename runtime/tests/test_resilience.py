from ases.pipeline import scan_project

def test_malformed_python_does_not_crash(tmp_path):
    root=tmp_path/"repo"; root.mkdir()
    (root/"bad.py").write_text("def broken(:\n",encoding="utf-8")
    result=scan_project(root,tmp_path/"out")
    assert result["validation"]["status"]=="PASS"
