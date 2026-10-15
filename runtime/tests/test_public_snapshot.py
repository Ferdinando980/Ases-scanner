import json
from pathlib import Path
import pytest
from ases.evidence import validate_context
from ases.pipeline import scan_project
from ases.semantic_diff import semantic_diff, load_context
from ases.model import FactGraph, Node, Edge
from ases.recovery.paths import recover_sensitive_paths


def snapshot(root, out):
    scan_project(root, out)
    return load_context(out)


def test_public_identity_survives_line_moves_and_legacy_is_preserved(tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    source = root / "server.py"
    source.write_text('@app.get("/users")\ndef users():\n    return []\n')
    before = snapshot(root, tmp_path / "before")
    source.write_text('\n\n# harmless position change\n' + source.read_text())
    after = snapshot(root, tmp_path / "after")
    assert [x["id"] for x in before["entities"]] == [x["id"] for x in after["entities"]]
    assert semantic_diff(before, after)["summary"]["changed"] == 0
    assert before["snapshot_id"] != after["snapshot_id"]
    assert before["observations"] != after["observations"]
    legacy = json.loads((tmp_path / "after" / "consumer-context.json").read_text())
    assert legacy["schema"] == "ases-consumer-context/1.5"
    validate_context(after)
    after["entities"][0]["name"] = "tampered"
    with pytest.raises(ValueError, match="digest"):
        validate_context(after)


def test_diff_preserves_url_ports_and_qualifies_absence():
    old = {"schema": "ases-consumer-context/2.0", "analysis_profile": {},
           "coverage": {"files": {"server.ts": {"status": "ANALYZED"}}},
           "entities": [{"id": "client", "path": "server.ts", "endpoint": "http://localhost:8080"}]}
    new = {**old, "entities": [{**old["entities"][0], "endpoint": "http://localhost:9090"}]}
    assert semantic_diff(old, new)["summary"]["changed"] == 1
    partial = {**old, "entities": [], "coverage": {"files": {"server.ts": {"status": "PARTIAL"}}}}
    assert semantic_diff(old, partial)["summary"]["removed"] == 0
    assert semantic_diff(old, partial)["uncertain"][0]["presence"] == "only_before"
    complete = {**old, "entities": []}
    assert semantic_diff(old, complete)["summary"]["removed"] == 1


def test_path_depth_limit_preserves_explicit_partial_coverage():
    graph = FactGraph(nodes=[Node("route", "route", "route", metadata={"handler": "f0"})] +
                      [Node(f"f{i}", "function", f"f{i}") for i in range(12)] +
                      [Node("store", "repository", "store")],
                      edges=[Edge("route", "f0", "handled_by")] +
                      [Edge(f"f{i}", f"f{i+1}", "calls") for i in range(11)] +
                      [Edge("f11", "store", "calls")])
    coverage = []
    assert recover_sensitive_paths(graph, coverage) == []
    assert coverage[0]["status"] == "PARTIAL"
    assert coverage[0]["omitted_count"] is None
    assert coverage[0]["residual_unknowns"][0]["reason"] == "depth_limit"


def test_unknown_future_snapshot_schema_is_rejected(tmp_path):
    path = tmp_path / "consumer.json"
    path.write_text('{"schema":"ases-consumer-context/99.0"}')
    with pytest.raises(ValueError, match="Unsupported"):
        load_context(path)


def test_nonexistent_source_never_generates_a_phantom_success(tmp_path):
    with pytest.raises(ValueError, match="existing directory"):
        scan_project(tmp_path / "missing", tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_duplicate_call_sites_preserve_all_evidence():
    graph = FactGraph()
    graph.add_edge(Edge("handler", "store", "calls", ["server.ts:1"]))
    graph.add_edge(Edge("handler", "store", "calls", ["server.ts:9"]))
    assert len(graph.edges) == 1
    assert graph.edges[0].evidence == ["server.ts:1", "server.ts:9"]


def test_behavior_flow_does_not_traverse_architectural_dependencies():
    from ases.recovery.semantic import _flow_for_route
    route = Node("route", "route", "GET /login", metadata={"handler": "login"})
    graph = FactGraph(nodes=[route, Node("login", "function", "login"), Node("store", "repository", "store")],
                      edges=[Edge("login", "store", "depends_on")])
    scope = {}
    assert _flow_for_route(route, graph, scope) == ["route", "login"]
    assert scope["basis"] == "bounded static calls, not architectural dependencies"


def test_frontend_template_bytes_are_part_of_provenance_and_freshness(tmp_path):
    from hashlib import sha256
    (tmp_path / 'client').mkdir()
    page = tmp_path / 'client/page.html'
    page.write_text('<p>First version</p>')
    before = snapshot(tmp_path, tmp_path.parent / (tmp_path.name + '-before.ases'))
    source = next(row for row in before['source_manifest'] if row['path'] == 'client/page.html')
    assert source['sha256'] == sha256(page.read_bytes()).hexdigest()
    template = next(row for row in before['entities'] if row['kind'] == 'frontend_template')
    observation = next(row for row in before['observations'] if row['id'] in template['observation_refs'])
    assert observation['source_hashes']['client/page.html'] == source['sha256']
    page.write_text('<p>Second version</p>')
    after = snapshot(tmp_path, tmp_path.parent / (tmp_path.name + '-after.ases'))
    assert before['project_fingerprint'] != after['project_fingerprint']


def test_frontend_and_controls_respect_the_parser_byte_limit(tmp_path, monkeypatch):
    from ases.scanners import javascript
    monkeypatch.setattr(javascript, 'MAX_BYTES', 20)
    (tmp_path / 'client').mkdir()
    (tmp_path / 'client/api.js').write_text("export function request() { validateUser(); return fetch('/users'); }")
    context = snapshot(tmp_path, tmp_path.parent / (tmp_path.name + '.ases'))
    assert context['coverage']['files']['client/api.js']['status'] == 'UNKNOWN'
    assert not any(row.get('path') == 'client/api.js' for row in context['entities'])
    assert context['analysis_profile']['parser']['limits']['source_bytes'] == 20


def test_malformed_legacy_collection_has_an_explicit_diagnostic(tmp_path):
    path = tmp_path / 'legacy.json'
    path.write_text(json.dumps({'schema': 'ases-consumer-context/1.5', 'components': None}))
    with pytest.raises(ValueError, match='collection'):
        load_context(path)


def test_resealed_invalid_entity_path_is_rejected_before_queries(tmp_path):
    from ases.evidence import seal_context
    (tmp_path / 'a.mjs').write_text('function read() {}')
    context = snapshot(tmp_path, tmp_path.parent / (tmp_path.name + '.ases'))
    context['entities'][0]['path'] = {'unsafe': 'wrong type'}
    seal_context(context)
    with pytest.raises(ValueError, match='path'):
        validate_context(context)
