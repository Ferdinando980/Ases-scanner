"""Explicit desk operations. Inputs are read; results only enter the owned session."""
from __future__ import annotations

import json
from hashlib import sha256
import os
from pathlib import Path
from urllib.parse import urlsplit

from .pipeline import scan_project, is_generated_output
from .semantic_diff import load_context as _load_context, semantic_diff
from .diffing import load_findings, diff_findings

DOCUMENTS = ("REPORT.md", "REPORT.it.md", "OVERVIEW.md", "SUMMARY.md", "SYSTEM-OVERVIEW.md", "RAD.md", "SDD.md", "ODD.md", "TESTING.md", "TP.md", "TCS.md", "TIR.md", "TSR.md", "GUIDE.md", "DOCUMENT-QUALITY.md", "TRACEABILITY.md", "TRACEABILITY.yaml", "CONTROLS.yaml", "QUALITY.md", "SITE-OVERVIEW.md")
SNAPSHOT_FILES = ("inventory.yaml", "fact-graph.json", "semantic-model.yaml", "semantic-quality.json", "manifest.json", "validation.json", "consumer-context.json", "consumer-context.v2.json", "scanner-findings.json", "site-observations.json", "artifact-snapshot.json", "engineering-model.json", "engineering-review.json", "docs/engineering-documents.json")
MAX_SNAPSHOT_BYTES = 256 * 1024 * 1024
SOURCE_LIMITS = {"files": 5000, "bytes": 128 * 1024 * 1024, "file_bytes": 2 * 1024 * 1024}


def load_context(path):
    return _load_context(path, max_bytes=MAX_SNAPSHOT_BYTES)


def clean_preview(source):
    path = input_path(source, directory=True)
    if not is_generated_output(path):
        raise ValueError("Only a recognized ASES generated-output folder can be removed.")
    entries = []
    for directory, directories, files in os.walk(path, followlinks=False):
        for name in sorted(directories + files):
            if len(entries) >= 10000:
                raise ValueError("This output is too large for the desk cleanup preview.")
            child = Path(directory) / name
            info = child.lstat()
            if child.is_symlink() or getattr(info, "st_file_attributes", 0) & 1024:
                raise ValueError("Linked entries cannot be removed through the desk.")
            entries.append([child.relative_to(path).as_posix(), info.st_size, info.st_mtime_ns])
    entries.sort()
    return {"target": str(path), "entries": len(entries), "preview": [e[0] for e in entries[:100]],
            "fingerprint": sha256(json.dumps(entries).encode()).hexdigest(), "status": "AWAITING_CONFIRMATION"}


def input_path(value, *, directory=False):
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        raise ValueError("Enter an existing local path.")
    path = Path(value.strip()).expanduser().resolve(strict=True)
    if directory and not path.is_dir():
        raise ValueError("Expected a directory.")
    return path


def copy_snapshot(source, output):
    """Copy only known report files, never arbitrary neighbors of a supplied snapshot."""
    source = input_path(source, directory=True)
    context = load_context(source)
    if context["schema"] != "ases-consumer-context/2.0":
        raise ValueError("The desk explorer requires a v2 snapshot. Read legacy documents directly or use ases inspect; no implicit rescan or conversion was performed.")
    output.mkdir()
    for relative in (*SNAPSHOT_FILES, *("docs/" + name for name in DOCUMENTS)):
        path = source / relative
        if not path.exists():
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(source) or not path.is_file() or path.stat().st_size > MAX_SNAPSHOT_BYTES:
            raise ValueError("Snapshot files must be bounded regular files inside the selected folder.")
        dest = output / relative
        dest.parent.mkdir(exist_ok=True)
        dest.write_bytes(path.read_bytes())
    return context


