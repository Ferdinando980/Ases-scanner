import json
from pathlib import Path

from ases.pipeline import scan_project
from ases.quality_eval import evaluate_case, summarize


CORPUS = Path(__file__).parent / "fixture_quality"
ORACLE = json.loads((CORPUS / "oracle.json").read_text(encoding="utf-8"))["cases"]


def test_local_quality_corpus(tmp_path):
    cases = {}
    for name, expected in ORACLE.items():
        model = scan_project(CORPUS / name, tmp_path / f"{name}.ases")["semantic_model"]
        cases[name] = evaluate_case(model, expected)
    summary = summarize(cases)
    assert summary["false_negative"] == 0
    assert summary["false_positive"] == 0
    assert summary["true_positive"] == 7
    assert summary["true_negative"] == 12
    assert summary["precision"] == 1.0
    assert summary["recall"] == 1.0
    assert cases["spring_layers"]["unsupported_claims"] == ["CQRS", "Data Mapper"]


def test_quality_evaluation_does_not_count_unlabelled_or_unsupported_claims():
    model = {"pattern_findings": [{"rule_id": "architecture.mvc", "status": "OBSERVED"}]}
    result = evaluate_case(model, {"present": [], "absent": [], "unsupported": ["CQRS"]})
    assert result["unassessed_findings"] == ["architecture.mvc:OBSERVED"]
    assert result["unsupported_claims"] == ["CQRS"]
    assert summarize({"case": result})["precision"] is None


def test_quality_evaluation_counts_missed_and_spurious_findings():
    model = {"pattern_findings": [{"rule_id": "architecture.mvc", "status": "OBSERVED"}]}
    result = evaluate_case(model, {
        "present": ["architecture.layered:OBSERVED"],
        "absent": ["architecture.mvc:OBSERVED"],
    })
    summary = summarize({"case": result})
    assert summary["false_negative"] == 1
    assert summary["false_positive"] == 1
    assert summary["precision"] == 0.0
    assert summary["recall"] == 0.0
