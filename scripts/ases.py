#!/usr/bin/env python3
"""Tiny deterministic companion for ASES v0.2.

The LLM/agent remains the reasoner. This script only performs lightweight
classification hints and repository checks without external dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


FORMAL_TERMS = {
    "architecture", "architectural", "subsystem", "auth", "authentication",
    "authorization", "security", "migration", "schema", "database migration",
    "concurrency", "deployment", "breaking api", "public api", "persistence",
}

BUG_TERMS = {"bug", "fix", "broken", "crash", "regression", "error", "incorrect"}
REFACTOR_TERMS = {"refactor", "cleanup", "restructure", "rename", "simplify"}
DOC_TERMS = {"docs", "documentation", "readme", "document"}
TEST_TERMS = {"test", "testing", "coverage", "tcs", "tir", "tsr", "test plan"}


def classify(text: str) -> dict:
    t = text.lower()
    classification = "FEATURE"
    if any(x in t for x in BUG_TERMS):
        classification = "BUGFIX"
    elif any(x in t for x in REFACTOR_TERMS):
        classification = "REFACTOR"
    elif any(x in t for x in DOC_TERMS) and not any(x in t for x in BUG_TERMS):
        classification = "DOCUMENTATION"
    elif any(x in t for x in TEST_TERMS) and not any(x in t for x in BUG_TERMS):
        classification = "TESTING"

    rigor = "LEAN" if classification in {"BUGFIX", "REFACTOR", "DOCUMENTATION", "TESTING"} else "STANDARD"
    reasons = []
    hits = sorted(x for x in FORMAL_TERMS if x in t)
    if hits:
        rigor = "FORMAL"
        reasons.append("formal escalation trigger(s): " + ", ".join(hits))
    elif classification == "FEATURE":
        reasons.append("externally visible/new behavior assumed")
    else:
        reasons.append("local/specialized task by default")

    return {"classification": classification, "rigor": rigor, "reasons": reasons}


def check_repo(root: Path) -> dict:
    issues = []
    warnings = []

    ases = root / ".ases"
    if not ases.exists():
        # Also support running inside the standard package itself.
        if (root / "STANDARD.md").exists() and (root / "GATES.md").exists():
            ases = root
        else:
            issues.append("ASES directory not found (.ases/) and no local STANDARD.md/GATES.md detected")
            return {"ok": False, "issues": issues, "warnings": warnings}

    required = [
        "STANDARD.md",
        "GATES.md",
        "orchestrator/TASK-ROUTER.md",
        "skills/simplicity-gate/SKILL.md",
        "skills/consistency-auditor/SKILL.md",
    ]
    for rel in required:
        if not (ases / rel).exists():
            issues.append(f"missing required ASES file: {rel}")

    trace_candidates = [
        root / "docs" / "traceability.yaml",
        root / "docs" / "traceability.yml",
        ases / "schemas" / "traceability.yaml",
    ]
    if not any(p.exists() for p in trace_candidates):
        warnings.append("no traceability YAML found; acceptable for LEAN projects, expected for projects using traceability")

    # Cheap stale-marker scan, intentionally conservative.
    stale_re = re.compile(r"\b(TODO|FIXME|STALE_DOC|BROKEN_TRACE)\b")
    scanned = 0
    for base in [root / "docs", ases]:
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and p.suffix.lower() in {".md", ".yaml", ".yml", ".json"}:
                try:
                    txt = p.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                scanned += 1
                if stale_re.search(txt):
                    warnings.append(f"review marker found: {p.relative_to(root)}")

    return {"ok": not issues, "issues": issues, "warnings": warnings, "files_scanned": scanned}


def main() -> int:
    parser = argparse.ArgumentParser(prog="ases", description="ASES v0.2 helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_class = sub.add_parser("classify", help="give a deterministic task classification hint")
    p_class.add_argument("task", nargs="+", help="task description")

    p_check = sub.add_parser("check", help="lightweight ASES repository consistency check")
    p_check.add_argument("root", nargs="?", default=".")

    args = parser.parse_args()

    if args.cmd == "classify":
        print(json.dumps(classify(" ".join(args.task)), indent=2))
        return 0

    if args.cmd == "check":
        result = check_repo(Path(args.root).resolve())
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
