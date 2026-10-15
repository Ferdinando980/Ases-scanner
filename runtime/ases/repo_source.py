from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
import shutil
import subprocess
import tempfile

@dataclass
class ResolvedSource:
    root: Path
    display_source: str
    is_remote: bool
    repo_name: str
    _tmp: tempfile.TemporaryDirectory | None = None

    def cleanup(self):
        if self._tmp is not None:
            self._tmp.cleanup()
            self._tmp = None

def is_git_url(value: str) -> bool:
    return value.strip().startswith(("https://", "http://", "ssh://", "git@", "file://"))

def repo_name_from_url(url: str) -> str:
    if url.startswith("git@"):
        tail = url.split(":", 1)[-1]
    else:
        tail = urlparse(url).path
    name = Path(tail.rstrip("/")).name
    if name.endswith(".git"):
        name = name[:-4]
    return name or "repository"

def resolve_source(value: str) -> ResolvedSource:
    if not is_git_url(value):
        root = Path(value).expanduser().absolute().resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"Not a directory: {root}")
        return ResolvedSource(
            root=root,
            display_source=str(root),
            is_remote=False,
            repo_name=root.name,
        )

    if shutil.which("git") is None:
        raise RuntimeError("Git is required to scan a repository URL, but 'git' was not found in PATH.")

    tmp = tempfile.TemporaryDirectory(prefix="ases-clone-")
    dest = Path(tmp.name) / repo_name_from_url(value)

    proc = subprocess.run(
        ["git", "clone", "--depth", "1", "--no-tags", value, str(dest)],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        tmp.cleanup()
        detail = (proc.stderr or proc.stdout or "git clone failed").strip()
        raise RuntimeError(f"Unable to clone repository: {detail}")

    return ResolvedSource(
        root=dest.resolve(),
        display_source=value,
        is_remote=True,
        repo_name=repo_name_from_url(value),
        _tmp=tmp,
    )
