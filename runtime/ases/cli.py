from __future__ import annotations
import argparse, json, yaml
from pathlib import Path
from urllib.parse import urlsplit
from .pipeline import scan_project, clean_output, default_output, is_generated_output
from .audit import audit_project
from .selfcheck import selfcheck
from .export import export_json
from .repo_source import resolve_source
from .diffing import load_findings, diff_findings
from .semantic_diff import load_context, semantic_diff
from . import __version__

def build_parser():
    p = argparse.ArgumentParser(prog="ases", description="ASES software-engineering and reverse-engineering toolkit")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Recover a semantic baseline from a local path or Git repository URL")
    scan.add_argument("source", help="Local repository path or Git URL")
    scan.add_argument("--out", help="Output directory")
    scan.add_argument("--json", action="store_true")
    scan.add_argument("--baseline", help="Previous .ases directory or scanner-findings.json; writes findings-diff.json")

    site = sub.add_parser("scan-site", help="Observe the published frontend of a public HTTP(S) site")
    site.add_argument("url", help="Public website URL")
    site.add_argument("--out", help="Output directory (default: <host>.site.ases)")
    site.add_argument("--max-pages", type=int, default=5, help="Maximum same-origin HTML pages (1–10; default: 5)")
    site.add_argument("--allow-local", action="store_true", help="Allow private/local addresses for a trusted test site")
    site.add_argument("--json", action="store_true")

    inspect = sub.add_parser("inspect", help="Summarize a semantic model")
    inspect.add_argument("path")
    inspect.add_argument("--collection", choices=["entities", "structural_relations", "observations", "analysis_unknowns", "behaviors", "controls", "tests", "external_systems"])
    inspect.add_argument("--select")
    inspect.add_argument("--offset", type=int, default=0)
    inspect.add_argument("--limit", type=int, default=64)

    trace = sub.add_parser("trace", help="Trace an exact entity/route selector in a saved public snapshot")
    trace.add_argument("path")
    trace.add_argument("selector")
    trace.add_argument("--direction", choices=["forward", "backward"], default="forward")
    trace.add_argument("--max-nodes", type=int, default=10000)

    artifact = sub.add_parser("scan-artifact", help="Inspect a supplied local artifact without building or executing it")
    artifact.add_argument("path")
    artifact.add_argument("--out", required=True)
    reconcile = sub.add_parser("reconcile-artifact", help="Correlate saved source/artifact snapshots and optional imported runtime observations")
    reconcile.add_argument("source")
    reconcile.add_argument("artifact")
    reconcile.add_argument("--runtime")
    reconcile.add_argument("--mapping", action="append", default=[], help="JSON runtime_prefix/artifact_prefix mapping")
    reconcile.add_argument("--out")

    audit = sub.add_parser("audit", help="Compare a fresh scan against the stored .ases baseline")
    audit.add_argument("path")
    audit.add_argument("--json", action="store_true")


    diff = sub.add_parser("diff", help="Compare two ASES scanner outputs using stable finding fingerprints")
    diff.add_argument("before", help="Previous .ases directory or scanner-findings.json")
    diff.add_argument("after", help="Current .ases directory or scanner-findings.json")
    diff.add_argument("--out", help="Optional JSON output path")

    semdiff = sub.add_parser("semantic-diff", help="Compare two ASES semantic snapshots")
    semdiff.add_argument("before", help="Previous .ases directory or consumer-context.json")
    semdiff.add_argument("after", help="Current .ases directory or consumer-context.json")
    semdiff.add_argument("--out", help="Optional JSON output path")

    exp = sub.add_parser("export", help="Export generic consumer context")
    exp.add_argument("path", help="semantic-model.yaml or .ases directory")
    exp.add_argument("--out", required=True)
    exp.add_argument("--schema", choices=["1.5", "2.0"], default="1.5")

    clean = sub.add_parser("clean", help="Remove generated ASES scan output")
    clean.add_argument("path", nargs="?", help=".ases output directory to remove")
    clean.add_argument("--all", action="store_true", help="Remove direct .ases outputs in the current directory")

    sc = sub.add_parser("selfcheck", help="Use ASES to inspect its own repository/runtime")
    sc.add_argument("path", nargs="?", default=".")
    sc.add_argument("--clean", action="store_true", help="Remove .ases-selfcheck after completion")
    return p

