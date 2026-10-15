from __future__ import annotations
from pathlib import Path
from .pipeline import scan_project

CAPABILITY_FILES = {
    "scanners/python.py": "scanner_python",
    "scanners/java.py": "scanner_java",
    "scanners/typescript.py": "scanner_typescript",
    "scanners/frontend.py": "scanner_frontend",
    "recovery/semantic.py": "semantic_model",
    "renderers/markdown.py": "documentation_renderer",
    "audit.py": "drift_audit",
    "export.py": "generic_export",
}

def selfcheck(root: Path) -> dict:
    result = scan_project(root, root / ".ases-selfcheck")
    graph = result["graph"]
    paths = {n.get("path","") for n in graph["nodes"]}
    observed_caps = {
        capability
        for suffix, capability in CAPABILITY_FILES.items()
        if any(path.endswith(suffix) for path in paths)
    }

    missing = sorted(set(CAPABILITY_FILES.values()) - observed_caps)
    return {
        "version":result["semantic_model"]["ases_version"],
        "observed_capabilities":sorted(observed_caps),
        "missing_capabilities":missing,
        "status":"PASS" if not missing else "FAIL",
    }
