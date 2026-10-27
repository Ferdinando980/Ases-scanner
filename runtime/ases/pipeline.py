from __future__ import annotations
from pathlib import Path
import json, shutil, yaml
from .model import FactGraph
from .scanners.filesystem import scan_filesystem
from .scanners.java import scan_java
from .scanners.typescript import scan_typescript
from .scanners.python import scan_python
from .scanners.frontend import scan_frontend
from .recovery.controls import recover_controls
from .recovery.traceability import enrich_traceability
from .recovery.semantic import build_semantic_model
from .renderers.markdown import system_overview, recovered_rad, recovered_sdd, recovered_odd, testing_baseline, quality_report, doc_signature, decision_summary
from .validation import validate_model
from .manifest import build_manifest
from .export import generic_context
from .scanner_output import scanner_findings

OUTPUT_MARKER = ".ases-output"


def _output_path(path: Path) -> Path:
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.is_symlink() or (part.exists() and getattr(part.lstat(), "st_file_attributes", 0) & 1024):
            raise ValueError(f"ASES output cannot follow a symlink or junction: {part}")
    return path.resolve()


def is_generated_output(path: Path) -> bool:
    try:
        path = _output_path(path)
        return (path.is_dir() and (path / OUTPUT_MARKER).is_file() and
                not any((path / name).exists() for name in ("STANDARD.md", "GATES.md", "AGENTS.md", ".git")))
    except (OSError, ValueError):
        return False


def default_output(root: Path) -> Path:
    candidate = root / ".ases"
    return root / "ases-scan.ases" if candidate.exists() and not is_generated_output(candidate) else candidate

def clean_output(path: Path) -> bool:
    path = _output_path(path)
    if not path.exists():
        return False
    if not path.is_dir():
        raise ValueError(f"Not a directory: {path}")
    if not is_generated_output(path):
        raise ValueError(f"Refusing to remove unrecognized ASES output directory: {path}")
    shutil.rmtree(path)
    return True

def prepare_output(path: Path, *, clear=True) -> Path:
    path = _output_path(path)
    if path.exists():
        if not path.is_dir():
            raise ValueError(f"Not an ASES output directory: {path}")
        if any(path.iterdir()) and not is_generated_output(path):
            raise ValueError(f"Output contains user material or an engineering kit; choose an empty --out: {path}")
        if clear and is_generated_output(path):
            clean_output(path)
    path.mkdir(parents=True, exist_ok=True)
    (path / OUTPUT_MARKER).write_text("ASES generated output. Safe to remove.\n", encoding="utf-8")
    return path


def scan_project(root: Path, out: Path | None = None, source_uri: str | None = None,
                 site_observations: dict | None = None, *, progress=None, exclude=(), limits=None) -> dict:
    from .scanners.filesystem import source_catalog
    with source_catalog(root, exclusions=exclude, limits=limits):
        return _scan_project(root, out, source_uri, site_observations, progress=progress, exclude=exclude)


