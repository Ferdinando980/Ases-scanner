from pathlib import Path
import re
from ases.pipeline import scan_project
from ases.renderers.markdown import doc_signature

SIG_RE = re.compile(r"^<!-- ases:doc fingerprint=[0-9a-f]{64} ases_version=\S+ -->\n")

def test_signed_docs_carry_a_matching_fingerprint(tmp_path):
    fixture = Path(__file__).parent / "fixture_python"
    out = tmp_path / "out"
    result = scan_project(fixture, out)
    fp = result["manifest"]["project_fingerprint"]
    for name in ("SUMMARY.md", "SYSTEM-OVERVIEW.md", "RAD.md", "SDD.md", "ODD.md", "TESTING.md"):
        text = (out / "docs" / name).read_text(encoding="utf-8")
        m = SIG_RE.match(text)
        assert m, f"{name}: missing or malformed ases:doc signature"
        assert f"fingerprint={fp}" in text, f"{name}: fingerprint does not match manifest.json"
    # Data files (not prose a person is meant to confirm/edit) stay unsigned.
    for name in ("TRACEABILITY.yaml", "CONTROLS.yaml", "QUALITY.md"):
        text = (out / "docs" / name).read_text(encoding="utf-8")
        assert not text.startswith("<!-- ases:doc"), f"{name}: should not carry a doc signature"

def test_doc_signature_is_a_pure_function_of_the_manifest():
    a = doc_signature({"project_fingerprint": "abc", "ases_version": "1.7.0"})
    b = doc_signature({"project_fingerprint": "abc", "ases_version": "1.7.0"})
    c = doc_signature({"project_fingerprint": "xyz", "ases_version": "1.7.0"})
    assert a == b
    assert a != c