def _default_remote_output(repo_name: str) -> Path:
    return Path.cwd() / f"{repo_name}.ases"

def main(argv=None):
    try:
        return _main(argv)
    except (ValueError, OSError) as exc:
        raise SystemExit(str(exc)) from exc


def _main(argv=None):
    args = build_parser().parse_args(argv)

    if args.command == "scan-site":
        from .site_source import scan_site
        try:
            name = (urlsplit(args.url).hostname or "site").replace(":", "-")
            out = Path(args.out) if args.out else Path.cwd() / f"{name}.site.ases"
            result = scan_site(args.url, out, max_pages=args.max_pages, allow_local=args.allow_local)
            observations = result["semantic_model"]["site_observations"]
            summary = {
                "source": observations["source_uri"], "mode": "LIVE_SITE", "output": result["output"],
                "pages": len(observations["pages"]),
                "forms": sum(len(page["forms"]) for page in observations["pages"]),
                "script_urls": len({script for page in observations["pages"] for script in page["scripts"]}),
                "framework_hints": [hint["name"] for hint in observations["framework_hints"]],
                "validation": result["validation"]["status"],
            }
            print(json.dumps(summary, indent=2) if args.json else "\n".join(f"{k}={v}" for k, v in summary.items()))
            return 0
        except (ValueError, RuntimeError) as exc:
            raise SystemExit(str(exc)) from exc

    if args.command == "scan":
        source = None
        try:
            source = resolve_source(args.source)
            if args.out:
                out = Path(args.out)
            elif source.is_remote:
                out = _default_remote_output(source.repo_name)
            else:
                out = default_output(source.root)

            result = scan_project(
                source.root,
                out,
                source_uri=source.display_source if source.is_remote else None
            )
            model = result["semantic_model"]
            finding_diff = None
            if args.baseline:
                finding_diff = diff_findings(load_findings(Path(args.baseline)), load_findings(Path(result["output"])))
                (Path(result["output"]) / "findings-diff.json").write_text(json.dumps(finding_diff, indent=2), encoding="utf-8")
                baseline_context = Path(args.baseline)
                if baseline_context.is_dir() or baseline_context.name in {"consumer-context.json", "consumer-context.v2.json"}:
                    semantic_delta = semantic_diff(load_context(baseline_context), load_context(Path(result["output"])))
                    (Path(result["output"]) / "semantic-diff.json").write_text(json.dumps(semantic_delta, indent=2), encoding="utf-8")
            summary = {
                "source": source.display_source,
                "remote": source.is_remote,
                "output": result["output"],
                "languages": model["project"]["languages"],
                "frameworks": model["project"]["frameworks"],
                "components": len(model["components"]),
                "behaviors": len(model["behaviors"]),
                "tests": len(model["tests"]),
                "assets": len(model["assets"]),
                "controls": len(model.get("controls",[])),
                "trust_boundaries": len(model["trust_boundaries"]),
                "observed_patterns": len([p for p in model.get("pattern_findings",[]) if p.get("status")=="OBSERVED"]),
                "pattern_opportunities": len(model.get("pattern_opportunities",[])),
                "pattern_hints": len(model.get("pattern_hints",[])),
                "frontend_findings": len(model.get("frontend_findings",[])),
                "frontend_components": len(model.get("frontend",{}).get("components",[])),
                "frontend_templates": len(model.get("frontend",{}).get("templates",[])),
                "frontend_services": len(model.get("frontend",{}).get("services",[])),
                "frontend_api_calls": len(model.get("frontend",{}).get("api_calls",[])),
                "frontend_route_declarations": len(model.get("frontend",{}).get("routes",[])),
                "cross_boundary_findings": len(model.get("cross_boundary_findings",[])),
                "source_roles": model.get("source_classification",{}).get("roles",{}),
                "trace_links": len(model["trace_links"]),
                "validation": result["validation"]["status"],
                "diff": finding_diff["summary"] if finding_diff else None,
            }
            print(json.dumps(summary, indent=2) if args.json else "\n".join(f"{k}={v}" for k,v in summary.items()))
            return 0
        except (ValueError, RuntimeError) as e:
            raise SystemExit(str(e))
        finally:
            if source is not None:
                source.cleanup()

    if args.command == "scan-artifact":
        from .artifacts import write_artifact
        document = write_artifact(Path(args.path), Path(args.out))
        print(json.dumps({"snapshot_id": document["snapshot_id"], "files": len(document["files"]), "coverage": document["coverage"]}, indent=2))
        return 0

    if args.command == "reconcile-artifact":
        from .artifacts import load_artifact, load_runtime, reconcile_artifact
        report = reconcile_artifact(load_context(Path(args.source)), load_artifact(args.artifact),
                                    load_runtime(args.runtime) if args.runtime else None,
                                    [json.loads(value) for value in args.mapping])
        if args.out:
            Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0

    if args.command == "trace":
        from .snapshot import trace_snapshot
        print(json.dumps(trace_snapshot(load_context(Path(args.path)), args.selector, direction=args.direction, max_nodes=args.max_nodes), indent=2))
        return 0

    if args.command == "inspect":
        p = Path(args.path)
        if p.suffix == ".json" or (p.is_dir() and (p / "consumer-context.v2.json").exists()):
            from .snapshot import inspect_snapshot
            print(json.dumps(inspect_snapshot(load_context(p), collection=args.collection, selector=args.select,
                                              offset=args.offset, limit=args.limit), indent=2))
            return 0
        if p.is_dir():
            p = p/"semantic-model.yaml"
        model = yaml.safe_load(p.read_text(encoding="utf-8"))
        print(json.dumps({
            "project": model.get("project"),
            "actors": [a["name"] for a in model.get("actors",[])],
            "behaviors": [b["name"] for b in model.get("behaviors",[])],
            "controls": [c.get("control_type") for c in model.get("controls",[])],
            "pattern_findings": model.get("pattern_findings",[]),
            "unknowns": [u["statement"] for u in model.get("unknowns",[])],
        }, indent=2))
        return 0

    if args.command == "audit":
        report = audit_project(Path(args.path))
        print(json.dumps(report, indent=2))
        return 0 if report["status"] in {"PASS","NO_BASELINE"} else 1

    if args.command == "diff":
        report = diff_findings(load_findings(Path(args.before)), load_findings(Path(args.after)))
        if args.out:
            Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0

    if args.command == "semantic-diff":
        report = semantic_diff(load_context(Path(args.before)), load_context(Path(args.after)))
        if args.out:
            Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0

    if args.command == "export":
        data = export_json(Path(args.path), Path(args.out), schema=args.schema)
        print(json.dumps({"output":args.out,"schema":data["schema"]}, indent=2))
        return 0


    if args.command == "clean":
        if args.all:
            targets = [p for p in Path.cwd().iterdir() if is_generated_output(p)]
            removed = [str(p) for p in targets if clean_output(p)]
            print(json.dumps({"removed": removed}, indent=2))
            return 0
        if not args.path:
            raise SystemExit("Provide an ASES output directory or use --all")
        removed = clean_output(Path(args.path))
        print(json.dumps({"removed": [str(Path(args.path).resolve())] if removed else []}, indent=2))
        return 0

    if args.command == "selfcheck":
        root = Path(args.path).resolve()
        report = selfcheck(root)
        print(json.dumps(report, indent=2))
        if args.clean:
            clean_output(root/".ases-selfcheck")
        return 0 if report["status"] == "PASS" else 1

    return 2
