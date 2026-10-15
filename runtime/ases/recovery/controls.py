from __future__ import annotations
from pathlib import Path
import re
from ..model import FactGraph, Node, Edge, Evidence
from ..scanners.filesystem import iter_owned_files
from ..scanners.common import line_of

RULES = [
    ("authentication", re.compile(r'@(PreAuthorize|Secured|RolesAllowed|Authenticated|UseGuards|Auth|Authorize|login_required)\b')),
    ("authorization", re.compile(r'(hasRole|hasAuthority|permission_required|roles?\s*[:=]|authorize\b)', re.I)),
    ("validation", re.compile(r'@(Valid|Validated|NotNull|NotBlank|Size|Min|Max|IsEmail|IsString|IsInt)\b')),
    ("validation", re.compile(r'\b(schema\.parse|safeParse|validator\b|validate\w*\s*\()', re.I)),
    ("rate_limit", re.compile(r'\b(rate.?limit|throttl)', re.I)),
]

SESSION_RULES = [
    ("session_read", re.compile(r'\b(getSession|getAttribute|sessionStorage\.getItem|localStorage\.getItem|SessionUtil\b)', re.I)),
    ("session_write", re.compile(r'\b(setAttribute|sessionStorage\.setItem|localStorage\.setItem)\b', re.I)),
    ("session_invalidate", re.compile(r'\b(invalidate\s*\(|removeAttribute|sessionStorage\.removeItem|localStorage\.removeItem)\b', re.I)),
]

def _layer(rel: str) -> str:
    low=rel.lower()
    if any(x in low for x in ("/static/","/public/","/frontend/","/client/","/webapp/")):
        return "CLIENT"
    if any(x in low for x in ("/src/main/java/","/server/","/backend/","/api/")) or rel.endswith(".java") or rel.endswith(".py"):
        return "SERVER"
    return "UNKNOWN"

def recover_controls(root: Path, graph: FactGraph) -> FactGraph:
    for p in iter_owned_files(root):
        if p.suffix.lower() not in {".java",".kt",".ts",".tsx",".js",".jsx",".mjs",".cjs",".mts",".cts",".py"}:
            continue
        rel=p.relative_to(root).as_posix()
        is_js = p.suffix.lower() in {".ts",".tsx",".js",".jsx",".mjs",".cjs",".mts",".cts"}
        if is_js:
            from ..scanners.javascript import MAX_BYTES
            if p.stat().st_size > MAX_BYTES:
                continue  # The parser's UNKNOWN coverage already records the limit.
        # AST ranges use the original UTF-8 bytes, including CRLF line endings.
        try:
            text=p.read_bytes().decode("utf-8",errors="strict" if is_js else "ignore")
        except UnicodeError:
            continue
        if is_js:
            from ..scanners.javascript import syntax_text
            try:
                text = syntax_text(text, p.suffix.lower(), remove_strings=True)
            except ValueError:
                continue
        local_targets=[n for n in graph.nodes if n.path==rel and n.kind in {"route","method","function","controller","service"}]

        for ctype,rx in RULES:
            for i,m in enumerate(rx.finditer(text)):
                line=line_of(text,m.start())
                cid=f"control:{ctype}:{rel}:{line}:{i}"
                ev=[f"{rel}:{line}"]
                graph.add_node(Node(
                    cid,"control",m.group(0)[:100],rel,
                    {"control_type":ctype,"line":line,"enforcement_layer":_layer(rel)},
                    Evidence(evidence=ev)
                ))
                target=_scope_target(local_targets,text,m.start()) if is_js else _nearest_target(local_targets,line)
                control = next(n for n in graph.nodes if n.id == cid)
                control.metadata["scope_basis"] = "lexical-callable" if is_js and target else "unknown" if is_js else "nearest-declaration-heuristic"
                if target:
                    graph.add_edge(Edge(cid,target.id,"protects_or_validates",ev,{"basis": control.metadata["scope_basis"]}))

        for stype,rx in SESSION_RULES:
            for i,m in enumerate(rx.finditer(text)):
                line=line_of(text,m.start())
                sid=f"session:{stype}:{rel}:{line}:{i}"
                ev=[f"{rel}:{line}"]
                graph.add_node(Node(
                    sid,"session_operation",m.group(0)[:100],rel,
                    {"operation":stype,"line":line,"enforcement_layer":_layer(rel)},
                    Evidence(evidence=ev)
                ))
                target=_scope_target(local_targets,text,m.start()) if is_js else _nearest_target(local_targets,line)
                if target:
                    graph.add_edge(Edge(sid,target.id,"session_affects",ev))
    return graph


def _scope_target(targets, text, position):
    offset = len(text[:position].encode("utf-8"))
    candidates = [n for n in targets if n.metadata.get("start_byte", -1) <= offset < n.metadata.get("end_byte", -1)]
    return min(candidates, key=lambda n: n.metadata["end_byte"] - n.metadata["start_byte"]) if candidates else None

def _nearest_target(targets, line):
    scored=[]
    for t in targets:
        tline=_node_line(t)
        if tline is not None:
            scored.append((abs(tline-line), tline < line, t))
    if not scored:
        return None
    scored.sort(key=lambda x:(x[0],x[1]))
    return scored[0][2]

def _node_line(node):
    for ev in node.provenance.evidence:
        if ":" in ev:
            try: return int(ev.rsplit(":",1)[1])
            except ValueError: pass
    return None
