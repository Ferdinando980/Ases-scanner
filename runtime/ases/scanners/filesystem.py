from __future__ import annotations
from pathlib import Path
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar
import os
from .common import sha256_file
from ..source_roles import classify_source

CODE_EXTS = {
    ".mjs":"JavaScript", ".cjs":"JavaScript", ".mts":"TypeScript", ".cts":"TypeScript",
    ".java":"Java", ".kt":"Kotlin", ".py":"Python", ".js":"JavaScript",
    ".ts":"TypeScript", ".tsx":"TypeScript", ".jsx":"JavaScript",
    ".go":"Go", ".rs":"Rust", ".cs":"C#", ".php":"PHP", ".rb":"Ruby",
    ".c":"C", ".cpp":"C++", ".h":"C/C++", ".swift":"Swift"
}
DOCUMENT_EXTS = {
    ".md":"markdown", ".rst":"rst", ".adoc":"asciidoc", ".txt":"text",
    ".pdf":"pdf", ".docx":"docx", ".doc":"doc", ".odt":"odt",
    ".xlsx":"xlsx", ".xls":"xls", ".ods":"ods",
    ".pptx":"pptx", ".ppt":"ppt",
    ".reqw":"reqview", ".arff":"arff",
    ".puml":"plantuml", ".plantuml":"plantuml", ".mmd":"mermaid",
    ".drawio":"drawio", ".wsd":"plantuml", ".html":"html", ".htm":"html"
}
IGNORE_DIRS = {
    ".git",".idea",".vscode","node_modules","target","build","dist",".next",
    "__pycache__",".gradle","vendor","coverage",".ases",".ases-selfcheck", ".venv",
    ".pytest_cache",".mypy_cache",".ruff_cache","site-packages","dist-packages"
}
BUILD_FILES = {
    "pom.xml":"Maven", "build.gradle":"Gradle", "build.gradle.kts":"Gradle",
    "package.json":"npm", "pyproject.toml":"Python", "requirements.txt":"Python",
    "go.mod":"Go", "Cargo.toml":"Rust"
}
FRONTEND_INPUTS = {".html": "HTML", ".htm": "HTML", ".jsp": "JSP", ".hbs": "Handlebars",
                   ".ejs": "EJS", ".pug": "Pug", ".twig": "Twig", ".vue": "Vue", ".svelte": "Svelte"}

def _load_asesignore(root: Path) -> list[str]:
    p = root / ".asesignore"
    if not p.exists():
        return []
    patterns = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            patterns.append(s.replace("\\","/"))
    return patterns

def _ignored(rel: str, patterns: list[str]) -> bool:
    import fnmatch
    rel = rel.replace("\\","/")
    for pat in patterns:
        p = pat.lstrip("/")
        if fnmatch.fnmatch(rel, p) or fnmatch.fnmatch("/"+rel, pat):
            return True
        if p.endswith("/") and rel.startswith(p):
            return True
    return False

FILESYSTEM_PROFILE = "project-files/4"
_catalog = ContextVar("ases_source_catalog", default=None)


@contextmanager
def source_catalog(root: Path, *, exclusions=(), limits=None):
    """One inventory per scan; no cache survives into a later project state."""
    token = _catalog.set({"root": root.absolute().resolve(), "files": None, "excluded": [], "roles": {},
                          "patterns": tuple(exclusions), "limits": limits, "unavailable": []})
    try:
        yield
    finally:
        _catalog.reset(token)


def source_unavailable(root, path, graph=None):
    relative = path.relative_to(root).as_posix()
    row = {'path':relative,'reason':'source_unavailable_during_scan','state':'UNKNOWN'}
    catalog = _catalog.get()
    if catalog is not None and catalog['root'] == root.absolute().resolve() and row not in catalog['unavailable']:
        catalog['unavailable'].append(row)
    if graph is not None:
        if row not in graph.unknowns: graph.unknowns.append(row)
        graph.coverage[relative] = {'status':'UNKNOWN','basis':'source unavailable during scan','omitted_count':None}


