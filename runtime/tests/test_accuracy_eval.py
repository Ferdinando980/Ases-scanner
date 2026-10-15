"""Verify the measuring instrument, including deliberate FP/FN injection."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from ases.accuracy import claim, evaluate_corpus, predictions, validate_corpus
from ases.quality_eval import evaluate_predictions, summarize


CORPUS_PATH = Path(__file__).parent / "fixture_accuracy/corpus.json"


def small_corpus():
    original = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    original["cases"] = [original["cases"][0]]
    return original


def test_scoring_detects_injected_false_alarm_and_omission():
    oracle = {"present": ["found", "missed"], "absent": ["spurious", "excluded"]}
    result = evaluate_predictions(["found", "spurious", "not-labelled"], oracle)
    summary = summarize({"case": result})
    assert {key: summary[key] for key in ("true_positive", "false_positive", "false_negative", "true_negative")} == {
        "true_positive": 1, "false_positive": 1, "false_negative": 1, "true_negative": 1}
    assert summary["precision"] == summary["recall"] == summary["f1"] == 0.5
    assert summary["unassessed"] == 1
    assert result["unassessed_findings"] == ["not-labelled"]
    complete = evaluate_predictions(["found", "spurious", "not-labelled"], oracle, complete=True)
    assert complete["false_positive"] == ["not-labelled", "spurious"]
    assert complete["unassessed_findings"] == []


def test_empty_and_negative_only_cases_do_not_receive_perfect_accuracy():
    empty = evaluate_predictions([], {"present": [], "absent": ["excluded"]})
    summary = summarize({"case": empty})
    assert summary["true_negative"] == 1
    assert summary["precision"] is summary["recall"] is summary["f1"] is None
    with pytest.raises(ValueError, match="both"):
        evaluate_predictions([], {"present": ["same"], "absent": ["same"]})


@pytest.mark.parametrize("path", ["../escape.py", "/absolute.py", "C:/private.py", "a\\b.py", "a/./b.py", "a//b.py"])
def test_corpus_rejects_source_path_escape(path):
    corpus = small_corpus()
    corpus["cases"][0]["files"] = {path: "pass"}
    with pytest.raises(ValueError, match="unsafe"):
        validate_corpus(corpus)


@pytest.mark.parametrize("mutation", ["overlap", "duplicates", "outside-scope", "duplicate-id", "missing-completeness"])
def test_corpus_rejects_ambiguous_oracles(mutation):
    corpus = small_corpus()
    case = corpus["cases"][0]
    if mutation == "overlap":
        case["oracle"]["absent"].append(deepcopy(case["oracle"]["present"][0]))
    elif mutation == "duplicates":
        case["oracle"]["present"].append(deepcopy(case["oracle"]["present"][0]))
    elif mutation == "outside-scope":
        case["oracle"]["present"][0][0] = "function"
    elif mutation == "duplicate-id":
        corpus["cases"].append(deepcopy(case))
    else:
        del case["scope"]["complete"]
    with pytest.raises(ValueError):
        validate_corpus(corpus)


def test_projected_relations_preserve_endpoint_type_file_and_direction():
    case = {"scope": {"collection": "relations", "select": ["calls"]}, "files": {"app.py": ""}}
    scan = {"graph": {"nodes": [
        {"id": "1", "kind": "function", "path": "app.py", "name": "handler"},
        {"id": "2", "kind": "function", "path": "app.py", "name": "helper"}],
        "edges": [{"source": "1", "target": "2", "relation": "calls"},
                  {"source": "1", "target": "2", "relation": "declares"}]}}
    assert predictions(scan, case) == [claim(["calls", "function", "app.py", "handler", "function", "app.py", "helper"])]


def test_runner_report_escaping_cleanup_and_green_red_gate(tmp_path):
    corpus = small_corpus()
    corpus["cases"][0]["files"]["app.py"] += '\n# </pre><script>alert("source")</script>\n'
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(corpus), encoding="utf-8")
    out = tmp_path / "report.ases"
    result = evaluate_corpus(path, out)
    assert result["passed"]
    row = next(iter(result["cases"].values()))
    assert all(row["metamorphic"].values())
    assert not row["collapsed_predictions"]
    assert sorted(p.name for p in out.iterdir()) == [".ases-output", "REPORT.md", "report.html", "results.json"]
    assert result == json.loads((out / "results.json").read_text(encoding="utf-8"))
    html = (out / "report.html").read_text(encoding="utf-8")
    assert "&lt;/pre&gt;&lt;script&gt;" in html
    assert '</pre><script>alert("source")</script>' not in html
    # Mutate the oracle, not ASES: the instrument must expose an omission.
    corpus["cases"][0]["oracle"]["present"].append(["route", "app.py", "GET /missing"])
    path.write_text(json.dumps(corpus), encoding="utf-8")
    red = evaluate_corpus(path, out)
    assert not red["passed"]
    assert next(iter(red["cases"].values()))["false_negative"] == [claim(["route", "app.py", "GET /missing"])]


def test_runner_refuses_destructive_output_and_validates_before_writing(tmp_path):
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(small_corpus()), encoding="utf-8")
    (tmp_path / ".ases-output").write_text("marker", encoding="utf-8")
    with pytest.raises(ValueError, match="cannot replace"):
        evaluate_corpus(path, tmp_path)
    assert path.is_file()
    out = tmp_path / "user"
    out.mkdir()
    (out / "keep.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="user material"):
        evaluate_corpus(path, out)
    path.write_text('{"schema": "wrong"}', encoding="utf-8")
    absent_output = tmp_path / "new-output"
    with pytest.raises(ValueError, match="schema"):
        evaluate_corpus(path, absent_output)
    assert not absent_output.exists()
    assert (out / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_default_corpus_is_valid():
    validate_corpus(json.loads(CORPUS_PATH.read_text(encoding="utf-8")))
