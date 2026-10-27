"""Inspectably scoped document evaluation. Labels and target runs remain separate."""
from __future__ import annotations

from collections import Counter
from html import escape
import json
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from time import perf_counter

from .model import digest
from .service import read_json


def counts(actual, expected):
    actual, expected = set(actual), set(expected)
    tp, fp, fn = actual & expected, actual - expected, expected - actual
    return {"TP": len(tp), "FP": len(fp), "FN": len(fn), "expected": len(expected), "predicted": len(actual),
            "precision": len(tp) / len(actual) if actual else None, "recall": len(tp) / len(expected) if expected else None,
            "correct": sorted(tp), "unexpected": sorted(fp), "missing": sorted(fn)}


def evaluate_documents(corpus_path, out):
    from ..pipeline import prepare_output, scan_project
    from .claim_evaluation import validate_oracles, score_claims, summarize
    corpus = read_json(corpus_path, 8 * 1024 * 1024)
    if not isinstance(corpus, dict) or corpus.get("schema") != "ases-document-corpus/1" or not isinstance(corpus.get("cases"), list) or not corpus["cases"] or not isinstance(corpus.get("label_review"), str) or not corpus["label_review"].strip():
        raise ValueError("Expected document corpus with nonempty cases and explicit label_review")
    seen = set()
    # Validate the entire corpus before replacing an output directory.
    for case in corpus["cases"]:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"] or case["id"] in seen:
            raise ValueError("Cases need unique nonempty IDs")
        seen.add(case["id"])
        validate_oracles(case.get("behaviors", []))
        if not isinstance(case.get("files"), dict) or not case["files"] or not isinstance(case.get("requirements"), list):
            raise ValueError("Case needs own source files and a closed requirement-ID oracle")
        if not all(isinstance(r, str) and r for r in case["requirements"]) or len(case["requirements"]) != len(set(case["requirements"])):
            raise ValueError("Requirement-ID oracle needs unique nonempty strings")
        for collection in ("fields", "links", "checks"):
            labels = case.get(collection, [])
            if not isinstance(labels, list):
                raise ValueError("Expected label list: " + collection)
            for label in labels:
                if not isinstance(label, dict) or "expected" not in label:
                    raise ValueError("Labels need an explicit expected value")
                if collection in {"fields", "links"} and (not isinstance(label.get("select"), dict) or not label["select"] or not all(isinstance(k, str) for k in label["select"])):
                    raise ValueError("Labels need a nonempty selector")
                if collection == "fields" and (not isinstance(label.get("field"), str) or not label["field"]):
                    raise ValueError("Field labels need a field path")
                if collection in {"links", "checks"} and not isinstance(label["expected"], bool):
                    raise ValueError("Presence labels need boolean expectations")
                if collection == "checks" and (not isinstance(label.get("kind"), str) or not label["kind"]):
                    raise ValueError("Check labels need a named kind")
        for name, text in case["files"].items():
            if not isinstance(name, str) or not name or "\\" in name or ":" in name or PurePosixPath(name).is_absolute() or any(p in {"", ".", ".."} for p in name.split("/")) or not isinstance(text, str):
                raise ValueError("Unsafe fixture path or content")
    out = prepare_output(Path(out))
    cases = []
    started = perf_counter()
    for case in corpus["cases"]:
        with TemporaryDirectory(prefix="ases-doc-eval-", dir=out) as temporary:
            root = Path(temporary) / "source"
            for name, text in case["files"].items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            start = perf_counter()
            model = scan_project(root, Path(temporary) / "scan")["engineering_model"]
            reqs = {r["id"]: r for r in model["requirements"]}
            result = {"id": case["id"], "requirements": counts(reqs, case["requirements"]), "coverage": model["coverage"],
                      "seconds": round(perf_counter() - start, 4), "fields": [], "links": [], "checks": []}
            all_rows = model["requirements"] + model["api"] + model.get("recovered_requirements", [])
            for label in case.get("fields", []):
                matches = [r for r in all_rows if all(r.get(k) == v for k, v in label["select"].items())]
                value = matches[0] if len(matches) == 1 else None
                for key in label["field"].split("."):
                    value = value.get(key) if isinstance(value, dict) else value[int(key)] if isinstance(value, list) and key.isdigit() and int(key) < len(value) else None
                result["fields"].append({**label, "actual": value, "correct": len(matches) == 1 and value == label["expected"], "matches": len(matches)})
            for label in case.get("links", []):
                present = any(all(link.get(k) == v for k, v in label["select"].items()) for link in model["links"])
                result["links"].append({**label, "actual": present, "correct": present == label["expected"]})
            for label in case.get("checks", []):
                present = any(i["kind"] == label["kind"] for i in model["issues"])
                result["checks"].append({**label, "actual": present, "correct": present == label["expected"]})
            result["behaviors"] = score_claims(model, case.get("behaviors", []))
            result["output_bytes"] = len(json.dumps(model, ensure_ascii=False).encode())
            result["passed"] = not result["requirements"]["FP"] and not result["requirements"]["FN"] and all(r["correct"] for key in ("fields", "links", "checks") for r in result[key]) and all(label["passed"] for label in result["behaviors"])
            cases.append(result)
    summary = {key: sum(c["requirements"][key] for c in cases) for key in ("TP", "FP", "FN", "expected", "predicted")}
    summary.update(precision=summary["TP"] / summary["predicted"] if summary["predicted"] else None,
                   recall=summary["TP"] / summary["expected"] if summary["expected"] else None)
    fields = {key: {"correct": sum(r["correct"] for c in cases for r in c[key]), "labelled": sum(len(c[key]) for c in cases)} for key in ("fields", "links", "checks")}
    report = {"schema": "ases-document-evaluation/1", "corpus_digest": digest(corpus), "label_review": corpus["label_review"],
              "limitations": corpus.get("limitations", []), "requirements": summary, **fields, "behavior_claims": summarize(cases), "cases": cases,
              "seconds": round(perf_counter() - started, 4), "target_tests_executed": 0,
              "meaning": "Closed labelled scope only. Field/link correctness and document completeness are separate. No global project score."}
    (out / "document-accuracy.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Document accuracy", "", "Label review: " + report["label_review"], "", report["meaning"], "",
             "| Scope | TP / correct | FP | FN | Labels |", "|---|---:|---:|---:|---:|",
             f"| Requirement IDs | {summary['TP']} | {summary['FP']} | {summary['FN']} | {summary['expected']} |"]
    lines += [f"| {k} | {v['correct']} | — | — | {v['labelled']} |" for k, v in fields.items()]
    lines += [f"| Behavior {k} | {v['TP']} | {v['FP']} | {v['FN']} | {v['expected']} |" for k,v in report["behavior_claims"]["categories"].items()]
    lines += ["", "## Cases", ""]
    for case in cases:
        lines += ["### " + case["id"], "", "```json", json.dumps(case, ensure_ascii=False, indent=2), "```", ""]
    lines += ["## Limits", ""] + ["- " + s for s in report["limitations"]]
    text = "\n".join(lines) + "\n"
    (out / "DOCUMENT-ACCURACY.md").write_text(text, encoding="utf-8")
    (out / "document-accuracy.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>ASES document accuracy</title><style>body{font:17px system-ui;background:#f5f7ef;color:#193d2c;max-width:1000px;margin:2rem auto;padding:1rem}pre{white-space:pre-wrap;overflow-wrap:anywhere}details{border-top:1px solid #abc1ad;padding:1rem}summary{cursor:pointer}</style><h1>ASES document accuracy</h1><p>' + escape(report["meaning"]) + '</p><p>Label review: ' + escape(report["label_review"]) + '</p><h2>Measured scope</h2><pre>' + escape(json.dumps({"requirements": summary, **fields, "behavior_claims": report["behavior_claims"]}, indent=2)) + '</pre>' + ''.join('<details><summary>' + escape(c["id"]) + (' — PASS' if c["passed"] else ' — REVIEW') + '</summary><pre>' + escape(json.dumps(c, ensure_ascii=False, indent=2)) + '</pre></details>' for c in cases) + '<h2>Limits</h2><ul>' + ''.join('<li>' + escape(s) + '</li>' for s in report["limitations"]) + '</ul></html>', encoding="utf-8")
    return report