def unavailable_sources(root):
    catalog = _catalog.get()
    return list(catalog['unavailable']) if catalog is not None and catalog['root']==root.absolute().resolve() else []


def _excluded_directory(path: Path, root: Path, patterns: list[str]):
    relative = path.relative_to(root).as_posix()
    if path.name in IGNORE_DIRS:
        return "default-directory"
    if path.is_symlink() or (os.name == "nt" and path.lstat().st_file_attributes & 1024):
        return "linked-directory"
    if (path / "pyvenv.cfg").is_file() or (path / "conda-meta" / "history").is_file():
        return "python-environment"
    if (path / ".ases-output").is_file():
        return "generated-ases-output"
    if _ignored(relative, patterns) or _ignored(relative + "/", patterns):
        return "asesignore"
    return None


def iter_project_files(root: Path, *, excluded: list | None = None):
    root = root.absolute().resolve()
    catalog = _catalog.get()
    if catalog is not None and catalog["root"] == root:
        if catalog["files"] is None:
            catalog["files"] = list(_walk_project_files(root, excluded=catalog["excluded"]))
            if catalog["limits"]:
                count = total = 0
                limits = catalog["limits"]
                for path in catalog["files"]:
                    if path.suffix.lower() not in CODE_EXTS.keys() | FRONTEND_INPUTS.keys():
                        continue
                    relative = path.relative_to(root).as_posix()
                    source = classify_source(relative, root)
                    catalog["roles"][relative] = source
                    if source["role"] not in {"OWNED_SOURCE", "TEST"}:
                        continue
                    try:
                        size = path.stat().st_size
                    except OSError:
                        source_unavailable(root,path)
                        continue
                    count += 1
                    total += size
                    if count > limits["files"] or total > limits["bytes"] or size > limits["file_bytes"]:
                        raise ValueError("UI_SCOPE_LIMIT: source scope exceeds 5000 files, 128 MiB total or 2 MiB per file. Add exclusions or use the CLI for a larger intentional scan.")
        if excluded is not None:
            excluded.extend(catalog["excluded"])
        for path in catalog["files"]:
            try:
                available = path.is_file() and not path.is_symlink()
            except OSError:
                available = False
            if available:
                yield path
            else:
                source_unavailable(root,path)
    else:
        yield from _walk_project_files(root, excluded=excluded)


def _walk_project_files(root: Path, *, excluded=None):
    root = root.absolute().resolve()
    patterns = _load_asesignore(root)
    catalog = _catalog.get()
    if catalog is not None and catalog["root"] == root:
        patterns += list(catalog["patterns"])
    def unavailable_directory(error):
        if error.filename:
            source_unavailable(root,Path(error.filename))
    for directory, dirs, names in os.walk(root, followlinks=False, onerror=unavailable_directory):
        base = Path(directory)
        # Prune excluded trees before walking; never traverse symlinks or junctions.
        admitted = []
        for name in sorted(dirs):
            try:
                reason = _excluded_directory(base / name, root, patterns)
            except OSError:
                source_unavailable(root,base/name)
                reason = 'unavailable-directory'
            if reason:
                if excluded is not None:
                    excluded.append({"path": (base / name).relative_to(root).as_posix(), "reason": reason})
            else:
                admitted.append(name)
        dirs[:] = admitted
        for name in sorted(names):
            p = base / name
            try:
                if p.is_symlink():
                    continue
                available = p.is_file()
            except OSError:
                available = False
            if not available:
                source_unavailable(root,p)
                continue
            rel = p.relative_to(root).as_posix()
            if not _ignored(rel, patterns):
                yield p

def iter_owned_files(root: Path):
    """Runtime-analyzable project files only. Generated/vendor/tooling/docs never drive findings."""
    root = root.absolute().resolve()
    catalog = _catalog.get()
    roles = catalog["roles"] if catalog is not None and catalog["root"] == root else {}
    for p in iter_project_files(root):
        relative = p.relative_to(root).as_posix()
        if relative not in roles:
            roles[relative] = classify_source(relative, root)
        role = roles[relative]["role"]
        if role in {"OWNED_SOURCE", "TEST"}:
            yield p

