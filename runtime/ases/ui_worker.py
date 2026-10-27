"""Isolated desk job. Reads a private request file; never starts a web server."""
from __future__ import annotations

import gc
from collections import Counter
import json
import os
from pathlib import Path
import sys
import tempfile
from time import monotonic, sleep

from .ui_operations import execute, load_context


def write_state(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    for attempt in range(8):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            # Windows readers/antivirus can briefly deny replacement of an open file.
            if attempt == 7:
                raise
            sleep(0.01 * (attempt + 1))


def operation_preview(data, action):
    """Bound browser delivery. Original results remain complete in the download."""
    if data is None:
        return None
    if action == "export":
        return {"schema": data["schema"], "snapshot_id": data.get("snapshot_id"), "project": data.get("project"),
                "counts": {key: len(value) for key, value in data.items() if isinstance(value, list)},
                "delivery": {"truncated": True, "complete_file": "export.json"}}
    truncated = False
    def reduce(value, depth=0):
        nonlocal truncated
        if isinstance(value, str) and len(value) > 1500:
            truncated = True
            return value[:1500] + "…"
        if isinstance(value, list):
            if len(value) > 10:
                truncated = True
            return [reduce(item, depth + 1) for item in value[:10]]
        if isinstance(value, dict):
            if depth > 5:
                truncated = True
                return {"preview": "See complete result in download"}
            return {key: reduce(item, depth + 1) for key, item in value.items()}
        return value
    preview = reduce(data)
    preview["delivery"] = {"truncated": truncated, "complete_file": "operation-result.json"}
    if action == "accuracy":
        preview["case_summary"] = {"total": len(data["cases"]), "passed": sum(c["passed"] for c in data["cases"].values())}
    if action == "artifact":
        preview["counts"] = {"files": len(data["files"]), "unknowns": len(data.get("unknowns", []))}
    if action == "reconcile":
        preview["match_summary"] = {key: dict(Counter(row["status"] for row in data[key])) for key in ("source_matches", "runtime_matches")}
    if action == "compare":
        preview["semantic"]["uncertain_count"] = len(data["semantic"].get("uncertain", []))
    if action == "site":
        preview["counts"] = {"pages": len(data["pages"]), "forms": sum(len(p.get("forms", [])) for p in data["pages"])}
    return preview


def run(workspace):
    workspace = Path(workspace).resolve(strict=True)
    request = json.loads((workspace / "request.json").read_text(encoding="utf-8"))
    scratch = workspace / "scratch"
    scratch.mkdir()
    os.environ["TEMP"] = os.environ["TMP"] = str(scratch)
    tempfile.tempdir = str(scratch)
    started = monotonic()
    stage = "starting"

    def progress(value):
        nonlocal stage
        stage = value
        try:
            write_state(workspace / "progress.json", {"stage": stage, "elapsed": round(monotonic() - started, 1)})
        except OSError:
            pass  # A missed progress refresh must never fail the actual analysis.

    try:
        progress("starting")
        operation = execute(request["action"], request["options"], workspace / "report.ases",
                            retain_source=lambda _: None, progress=progress, workspace=workspace)
        scan = operation.pop("scan")
        root = operation["root"]
        if scan is not None:
            # Release the AST/fact/model graphs before opening the sealed delivery snapshot.
            compact = {"inventory": scan["inventory"], "validation": scan["validation"], "output": scan["output"]}
            del scan
            gc.collect()
            progress("presentation")
            context = load_context(operation["output"])
            findings_path = operation["output"] / "scanner-findings.json"
            findings = json.loads(findings_path.read_text(encoding="utf-8")) if findings_path.exists() else {"findings": []}
            from .ui import build_report, readable_report
            report = {**build_report(compact, context, findings), "kind": "scan", "action": operation["action"], "data": operation_preview(operation["data"], operation["action"])}
            for lang, filename in (("it", "REPORT.it.md"), ("en", "REPORT.md")):
                (operation["output"] / "docs" / filename).write_text(readable_report(report, lang), encoding="utf-8")
                if filename not in report["documents"]:
                    report["documents"].append(filename)
        else:
            report = {"kind": "operation", "action": operation["action"], "data": operation_preview(operation["data"], operation["action"])}
        write_state(workspace / "result.json", {"root": str(root) if root is not None else None,
                                               "action": operation["action"], "report": report})
        progress("complete")
        return 0
    except Exception as exc:
        write_state(workspace / "error.json", {"code": "scan_failed", "stage": stage,
                                              "detail": str(exc)[:1200], "type": type(exc).__name__})
        return 1


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1]))