def execute(action, options, output, *, retain_source, progress=None, workspace=None):
    """Reuse scanner APIs without subprocess command composition or target execution."""
    source = options.get("source", "")
    other = options.get("other", "")
    baseline = options.get("baseline", "")
    root = None
    scan = None
    data = None
    if progress is not None:
        progress(action if action not in {"scan", "selfcheck", "audit"} else "starting")
    if action == "scan":
        from .repo_source import resolve_source, is_git_url
        if not isinstance(source, str) or len(source) > 4096:
            raise ValueError("Enter a local path or a public HTTPS Git URL.")
        if is_git_url(source):
            if progress is not None:
                progress("clone")
            url = urlsplit(source)
            if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError("The desk accepts public HTTPS Git URLs without credentials, queries, or fragments.")
            from .site_source import _public_host
            _public_host(source, False)
        resolved = resolve_source(source, timeout=120, interactive=False,
                                  checkout_parent=workspace / "checkout" if workspace is not None else None)
        retain_source(resolved)
        root = resolved.root
        exclusions = options.get("exclude", "")
        if not isinstance(exclusions, str) or len(exclusions) > 4000:
            raise ValueError("Exclusions must be a bounded list of patterns, one per line.")
        scan = scan_project(root, output, source_uri=resolved.display_source if resolved.is_remote else None,
                            progress=progress, exclude=tuple(line.strip() for line in exclusions.splitlines() if line.strip()),
                            limits=SOURCE_LIMITS)
        if baseline:
            before = input_path(baseline)
            delta = diff_findings(load_findings(before), load_findings(output))
            (output / "findings-diff.json").write_text(json.dumps(delta, indent=2), encoding="utf-8")
            delta = semantic_diff(load_context(before), load_context(output))
            (output / "semantic-diff.json").write_text(json.dumps(delta, indent=2), encoding="utf-8")
    elif action == "site":
        from .site_source import scan_site
        scan = scan_site(source, output, max_pages=int(options.get("pages", 5)))
        data = scan["semantic_model"]["site_observations"]
    elif action == "open":
        context = copy_snapshot(source, output)
        if other:
            root = input_path(other, directory=True)
        scan = {"output": str(output), "inventory": {"languages": context["project"].get("languages", [])}, "validation": context["validation"]}
    elif action == "artifact":
        from .artifacts import write_artifact
        data = write_artifact(input_path(source), output)
    elif action == 'interpret':
        provider = options.get('provider', 'llm')
        if provider == 'llm':
            endpoint = options.get('endpoint', '')
            if not endpoint:
                raise ValueError('Provider llm requires a local model server endpoint.')
            from .engineering.local_interpret import interpret,write_result
            result = interpret(input_path(source,directory=True),endpoint,maximum=3,progress=progress)
        elif provider == 'gliner2':
            python_executable = options.get('python_executable', '').strip()
            model_path = options.get('model_path', '').strip()
            if not python_executable or not model_path:
                raise ValueError('Provider gliner2 requires a local Python runtime and model directory.')
            from .engineering.semantic_extract import interpret
            result = interpret(input_path(source,directory=True),python_executable=python_executable,model_path=model_path)
            # The shared report writer and desk view use the existing candidate fields.
            result = {**result, 'candidates': result.get('hypotheses', []), 'rejected_candidates': 0}
            from .engineering.local_interpret import write_result
        else:
            raise ValueError('Choose provider llm or gliner2.')
        data=write_result(result,output)
    elif action == 'runtime-check':
        from .engineering.runtime_evidence import correlate
        data=correlate(input_path(source,directory=True),input_path(other))
    elif action == "reconcile":
        from .artifacts import load_artifact, load_runtime, reconcile_artifact
        mappings = json.loads(options.get("mappings", "[]") or "[]")
        if not isinstance(mappings, list):
            raise ValueError("Runtime mappings must be a JSON list.")
        data = reconcile_artifact(load_context(input_path(source)), load_artifact(input_path(other)),
                                  load_runtime(input_path(baseline)) if baseline else None, mappings)
    elif action == "compare":
        before, after = input_path(source), input_path(other)
        data = {"findings": diff_findings(load_findings(before), load_findings(after)),
                "semantic": semantic_diff(load_context(before), load_context(after))}
        if all(path.is_dir() and (path / "engineering-model.json").is_file() for path in (before, after)):
            from .engineering.model import engineering_diff
            from .engineering.service import load_reviewed_model
            data["engineering"] = engineering_diff(load_reviewed_model(before), load_reviewed_model(after))
    elif action == "audit":
        from .audit import audit_project
        data = audit_project(input_path(source, directory=True), scan_options={"progress": progress, "limits": SOURCE_LIMITS})
    elif action == "export":
        from .export import export_json
        output.mkdir()
        data = export_json(input_path(source), output / "export.json", schema=options.get("schema", "2.0"), max_snapshot_bytes=MAX_SNAPSHOT_BYTES)
    elif action == "selfcheck":
        from .selfcheck import selfcheck
        root = input_path(source, directory=True)
        scan = scan_project(root, output, progress=progress, limits=SOURCE_LIMITS)
        data = {**selfcheck(root, scan_result=scan), "meaning": "Static capability-file recognition; not a test-suite execution."}
    elif action == "accuracy":
        from .accuracy import evaluate_corpus
        corpus = Path(__file__).resolve().parents[1] / "tests" / "fixture_accuracy" / "corpus.json" if source == "bundled" else input_path(source)
        data = evaluate_corpus(corpus, output)
    elif action == "clean":
        data = clean_preview(source)
    else:
        raise ValueError("Unknown desk operation.")
    if data is not None:
        output.mkdir(exist_ok=True)
        (output / "operation-result.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"scan": scan, "data": data, "root": root, "output": output, "action": action}
