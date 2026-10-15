"""Bounded source/oracle evaluation. Target source is parsed, never executed."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path, PurePosixPath
import re
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

from .pipeline import prepare_output, scan_project
from .quality_eval import FINDING_GROUPS, evaluate_predictions, summarize


def claim(parts):
    return json.dumps(parts, ensure_ascii=False, separators=(",", ":"))


def validate_corpus(corpus):
    """Validate all cases before creating or replacing any output."""
    if not isinstance(corpus, dict) or corpus.get("schema") != "ases-accuracy-corpus/1":
        raise ValueError("Unsupported corpus schema")
    if not isinstance(corpus.get("label_review"), str) or not corpus["label_review"]:
        raise ValueError("Corpus must declare label review status")
    if not isinstance(corpus.get("limitations"), list) or not all(isinstance(x, str) for x in corpus["limitations"]):
        raise ValueError("Corpus limitations must be strings")
    if not isinstance(corpus.get("cases"), list) or not corpus["cases"]:
        raise ValueError("Corpus needs nonempty cases")
    seen = set()
    for case in corpus["cases"]:
        if not isinstance(case, dict):
            raise ValueError("Each case must be an object")
        name = case.get("id", "")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,79}", name) or name in seen:
            raise ValueError("Invalid or duplicate case id")
        seen.add(name)
        for field in ("family", "language", "rationale"):
            if not isinstance(case.get(field), str) or not case[field]:
                raise ValueError(f"{name}: missing {field}")
        files = case.get("files")
        if not isinstance(files, dict) or not files:
            raise ValueError(f"{name}: missing source files")
        for path, source in files.items():
            if (not isinstance(path, str) or not path or "\\" in path or ":" in path
                    or PurePosixPath(path).is_absolute() or any(p in ("", ".", "..") for p in path.split("/"))
                    or not isinstance(source, str)):
                raise ValueError(f"{name}: unsafe source path or invalid source")
        scope = case.get("scope", {})
        if not isinstance(scope, dict):
            raise ValueError(f"{name}: invalid scope")
        collection = scope.get("collection")
        if collection not in {"entities", "relations", "findings"}:
            raise ValueError(f"{name}: invalid collection")
        selectors = scope.get("select")
        if not isinstance(selectors, list) or not selectors or not all(isinstance(s, str) and s for s in selectors):
            raise ValueError(f"{name}: explicit kind/relation/rule selectors required")
        if not isinstance(scope.get("complete"), bool):
            raise ValueError(f"{name}: declare whether scoped oracle is complete")
        if not isinstance(case.get("metamorphic", False), bool):
            raise ValueError(f"{name}: metamorphic must be boolean")
        oracle = case.get("oracle", {})
        if not isinstance(oracle, dict):
            raise ValueError(f"{name}: invalid oracle")
        width = {"entities": 3, "relations": 7, "findings": 2}[collection]
        labelled = {}
        for state in ("present", "absent"):
            rows = oracle.get(state)
            if not isinstance(rows, list):
                raise ValueError(f"{name}: missing {state} labels")
            for row in rows:
                if not isinstance(row, list) or len(row) != width or not all(isinstance(x, str) for x in row):
                    raise ValueError(f"{name}: invalid label")
                if row[0] not in selectors:
                    raise ValueError(f"{name}: label outside selected scope")
                if collection == "entities" and row[1] not in files:
                    raise ValueError(f"{name}: entity label outside source scope")
                if collection == "relations" and (row[2] not in files or row[5] not in files):
                    raise ValueError(f"{name}: relation label outside source scope")
            labelled[state] = [claim(row) for row in rows]
            if len(set(labelled[state])) != len(rows):
                raise ValueError(f"{name}: duplicate labels")
        if set(labelled["present"]) & set(labelled["absent"]):
            raise ValueError(f"{name}: contradictory labels")
        for field in ("required_unknowns", "unsupported"):
            if not isinstance(case.get(field, []), list) or not all(isinstance(x, str) for x in case.get(field, [])):
                raise ValueError(f"{name}: invalid {field}")


def predictions(scan, case):
    scope = case["scope"]
    selected = set(scope["select"])
    graph = scan["graph"]
    nodes = {n["id"]: n for n in graph["nodes"]}
    descriptor = lambda n: [n["kind"], n.get("path") or "", n["name"]]
    if scope["collection"] == "entities":
        rows = [descriptor(n) for n in nodes.values() if n["kind"] in selected and n.get("path") in case["files"]]
    elif scope["collection"] == "relations":
        rows = [[e["relation"], *descriptor(nodes[e["source"]]), *descriptor(nodes[e["target"]])]
                for e in graph["edges"] if e["relation"] in selected
                and e["source"] in nodes and e["target"] in nodes
                and nodes[e["source"]].get("path") in case["files"]
                and nodes[e["target"]].get("path") in case["files"]]
    else:
        rows = [[f["rule_id"], f["status"]] for group in FINDING_GROUPS
                for f in scan["semantic_model"].get(group, []) if f["rule_id"] in selected]
    return [claim(row) for row in rows]


def run_case(case, work):
    source, output = work / case["id"], work / (case["id"] + ".ases")
    for name, content in case["files"].items():
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    start = perf_counter()
    scan = scan_project(source, output)
    actual = predictions(scan, case)
    oracle = {state: [claim(row) for row in case["oracle"][state]] for state in ("present", "absent")}
    oracle["unsupported"] = case.get("unsupported", [])
    result = evaluate_predictions(actual, oracle, complete=case["scope"]["complete"])
    unknowns = sorted({u["reason"] for u in scan["graph"].get("unknowns", [])})
    result.update({
        "case": case, "observed": sorted(set(actual)), "unknowns": unknowns,
        "labels": len(oracle["present"]) + len(oracle["absent"]),
        "missing_unknowns": sorted(set(case.get("required_unknowns", [])) - set(unknowns)),
        "collapsed_predictions": sum(count - 1 for count in Counter(actual).values()),
        "schema_valid": scan["validation"]["status"] == "PASS",
    })
    if case.get("metamorphic"):
        before = json.loads((output / "consumer-context.v2.json").read_text(encoding="utf-8"))
        for name, content in case["files"].items():
            comment = "#" if name.endswith(".py") else "//"
            (source / name).write_text(f"\n{comment} harmless position change\n\n" + content, encoding="utf-8")
        shifted = scan_project(source, output)
        after = json.loads((output / "consumer-context.v2.json").read_text(encoding="utf-8"))
        result["metamorphic"] = {
            "predictions_stable": set(actual) == set(predictions(shifted, case)),
            "entity_ids_stable": {e["id"] for e in before["entities"]} == {e["id"] for e in after["entities"]},
            "relation_ids_stable": {e["id"] for e in before["structural_relations"]} == {e["id"] for e in after["structural_relations"]},
            "unknowns_stable": unknowns == sorted({u["reason"] for u in shifted["graph"].get("unknowns", [])}),
            "schema_valid": shifted["validation"]["status"] == "PASS",
        }
    result["seconds"] = round(perf_counter() - start, 4)
    result["passed"] = not any((result["false_positive"], result["false_negative"],
                                result["missing_unknowns"], result["collapsed_predictions"],
                                not result["schema_valid"])) and all(result.get("metamorphic", {}).values())
    return result


def evaluate_corpus(corpus_path: Path, output: Path):
    corpus_path = corpus_path.resolve()
    payload = corpus_path.read_bytes()
    corpus = json.loads(payload)
    validate_corpus(corpus)
    # Never let a generated-output marker authorize removal of the input or code.
    resolved = output.absolute().resolve()
    package = Path(__file__).resolve().parent
    if corpus_path.is_relative_to(resolved) or package.is_relative_to(resolved):
        raise ValueError("Accuracy output cannot replace corpus or evaluator sources")
    output = prepare_output(output)
    with TemporaryDirectory(prefix="_work-", dir=output) as tmp:
        cases = {case["id"]: run_case(case, Path(tmp)) for case in corpus["cases"]}
    families = {}
    for family in sorted({case["family"] for case in corpus["cases"]}):
        group = {key: row for key, row in cases.items() if row["case"]["family"] == family}
        families[family] = {key: value for key, value in summarize(group).items() if key != "cases"}
        families[family]["labels"] = sum(row["labels"] for row in group.values())
        families[family]["case_count"] = len(group)
    code = sha256()
    for path in sorted(package.rglob("*.py")):
        code.update(path.relative_to(package).as_posix().encode())
        code.update(b"\0" + path.read_bytes() + b"\0")
    result = {
        "schema": "ases-accuracy-results/1", "generated_utc": datetime.now(timezone.utc).isoformat(),
        "corpus_sha256": sha256(payload).hexdigest(), "evaluator_and_scanner_sha256": code.hexdigest(),
        "label_review": corpus.get("label_review", "unspecified"),
        "environment": {"python": sys.version.split()[0], "platform": sys.platform,
                        "ases": version("ases"), "tree_sitter": version("tree-sitter"),
                        "tree_sitter_javascript": version("tree-sitter-javascript"),
                        "tree_sitter_typescript": version("tree-sitter-typescript")},
        "limitations": corpus.get("limitations", []), "families": families, "cases": cases,
        "passed": all(row["passed"] for row in cases.values()),
    }
    from .accuracy_report import write_report
    (output / "results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(result, output)
    return result
