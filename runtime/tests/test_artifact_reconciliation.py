import json
from hashlib import sha256
import pytest
from ases.pipeline import scan_project
from ases.semantic_diff import load_context
from ases.artifacts import inspect_artifact, write_artifact, load_artifact, load_runtime, reconcile_artifact


def setup(tmp_path):
    root, bundle = tmp_path / "app", tmp_path / "dist"
    root.mkdir()
    bundle.mkdir()
    source = "export function read() { return 1; }"
    (root / "server.mjs").write_text(source)
    out = tmp_path / "source.ases"
    scan_project(root, out)
    (bundle / "app.js").write_text("throw new Error('never execute');")
    (bundle / "app.js.map").write_text(json.dumps({"version": 3, "file": "app.js", "sources": ["server.mjs"], "sourcesContent": [source]}))
    return load_context(out), bundle


def test_source_map_match_is_inferred_without_execution_or_source_reads(tmp_path):
    source, bundle = setup(tmp_path)
    (bundle / "app.js").write_text("const sdk = require('sdk'); fetch('https://user:secret@example.test/users?token=secret'); throw new Error('never execute');")
    artifact = write_artifact(bundle, tmp_path / "artifact.ases")
    loaded = load_artifact(tmp_path / "artifact.ases" / "artifact-snapshot.json")
    assert artifact == loaded
    report = reconcile_artifact(source, artifact)
    assert report["source_matches"][0]["basis"] == "source-map-content"
    assert report["source_matches"][0]["state"] == "INFERRED"
    assert all(row["source_role"] == "BUILD_ARTIFACT" for row in artifact["files"])
    assert "sourcesContent" not in json.dumps(artifact)
    script = next(row for row in artifact["files"] if row["path"] == "app.js")
    assert script["imports"] == ["sdk"]
    assert script["literal_requests"][0]["endpoint"] == "https://example.test/users"
    assert "secret" not in json.dumps(artifact)


def test_runtime_digest_mismatch_and_partial_capture_stay_visible(tmp_path):
    source, bundle = setup(tmp_path)
    artifact = inspect_artifact(bundle)
    runtime = {"schema": "ases-runtime-observations/1.0", "collector": {"name": "fixture", "version": "1"},
               "environment": {"name": "local-fixture"}, "captured_at": "2026-10-13T12:00:00Z",
               "coverage": {"status": "PARTIAL"},
               "scripts": [{"location": "https://example.test/assets/app.js", "sha256": "0" * 64, "loaded": True}]}
    path = tmp_path / "runtime.json"
    path.write_text(json.dumps(runtime))
    observations = load_runtime(path)
    report = reconcile_artifact(source, artifact, observations, [{"runtime_prefix": "https://example.test/assets/", "artifact_prefix": ""}])
    assert report["runtime_matches"][0]["status"] == "mismatch"
    assert report["runtime_matches"][0]["load_state"] == "unknown"
    assert report["coverage"]["runtime"]["status"] == "PARTIAL"
    observations["scripts"][0]["sha256"] = sha256((bundle / "app.js").read_bytes()).hexdigest()
    assert reconcile_artifact(source, artifact, observations)["runtime_matches"][0]["load_state"] == "loaded"


def test_duplicate_exact_bytes_are_ambiguous_and_missing_map_is_unknown(tmp_path):
    source, bundle = setup(tmp_path)
    data = (tmp_path / "app" / "server.mjs").read_bytes()
    (bundle / "one.js").write_bytes(data)
    (bundle / "two.js").write_bytes(data)
    report = reconcile_artifact(source, inspect_artifact(bundle))
    assert report["source_matches"][0]["status"] == "ambiguous"
    no_maps = tmp_path / "without-map"
    no_maps.mkdir()
    (no_maps / "app.js").write_text("unrelated();")
    assert reconcile_artifact(source, inspect_artifact(no_maps))["source_matches"][0]["status"] == "unknown"


def test_malformed_runtime_or_artifact_is_rejected(tmp_path):
    runtime = tmp_path / "runtime.json"
    runtime.write_text('{"schema":"unsupported"}')
    with pytest.raises(ValueError, match="Unsupported"):
        load_runtime(runtime)
    source, bundle = setup(tmp_path)
    artifact = inspect_artifact(bundle)
    artifact["files"][0]["sha256"] = "0" * 64
    target = tmp_path / "artifact.json"
    target.write_text(json.dumps(artifact))
    with pytest.raises(ValueError, match="digest"):
        load_artifact(target)


def test_map_ambiguity_and_asserted_content_mismatch(tmp_path):
    source, bundle = setup(tmp_path)
    (bundle / "copy.map").write_bytes((bundle / "app.js.map").read_bytes())
    assert reconcile_artifact(source, inspect_artifact(bundle))["source_matches"][0]["status"] == "ambiguous"
    content = json.loads((bundle / "app.js.map").read_text())
    content["sourcesContent"] = ["different bytes"]
    for name in ("copy.map", "app.js.map"):
        (bundle / name).write_text(json.dumps(content))
    report = reconcile_artifact(source, inspect_artifact(bundle))
    assert report["source_matches"][0]["status"] == "mismatch"
    assert report["source_matches"][0]["source_map_contradictions"]


def test_artifact_limit_and_resealed_malformed_map_are_explicit(tmp_path, monkeypatch):
    from ases import artifacts
    source, bundle = setup(tmp_path)
    artifact = inspect_artifact(bundle)
    artifact["source_maps"][0]["content_sha256"] = 1
    artifacts._seal(artifact)
    with pytest.raises(ValueError, match="source map digest"):
        reconcile_artifact(source, artifact)
    monkeypatch.setattr(artifacts, "MAX_BYTES", 8)
    bounded = inspect_artifact(bundle)
    assert bounded["coverage"]["status"] == "PARTIAL" and bounded["coverage"]["omitted_count"] is None
    assert any(row["reason"] == "artifact_byte_limit" for row in bounded["unknowns"])
