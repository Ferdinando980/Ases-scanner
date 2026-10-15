import pytest
from ases.pipeline import scan_project
from ases.semantic_diff import load_context
from ases.snapshot import inspect_snapshot, trace_snapshot


def test_queries_are_deterministic_and_do_not_reread_source(tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    path = root / "server.mjs"
    path.write_text("function store() { return 1; } function handler() { return store(); } app.get('/users', handler);")
    out = tmp_path / "scan.ases"
    scan_project(root, out)
    context = load_context(out)
    first = trace_snapshot(context, "GET /users")
    assert first["selection"] == "exact"
    assert {r["name"] for r in first["entities"]} >= {"handler", "store"}
    path.write_text("throw new Error('should not be inspected or executed');")
    assert trace_snapshot(load_context(out), "GET /users") == first
    page = inspect_snapshot(context, collection="entities", limit=1)
    assert page["pagination"]["next_offset"] == 1
    assert page["parent_snapshot_id"] == first["parent_snapshot_id"]
    backward = trace_snapshot(context, "store", direction="backward")
    assert {r["name"] for r in backward["entities"]} >= {"handler", "GET /users"}
    limited = trace_snapshot(context, "GET /users", max_nodes=1)
    assert limited["coverage"]["truncated"] is True


def test_ambiguous_selector_never_selects_an_arbitrary_function(tmp_path):
    for name in ("a.mjs", "b.mjs"):
        (tmp_path / name).write_text("function read() {}")
    out = tmp_path.parent / (tmp_path.name + ".ases")
    scan_project(tmp_path, out)
    result = trace_snapshot(load_context(out), "read")
    assert result["selection"] == "ambiguous"
    assert len(result["seed_ids"]) == 2
    assert result["entities"] == []
    with pytest.raises(ValueError):
        inspect_snapshot(load_context(out), limit=0)