def _scan_project(root, out, source_uri, site_observations, *, progress, exclude):
    def stage(name):
        if progress is not None:
            progress(name)
    root = root.absolute().resolve()
    if not root.is_dir():
        raise ValueError("Scan source must be an existing directory")
    out = _output_path(out if out is not None else default_output(root))
    if root.is_relative_to(out):
        raise ValueError("Scan output cannot replace the source or its ancestors")
    out = prepare_output(out)
    docs = out / "docs"
    docs.mkdir(parents=True, exist_ok=True)

    stage("inventory")
    inventory = scan_filesystem(root)
    if site_observations is None:
        from .scanners.javascript import parser_profile
        from .scanners.filesystem import FILESYSTEM_PROFILE
        inventory["parser_profile"] = {**parser_profile(), "filesystem": FILESYSTEM_PROFILE}
        from .scanners.python_http import PROFILE as http_profile
        inventory["parser_profile"]["python_http"] = http_profile
        from .recovery.patterns import PROFILE as pattern_profile
        inventory["parser_profile"]["patterns"] = pattern_profile
        ignore = root / ".asesignore"
        inventory["exclusions"] = (ignore.read_text(encoding="utf-8").splitlines() if ignore.is_file() else []) + list(exclude)
    graph = FactGraph()
    if site_observations is None:
        for scanner in (scan_java, scan_typescript, scan_python, scan_frontend):
            stage({scan_java: "java", scan_typescript: "javascript", scan_python: "python", scan_frontend: "frontend"}[scanner])
            graph.merge(scanner(root))
        stage("relations")
        recover_controls(root, graph)
        test_paths = set(inventory.get("tests", []))
        for node in graph.nodes:
            if node.path in test_paths:
                node.metadata["is_test_code"] = True
        enrich_traceability(graph)
        from .scanners.filesystem import unavailable_sources, source_unavailable
        for missing in unavailable_sources(root):
            source_unavailable(root,root/missing['path'],graph)

    stage("model")
    model = build_semantic_model(root.name, inventory, graph, root if site_observations is None else None)
    if source_uri:
        model["project"]["source_uri"] = source_uri
    if site_observations is not None:
        from .site_source import enrich_site_model
        enrich_site_model(model, site_observations)
    graph_dict = graph.to_dict()

    # Schema path is resolved relative to installed package layout when available.
    candidate = Path(__file__).resolve().parents[2] / "schemas" / "semantic-model.schema.json"
    stage("validation")
    validation = validate_model(model, candidate if candidate.exists() else None)
    if "semantic_quality" in model:
        model["semantic_quality"]["schema_status"] = validation["status"]
    manifest = build_manifest(inventory, model, graph_dict)
    from .evidence import public_context
    context_v2 = public_context(model, graph_dict, inventory, manifest)
    from .evidence import validate_context
    validate_context(context_v2)
    stage("documents")
    sig = doc_signature(manifest)
    engineering = None
    if site_observations is None:
        from .engineering.model import build_engineering
        engineering = build_engineering(root, inventory, graph_dict, model, context_v2["snapshot_id"], progress)

    stage("document-rendering")

    def dump_yaml(value):
        return yaml.safe_dump(value, sort_keys=False, allow_unicode=True)

    outputs = {
        out / "inventory.yaml": dump_yaml(inventory),
        out / "fact-graph.json": json.dumps(graph_dict, separators=(",", ":")),
        out / "semantic-model.yaml": dump_yaml(model),
        out / "semantic-quality.json": json.dumps(model.get("semantic_quality", {}), indent=2),
        out / "manifest.json": json.dumps(manifest, indent=2),
        out / "validation.json": json.dumps(validation, indent=2),
        out / "consumer-context.json": json.dumps(generic_context(model, manifest), indent=2),
        out / "consumer-context.v2.json": json.dumps(context_v2, separators=(",", ":")),
        out / "scanner-findings.json": json.dumps(scanner_findings(model), indent=2),
        # Signed (doc_signature): a consumer can tell these five are fully regenerated from the
        # current project state, and compare the embedded fingerprint against a fresh manifest.json
        # to decide if they are stale, instead of guessing from a file's mtime.
        docs / "SYSTEM-OVERVIEW.md": sig + system_overview(model, inventory),
        docs / "SUMMARY.md": sig + decision_summary(model),
        docs / "RAD.md": sig + recovered_rad(model),
        docs / "SDD.md": sig + recovered_sdd(model),
        docs / "ODD.md": sig + recovered_odd(model, graph_dict),
        docs / "TESTING.md": sig + testing_baseline(model),
        docs / "TRACEABILITY.yaml": dump_yaml({"trace_links": model["trace_links"]}),
        docs / "CONTROLS.yaml": dump_yaml({"controls": model.get("controls", [])}),
        docs / "QUALITY.md": quality_report(model),
    }
    if site_observations is not None:
        outputs = {path: content for path, content in outputs.items() if path.parent != docs}
        outputs[out / "site-observations.json"] = json.dumps(site_observations, indent=2)
        lines = ["# Published frontend observation", "", f"Source: {site_observations['source_uri']}", "",
                 f"Sampled pages: {len(site_observations['pages'])}", "", "## Pages", ""]
        lines.extend(f"- [{page['title'] or page['url']}]({page['url']}) — {len(page['forms'])} forms, {len(page['scripts'])} script URLs"
                     for page in site_observations["pages"])
        lines += ["", "## Limits", ""]
        lines.extend(f"- {limit}" for limit in site_observations["limits"])
        outputs[docs / "SITE-OVERVIEW.md"] = sig + "\n".join(lines) + "\n"
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
    if engineering is not None:
        from .engineering.service import write_documents
        (out / "engineering-model.json").write_text(json.dumps(engineering, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        write_documents(engineering, docs, signature=sig)
    stage("complete")

    return {
        "inventory": inventory,
        "graph": graph_dict,
        "semantic_model": model,
        "manifest": manifest,
        "validation": validation,
        "engineering_model": engineering,
        "output": str(out),
    }
