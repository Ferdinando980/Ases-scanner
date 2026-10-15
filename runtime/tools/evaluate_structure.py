"""Small independent structural oracle and opt-in local performance samples. No target execution."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import time
import tracemalloc

from ases.pipeline import scan_project
from ases.scanners.javascript import scan_javascript
from ases.semantic_diff import load_context, semantic_diff
from ases.recovery.paths import recover_sensitive_paths

SOURCES = {
    "repo.mjs": "export function read() { return fetch('https://example.test/users'); }",
    "other.mjs": "export function read() { return 2; }",
    "server.mjs": """import {read as get} from './repo.mjs';
export function handler() { return get(); }
export function shadow(get) { return get(); }
app.get('/users', handler);
// app.get('/fake', handler); get();
const description = "app.get('/also-fake', handler)";
""",
    "types.ts": "import type {read} from './other.mjs'; function typed() { return read(); }",
}
PRESENT = {
    ("calls", "server.mjs", "handler", "repo.mjs", "read"),
    ("handled_by", "server.mjs", "GET /users", "server.mjs", "handler"),
    ("calls", "repo.mjs", "read", "repo.mjs", "GET https://example.test/users"),
}
PRESENT_ENTITIES = {
    ("function", "read", "repo.mjs"), ("function", "read", "other.mjs"),
    ("function", "handler", "server.mjs"), ("function", "shadow", "server.mjs"),
    ("function", "typed", "types.ts"), ("route", "GET /users", "server.mjs"),
    ("external_api_call", "GET https://example.test/users", "repo.mjs"),
}
ABSENT_ENTITIES = {("route", "GET /fake", "server.mjs"), ("route", "GET /also-fake", "server.mjs"),
                   ("function", "get", "server.mjs")}
USER_PATH = ("GET /users", "handler", "read", "GET https://example.test/users")
ABSENT_PATHS = {("GET /fake", *USER_PATH[1:]), ("GET /also-fake", *USER_PATH[1:]),
                ("GET /users", "handler", "shadow", USER_PATH[-1])}
ABSENT = {
    ("calls", "server.mjs", "handler", "other.mjs", "read"),
    ("calls", "server.mjs", "shadow", "repo.mjs", "read"),
    ("calls", "types.ts", "typed", "other.mjs", "read"),
    ("handled_by", "server.mjs", "GET /fake", "server.mjs", "handler"),
    ("handled_by", "server.mjs", "GET /also-fake", "server.mjs", "handler"),
}


def structural_oracle(directory):
    directory.mkdir(parents=True, exist_ok=True)
    for name, content in SOURCES.items():
        (directory / name).write_text(content)
    graph = scan_javascript(directory)
    nodes = {node.id: node for node in graph.nodes}
    actual = {(edge.relation, nodes[edge.source].path, nodes[edge.source].name,
               nodes[edge.target].path, nodes[edge.target].name)
              for edge in graph.edges if edge.source in nodes and edge.target in nodes}
    tp, fp, fn, tn = len(PRESENT & actual), len(ABSENT & actual), len(PRESENT - actual), len(ABSENT - actual)
    result = {"labelled_positive": len(PRESENT), "labelled_negative": len(ABSENT),
            "true_positive": tp, "false_positive": fp, "false_negative": fn, "true_negative": tn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "unassessed_relation_count": len(actual - PRESENT - ABSENT),
            "limitations": ["Eight explicitly labelled relations in a synthetic module/alias/shadowing corpus; not universal recall."]}
    actual_entities = {(node.kind, node.name, node.path) for node in graph.nodes}
    result["entities"] = {"true_positive": len(PRESENT_ENTITIES & actual_entities), "false_positive": len(ABSENT_ENTITIES & actual_entities),
                          "false_negative": len(PRESENT_ENTITIES - actual_entities), "true_negative": len(ABSENT_ENTITIES - actual_entities),
                          "unassessed": len(actual_entities - PRESENT_ENTITIES - ABSENT_ENTITIES)}
    actual_paths = {tuple(nodes[nid].name for nid in path["nodes"]) for path in recover_sensitive_paths(graph)}
    result["paths"] = {"true_positive": int(USER_PATH in actual_paths), "false_positive": len(actual_paths - {USER_PATH}),
                       "false_negative": int(USER_PATH not in actual_paths), "true_negative": len(ABSENT_PATHS - actual_paths),
                       "limitations": ["One supported user-read path and three labelled wrong paths; no general path recall estimate."]}
    before_out, after_out = directory.parent / "oracle-before.ases", directory.parent / "oracle-after.ases"
    scan_project(directory, before_out)
    before = load_context(before_out)
    for name, content in SOURCES.items():
        (directory / name).write_text("\n// harmless position change\n" + content.replace("{ return", "{\n  return").replace("; }", ";\n}"))
    scan_project(directory, after_out)
    after = load_context(after_out)
    old_ids, new_ids = ({row["id"] for row in snapshot["entities"]} for snapshot in (before, after))
    old_paths, new_paths = ({row["id"] for row in snapshot["sensitive_paths"]} for snapshot in (before, after))
    result["identity"] = {"entities_before": len(old_ids), "entities_after": len(new_ids), "stable_entities": len(old_ids & new_ids),
                          "paths_before": len(old_paths), "paths_after": len(new_paths), "stable_paths": len(old_paths & new_paths)}
    delta = semantic_diff(before, after)
    result["formatting_diff"] = {"summary": delta["summary"], "uncertain_count": len(delta["uncertain"]),
                                 "evidence_changed": delta["evidence_changed"], "analysis_profile_changed": delta["analysis_profile_changed"]}
    result["checks_passed"] = not any((fp, fn, result["entities"]["false_positive"], result["entities"]["false_negative"],
                                       result["paths"]["false_positive"], result["paths"]["false_negative"], old_ids != new_ids,
                                       old_paths != new_paths, any(delta["summary"].values()), delta["uncertain"]))
    return result


def sample(path, out):
    tracemalloc.start()
    start = time.perf_counter()
    scan_project(path, out)
    duration = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    context = load_context(out)
    return {"project": path.name, "seconds": round(duration, 3), "python_peak_mib": round(peak / 1024**2, 2),
            "entities": len(context["entities"]), "relations": len(context["structural_relations"]),
            "unknowns": len(context["analysis_unknowns"]), "snapshot_bytes": (out / "consumer-context.v2.json").stat().st_size,
            "file_coverage": {status: sum(row.get("status") == status for row in context["coverage"]["files"].values())
                              for status in ("ANALYZED", "PARTIAL", "UNKNOWN")},
            "limitations": ["Python allocation peak excludes native parser allocations; real-project truth is not fully annotated."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", action="append", default=[])
    parser.add_argument("--out", type=Path)
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="ases-structure-") as temp:
        root = Path(temp)
        result = {"schema": "ases-structural-evaluation/1.0", "oracle": structural_oracle(root / "oracle"),
                  "samples": [sample(Path(path).absolute().resolve(), root / f"sample-{i}.ases") for i, path in enumerate(arguments.project)]}
    encoded = json.dumps(result, indent=2)
    if arguments.out:
        arguments.out.write_text(encoded, encoding="utf-8")
    print(encoded)
    return 0 if result["oracle"]["checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
