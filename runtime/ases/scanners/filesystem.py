from __future__ import annotations
from pathlib import Path
from collections import Counter
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
    ".puml":"plantuml", ".plantuml":"plantuml", ".mmd":"mermaid",
    ".drawio":"drawio", ".wsd":"plantuml", ".html":"html", ".htm":"html"
}
IGNORE_DIRS = {
    ".git",".idea",".vscode","node_modules","target","build","dist",".next",
    "__pycache__",".gradle","vendor","coverage",".ases",".ases-selfcheck", ".venv",
    ".pytest_cache",".mypy_cache",".ruff_cache"
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

def iter_project_files(root: Path):
    root = root.absolute().resolve()
    patterns = _load_asesignore(root)
    for directory, dirs, names in os.walk(root, followlinks=False):
        base = Path(directory)
        # Prune excluded trees before walking; never traverse symlinks or junctions.
        dirs[:] = sorted(name for name in dirs if name not in IGNORE_DIRS
                         and not (base / name / ".ases-output").is_file()
                         and not (base / name).is_symlink()
                         and not (os.name == "nt" and (base / name).lstat().st_file_attributes & 1024))
        for name in sorted(names):
            p = base / name
            if p.is_symlink() or not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            if not _ignored(rel, patterns):
                yield p

def iter_owned_files(root: Path):
    """Runtime-analyzable project files only. Generated/vendor/tooling/docs never drive findings."""
    for p in iter_project_files(root):
        role = classify_source(p.relative_to(root).as_posix(), root)["role"]
        if role in {"OWNED_SOURCE", "TEST"}:
            yield p

def _doc_role(path: str) -> str:
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
        if any(k in name for k in keys):
            return role
    return "OTHER"

def scan_filesystem(root: Path) -> dict:
    files = list(iter_project_files(root))
    langs = Counter()
    build, docs, tests, configs, migrations = [], [], [], [], []
    doc_artifacts = []
    source_manifest = []

    for p in files:
        rel = p.relative_to(root).as_posix()
        ext = p.suffix.lower()
        source = classify_source(rel, root)
        if ext in CODE_EXTS and source["role"] in {"OWNED_SOURCE","TEST"}:
            langs[CODE_EXTS[ext]] += 1
        if source["role"] in {"OWNED_SOURCE", "TEST"} and (ext in CODE_EXTS or source["scope"] == "frontend" and ext in FRONTEND_INPUTS):
            source_manifest.append({"path":rel,"sha256":sha256_file(p),"language":CODE_EXTS.get(ext, FRONTEND_INPUTS.get(ext)),**source})
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

    role_counts=Counter(classify_source(p.relative_to(root).as_posix(), root)["role"] for p in files)
    scope_counts=Counter(classify_source(p.relative_to(root).as_posix(), root)["scope"] for p in files if classify_source(p.relative_to(root).as_posix(), root)["role"] in {"OWNED_SOURCE","TEST"})
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
    }