def _doc_role(path: str) -> str:
    import re
    name = Path(path).name.lower()
    tokens = {
        "SOW": ("statement of work","sow"),
        "RAD": ("rad","requirements analysis"),
        "SDD": ("sdd","system design"),
        "ODD": ("odd","object design"),
        "TP": ("test plan","tp"),
        "TCS": ("test case","tcs"),
        "TIR": ("test incident","tir"),
        "TSR": ("test summary","tsr"),
        "TRACEABILITY": ("tracciabil","traceability"),
        "README": ("readme",),
    }
    for role, keys in tokens.items():
        if any(re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", name) if len(k) <= 3 else k in name for k in keys):
            return role
    return "OTHER"

def scan_filesystem(root: Path) -> dict:
    root = root.absolute().resolve()
    excluded = []
    files = list(iter_project_files(root, excluded=excluded))
    langs = Counter()
    build, docs, tests, configs, migrations = [], [], [], [], []
    doc_artifacts = []
    source_manifest = []
    role_counts, scope_counts = Counter(), Counter()
    catalog = _catalog.get()

    for p in files:
        rel = p.relative_to(root).as_posix()
        ext = p.suffix.lower()
        source = (catalog["roles"].get(rel) if catalog is not None and catalog["root"] == root else None) or classify_source(rel, root)
        if catalog is not None and catalog["root"] == root:
            catalog["roles"][rel] = source
        role_counts[source["role"]] += 1
        if source["role"] in {"OWNED_SOURCE", "TEST"}:
            scope_counts[source["scope"]] += 1
        if ext in CODE_EXTS and source["role"] in {"OWNED_SOURCE","TEST"}:
            langs[CODE_EXTS[ext]] += 1
        if source["role"] in {"OWNED_SOURCE", "TEST"} and (ext in CODE_EXTS or source["scope"] == "frontend" and ext in FRONTEND_INPUTS):
            try:
                source_manifest.append({"path":rel,"sha256":sha256_file(p),"language":CODE_EXTS.get(ext, FRONTEND_INPUTS.get(ext)),**source})
            except OSError:
                source_unavailable(root,p)
        if p.name in BUILD_FILES:
            build.append({"path":rel, "tool":BUILD_FILES[p.name]})
        low = rel.lower()

        if (ext in DOCUMENT_EXTS or p.name.lower().startswith("readme")) and source["role"] in {"DOCUMENTATION","OWNED_SOURCE"}:
            docs.append(rel)
            doc_artifacts.append({
                "path": rel,
                "format": DOCUMENT_EXTS.get(ext, "text"),
                "role": _doc_role(rel),
                "source_role": source["role"],
                "parse_status": "DISCOVERED",
            })

        if source["role"] == "TEST":
            tests.append(rel)
        if ext in {".yml",".yaml",".toml",".json",".properties",".env",".xml"}:
            configs.append(rel)
        if "migration" in low or "/db/migrate" in low or "/migrations/" in low:
            migrations.append(rel)

    return {
        "root": str(root),
        "source_roles": dict(sorted(role_counts.items())),
        "source_scopes": dict(sorted(scope_counts.items())),
        "file_count": len(files),
        "languages": [{"name":k,"files":v} for k,v in langs.most_common()],
        "build_tools": sorted(build, key=lambda x:x["path"]),
        "documentation": sorted(set(docs)),
        "documentation_artifacts": sorted(doc_artifacts, key=lambda x:x["path"]),
        "tests": sorted(set(tests)),
        "configs": sorted(set(configs)),
        "migrations": sorted(set(migrations)),
        "source_manifest": sorted(source_manifest, key=lambda x:x["path"]),
        "source_scope": {"policy": FILESYSTEM_PROFILE, "excluded_directories": excluded,
                         "unavailable_files": unavailable_sources(root),
                         "user_exclusions": list(catalog["patterns"]) if catalog is not None else [],
                         "meaning": "Excluded directories are outside this scan; absence inside them is not assessed."},
    }
