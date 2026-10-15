from __future__ import annotations
from pathlib import Path
import hashlib

def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def balanced_block(text: str, open_pos: int, open_char: str="{", close_char: str="}") -> tuple[int,int] | None:
    """
    Conservative brace matcher that ignores braces in strings/comments enough for scanner use.
    open_pos must point at or before the first opening brace.
    Returns [start,end) bounds of the block including braces.
    """
    i = text.find(open_char, open_pos)
    if i < 0:
        return None
    depth = 0
    state = "code"
    quote = None
    j = i
    while j < len(text):
        ch = text[j]
        nxt = text[j+1] if j+1 < len(text) else ""
        if state == "code":
            if ch == "/" and nxt == "/":
                state = "line_comment"; j += 2; continue
            if ch == "/" and nxt == "*":
                state = "block_comment"; j += 2; continue
            if ch in ("'", '"', "`"):
                state = "string"; quote = ch; j += 1; continue
            if ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    return (i, j+1)
        elif state == "line_comment":
            if ch == "\n":
                state = "code"
        elif state == "block_comment":
            if ch == "*" and nxt == "/":
                state = "code"; j += 2; continue
        elif state == "string":
            if ch == "\\":
                j += 2; continue
            if ch == quote:
                state = "code"; quote = None
        j += 1
    return None
