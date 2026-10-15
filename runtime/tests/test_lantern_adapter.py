"""Tests the reference adapter in integrations/lantern/adapter.py against a REAL ASES scan
(not a hand-written fixture): if the consumer-context contract drifts, this fails instead of
the adapter silently going stale, which is the whole point of calling it a "real starter kit"
instead of an untested example."""
import importlib.util
import sys
from pathlib import Path

from ases.pipeline import scan_project
from ases.export import export_json

ADAPTER_PATH = Path(__file__).resolve().parents[2] / "integrations" / "lantern" / "adapter.py"
spec = importlib.util.spec_from_file_location("lantern_adapter", ADAPTER_PATH)
adapter = importlib.util.module_from_spec(spec)
sys.modules["lantern_adapter"] = adapter
spec.loader.exec_module(adapter)


def _consumer_context(tmp_path):
    fixture = Path(__file__).parent / "fixture_python"
    out = tmp_path / "scan-out"
    scan_project(fixture, out)
    manifest = __import__("json").loads((out / "manifest.json").read_text())
    return export_json(out, tmp_path / "consumer-context.json", manifest)


def test_adapt_reads_a_real_consumer_context(tmp_path):
    ctx = _consumer_context(tmp_path)
    result = adapter.adapt(ctx)
    assert result["schema"] == "lantern-semantic-context/2"
    assert result["source_schema"] == ctx["schema"]
    assert result["source_schema_supported"] is True
    assert result["source_ases_version"] == ctx["ases_version"]
    assert "behaviors" in result["attack_surface"]
    assert "data_stores" in result["attack_surface"]
    assert "external_systems" in result["attack_surface"]
    assert result["observed_controls"] == ctx["controls"]
    assert result["sessions"] == ctx["sessions"]


def test_adapt_defaults_everything_on_an_unknown_schema(tmp_path):
    result = adapter.adapt({"schema": "ases-consumer-context/99.0"})
    assert result["source_schema_supported"] is False
    assert result["attack_surface"]["behaviors"] == []
    assert result["observed_controls"] == []
    assert result["uncertainty"] == {"conflicts": [], "unknowns": []}


def test_cli_roundtrip_writes_a_file(tmp_path):
    ctx = _consumer_context(tmp_path)
    src = tmp_path / "in.json"
    dst = tmp_path / "out.json"
    src.write_text(__import__("json").dumps(ctx), encoding="utf-8")
    assert adapter.main([str(ADAPTER_PATH), str(src), str(dst)]) == 0
    written = __import__("json").loads(dst.read_text())
    assert written["source_schema"] == ctx["schema"]


def test_cli_without_args_prints_usage_and_returns_error():
    assert adapter.main(["adapter.py"]) == 1
