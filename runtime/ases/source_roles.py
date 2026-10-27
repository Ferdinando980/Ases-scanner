from __future__ import annotations
from pathlib import Path
import re

ROLES = {"OWNED_SOURCE","TEST","GENERATED","VENDORED","TOOLING","DOCUMENTATION","BUILD_ARTIFACT"}

_GENERATED_PARTS = {
    "jacoco","javadoc","surefire-reports","failsafe-reports","coverage-report",
    "coverage-reports","test-results","reports"
}
_VENDORED_PARTS = {"vendor","vendors","third_party","third-party"}
_TOOLING_PARTS = {".mvn","gradle/wrapper",".github/workflows"}
_BUILD_PARTS = {"target","build","dist","out",".next","coverage"}
_DOC_ROOTS = {"docs","documentation","documentazione","projectdocs","project-docs"}


def _extracted_vendor(parts):
    """Recognize an explicit vendor staging tree, not arbitrary vendor-like app names."""
    return (any(re.fullmatch(r'vendor[-_](?:update|cache|snapshot|download)s?', p) for p in parts)
            and 'extracted' in parts
            and any(re.search(r'(?:^|[-_])v?\d+\.\d+(?:\.\d+)?(?:$|[-_])',p) for p in parts))


def classify_source(path: str, root: Path | None = None) -> dict:
    rel = path.replace("\\","/").lstrip("/")
    low = rel.lower()
    parts = tuple(p.lower() for p in Path(rel).parts)
    name = Path(rel).name.lower()
    suffix = Path(rel).suffix.lower()

    if any(p in _BUILD_PARTS for p in parts):
        role = "BUILD_ARTIFACT"
    elif any(p in _TOOLING_PARTS for p in parts) or low.startswith((".mvn/",".github/workflows/")) or "gradle/wrapper/" in low:
        role = "TOOLING"
    elif any(p in _GENERATED_PARTS or p.startswith(("jacoco","javadoc")) for p in parts) or "/jacoco/" in f"/{low}" or "/javadoc/" in f"/{low}":
        role = "GENERATED"
    elif name.endswith((".min.js", ".min.css")) or _extracted_vendor(parts) or any(p in _VENDORED_PARTS for p in parts) or any(x in low for x in ("/static/js/lib/","/static/vendor/","/public/vendor/","/assets/vendor/")):
        role = "VENDORED"
    elif _is_test(low, name):
        role = "TEST"
    elif parts and parts[0] in _DOC_ROOTS:
        role = "DOCUMENTATION"
    else:
        role = "OWNED_SOURCE"

    scope = _scope(rel, role, suffix)
    if (root is not None and role in {"OWNED_SOURCE", "TEST"} and suffix in {".ts", ".js"}
            and low.startswith("src/app/") and (root / "angular.json").is_file()):
        scope = "frontend"
    return {"role": role, "scope": scope}


def _is_test(low: str, name: str) -> bool:
    if name.startswith('test_') and name.endswith('.py'):
        return True
    extension = Path(name).suffix
    if extension in {'.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx', '.mts', '.cts'} and name[:-len(extension)].endswith(('.test', '.spec')):
        return True
    return any(x in f"/{low}" for x in ("/src/test/","/test/","/tests/","/__tests__/")) or \
        name.endswith(("test.java","tests.java",".test.js",".test.ts",".spec.js",".spec.ts","_test.py"))


def _scope(rel: str, role: str, suffix: str) -> str:
    low = rel.lower()
    if role not in {"OWNED_SOURCE","TEST"}:
        return "non_runtime"
    if suffix in {".html",".htm",".jsp",".hbs",".ejs",".pug",".twig",".css",".scss",".sass",".vue",".svelte",".jsx",".tsx"}:
        return "frontend"
    if low.startswith(("frontend/","client/","web/","ui/")) or any(x in low for x in ("/templates/","/static/","/public/","/frontend/","/client/","/web/","/ui/")):
        return "frontend"
    if suffix in {".java",".kt",".py",".go",".rs",".cs",".php",".rb"}:
        return "backend"
    if suffix in {".js",".ts",".mjs",".cjs",".mts",".cts"} and any(x in low for x in ("controller","service","repository","server","api/","routes")):
        return "backend"
    return "shared"
