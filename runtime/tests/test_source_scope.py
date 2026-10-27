from ases.pipeline import scan_project
from ases.semantic_diff import load_context, semantic_diff


def write(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_named_python_environments_are_outside_source_scope(tmp_path):
    root = tmp_path / "project"
    write(root, "app.py", "def owned(): return 1\n")
    write(root, "tools/custom-runtime/pyvenv.cfg", "home = /python\n")
    write(root, "tools/custom-runtime/Lib/dependency.py", "def library_internals(): return 0\n")
    write(root, "other/site-packages/dependency.py", "def foreign_code(): return 0\n")
    result = scan_project(root, tmp_path / "first")
    assert [s["path"] for s in result["inventory"]["source_manifest"]] == ["app.py"]
    context = load_context(tmp_path / "first")
    excluded = {row["path"]: row["reason"] for row in context["source_scope"]["excluded_directories"]}
    assert excluded["tools/custom-runtime"] == "python-environment"
    assert excluded["other/site-packages"] == "default-directory"
    assert not any(e["name"] in {"library_internals", "foreign_code"} for e in context["entities"])


def test_catalog_is_fresh_and_scope_changes_do_not_prove_absence(tmp_path):
    root = tmp_path / "project"
    write(root, "app.py", "def owned(): return 1\n")
    write(root, "scratch/app.py", "def temporary_helper(): return 1\n")
    scan_project(root, tmp_path / "before")
    before = load_context(tmp_path / "before")
    assert any(e["name"] == "temporary_helper" for e in before["entities"])
    write(root, "new.py", "def newly_added(): return 2\n")
    scan_project(root, tmp_path / "after", exclude=("scratch/**",))
    after = load_context(tmp_path / "after")
    assert any(e["name"] == "newly_added" for e in after["entities"])
    assert not any(e["name"] == "temporary_helper" for e in after["entities"])
    assert after["source_scope"]["user_exclusions"] == ["scratch/**"]
    delta = semantic_diff(before, after)
    assert delta["analysis_profile_changed"]
    assert delta["uncertain"]
    assert not delta["summary"]["removed"]


def test_progress_reports_real_stages_in_order(tmp_path):
    root = tmp_path / "project"
    write(root, "app.py", "def read(): return 1\n")
    stages = []
    scan_project(root, tmp_path / "out", progress=stages.append)
    assert stages[0] == "inventory"
    assert stages.index("python") < stages.index("model") < stages.index("validation") < stages.index("documents")
    assert stages[-1] == "complete"


def test_snapshot_read_limit_is_explicit_and_validated(tmp_path):
    root = tmp_path / "project"
    write(root, "app.py", "def read(): return 1\n")
    scan_project(root, tmp_path / "out")
    path = tmp_path / "out" / "consumer-context.v2.json"
    import pytest
    with pytest.raises(ValueError, match="bounded"):
        load_context(path, max_bytes=path.stat().st_size - 1)
    assert load_context(path, max_bytes=path.stat().st_size)["schema"] == "ases-consumer-context/2.0"
