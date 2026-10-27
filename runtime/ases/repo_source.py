from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
import shutil
import subprocess
import tempfile
import os

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

def resolve_source(value: str, *, timeout: float | None = None, interactive: bool = True,
                   checkout_parent: Path | None = None) -> ResolvedSource:
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

    tmp = tempfile.TemporaryDirectory(prefix="ases-clone-") if checkout_parent is None else None
    parent = Path(tmp.name) if tmp is not None else Path(checkout_parent)
    if tmp is None:
        parent.mkdir(parents=True, exist_ok=False)
    dest = parent / repo_name_from_url(value)

    command = ["git"]
    if not interactive:
        command += ["-c", "credential.helper=", "-c", "core.hooksPath=" + str(parent / "no-hooks")]
    command += ["clone", "--depth", "1", "--no-tags", value, str(dest)]
    try:
        proc = subprocess.run(command, text=True, capture_output=True, timeout=timeout,
                              env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"} if not interactive else None)
    except BaseException:
        if tmp is not None:
            tmp.cleanup()
        raise
    if proc.returncode != 0:
        if tmp is not None:
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
