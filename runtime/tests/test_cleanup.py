from pathlib import Path
import pytest
from ases.pipeline import clean_output, scan_project


def test_rescan_replaces_generated_output(tmp_path):
    fixture = Path(__file__).parent / "fixture_spring"
    out = tmp_path / "project.ases"
    scan_project(fixture, out)
    stale = out / "stale.txt"
    stale.write_text("old", encoding="utf-8")

    scan_project(fixture, out)

    assert not stale.exists()
    assert (out / ".ases-output").exists()
    assert (out / "scanner-findings.json").exists()


def test_clean_output_refuses_unrecognized_directory(tmp_path):
    ordinary = tmp_path / "ordinary"
    ordinary.mkdir()
    (ordinary / "keep.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError):
        clean_output(ordinary)

    assert ordinary.exists()

def test_clean_output_removes_ases_directory(tmp_path):
    out = tmp_path / "project.ases"
    out.mkdir()
    (out / "x").write_text("x", encoding="utf-8")
    (out / ".ases-output").write_text("ASES generated output. Safe to remove.\n", encoding="utf-8")
    assert clean_output(out) is True
    assert not out.exists()
