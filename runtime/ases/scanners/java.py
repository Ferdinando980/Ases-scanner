from __future__ import annotations
from pathlib import Path
import re
from .filesystem import iter_owned_files
from .common import balanced_block, line_of
from ..model import FactGraph, Node, Edge, Evidence

PACKAGE_RE = re.compile(r'^\s*package\s+([\w.]+)\s*;', re.M)
IMPORT_RE = re.compile(r'^\s*import\s+(?:static\s+)?([\w.*]+)\s*;', re.M)
ANNOT_RE = re.compile(r'@([A-Za-z_][\w.]*)\s*(?:\(([^)]*)\))?')
TYPE_RE = re.compile(
    r'(?P<anns>(?:@\w+(?:\([^)]*\))?\s*)*)'
    r'(?:(?:public|protected|private|abstract|final|static|sealed|non-sealed)\s+)*'
    r'(?P<kind>class|interface|enum|record)\s+(?P<name>[A-Za-z_]\w*)'
    r'(?:\s+extends\s+(?P<extends>[A-Za-z_][\w.<>?, ]*))?'
    r'(?:\s+implements\s+(?P<implements>[A-Za-z_][\w.<>?, ]*))?'
)
METHOD_RE = re.compile(
    r'(?P<anns>(?:@\w+(?:\([^)]*\))?\s*)*)'
    r'(?P<vis>public|protected|private)\s+'
    r'(?:(?:static|final|synchronized|abstract|default|native)\s+)*'
    r'(?P<ret>[\w<>\[\], ?.@]+)\s+'
    r'(?P<name>[A-Za-z_]\w*)\s*\((?P<params>[^)]*)\)'
)
JUNIT_METHOD_RE = re.compile(
    r'(?P<anns>(?:@[\w.]+(?:\([^)]*\))?\s*)+)'
    r'(?:(?P<vis>public|protected|private)\s+)?'
    r'(?:(?:final|synchronized|static)\s+)*'
    r'(?P<ret>void)\s+(?P<name>[A-Za-z_]\w*)\s*\((?P<params>[^)]*)\)'
)
NON_CODE_RE = re.compile(r'//[^\r\n]*|/\*.*?\*/|""".*?"""|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.S)
FIELD_RE = re.compile(
    r'(?m)^\s*(?:private|protected|public)\s+(?:final\s+|static\s+)*'
    r'(?P<type>[A-Za-z_][\w<>\[\], ?.]*?)\s+(?P<name>[A-Za-z_]\w*)\s*(?:=|;)'
)
CALL_RE = re.compile(r'\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*\(')

SPRING_TYPE_ANN = {
    "RestController":"controller","Controller":"controller","Service":"service",
    "Repository":"repository","Component":"component","Entity":"entity",
    "Configuration":"configuration", "SpringBootApplication":"application"
}
HTTP_ANN = {
    "GetMapping":"GET","PostMapping":"POST","PutMapping":"PUT","PatchMapping":"PATCH",
    "DeleteMapping":"DELETE","RequestMapping":"ANY"
}
TEST_ANN = {"Test","ParameterizedTest","RepeatedTest"}

def _anns(text):
    return [(m.group(1).split(".")[-1], m.group(2) or "") for m in ANNOT_RE.finditer(text or "")]

def _str_arg(raw):
    m = re.search(r'["\']([^"\']+)["\']', raw or "")
    return m.group(1) if m else ""

def _join(base, child):
    parts = [x.strip("/") for x in (base, child) if x and x.strip("/")]
    return "/" + "/".join(parts) if parts else "/"


def _is_test_path(rel: str) -> bool:
    low = rel.lower()
    return "/test/" in low or "src/test/" in low or "/tests/" in low or Path(rel).name.lower().endswith("test.java")

def _classify_plain_type(name: str, pkg_name: str, rel: str, ann_names: list[str], declared_kind: str, implements: str | None) -> str:
    if _is_test_path(rel):
        return "test_class"
    lname = name.lower()
    lpkg = pkg_name.lower()
    if "SpringBootApplication" in ann_names or lname.endswith("application"):
        return "application"
    if lname.endswith("dto") or ".dto" in lpkg or "/dto/" in rel.lower():
        return "dto"
    if lname.endswith("dao") or ".dao" in lpkg or "/dao/" in rel.lower():
        return "repository"
    if declared_kind == "interface" and (lname.endswith("repository") or ".repository" in lpkg or "/repository/" in rel.lower()):
        return "repository"
    if lname.endswith("service") or lname.endswith("serviceimpl") or ".service" in lpkg or "/service/" in rel.lower():
        return "service"
    if lname.endswith("factory"):
        return "factory"
    if implements and any(tok.strip().split("<")[0].endswith("State") for tok in implements.split(",")):
        return "state_implementation"
    if ".model" in lpkg or "/model/" in rel.lower():
        return "domain_object"
    return declared_kind

def _creation_targets(body: str) -> list[str]:
    return sorted(set(re.findall(r'\bnew\s+([A-Za-z_]\w*)\s*\(', body)))

def _method_matches(text):
    non_code = [(m.start(), m.end()) for m in NON_CODE_RE.finditer(text)]
    matches = {m.start("name"): m for m in METHOD_RE.finditer(text)}
    for match in JUNIT_METHOD_RE.finditer(text):
        if any(name in TEST_ANN for name, _ in _anns(match.group("anns"))):
            matches[match.start("name")] = match
    for _, match in sorted(matches.items()):
        if not any(start <= match.start() < end for start, end in non_code):
            yield match


def scan_java(root: Path) -> FactGraph:
    graph = FactGraph()
    type_index = {}
    parsed_types = []

    for p in [p for p in iter_owned_files(root) if p.suffix == ".java"]:
        rel = p.relative_to(root).as_posix()
        text = p.read_text(encoding="utf-8", errors="ignore")
        pkg = PACKAGE_RE.search(text)
        pkg_name = pkg.group(1) if pkg else ""
        imports = IMPORT_RE.findall(text)

        for tm in TYPE_RE.finditer(text):
            block = balanced_block(text, tm.end())
            if not block:
                continue
            bstart,bend = block
            body = text[bstart:bend]
            name = tm.group("name")
            fqcn = f"{pkg_name}.{name}" if pkg_name else name
            ann = _anns(tm.group("anns"))
            ann_names = [a for a,_ in ann]
            kind = next((SPRING_TYPE_ANN[a] for a in ann_names if a in SPRING_TYPE_ANN), None)
            if kind is None:
                kind = _classify_plain_type(name, pkg_name, rel, ann_names, tm.group("kind"), tm.group("implements"))
            nid = f"type:{fqcn}"
            ev = [f"{rel}:{line_of(text,tm.start())}"]
            graph.add_node(Node(nid,kind,name,rel,{
                "fqcn":fqcn,"java_kind":tm.group("kind"),"package":pkg_name,
                "annotations":ann_names,"extends":tm.group("extends"),
                "implements":tm.group("implements"),"imports":imports,
                "creation_targets": _creation_targets(body),
                "is_test_code": _is_test_path(rel),
            },Evidence(evidence=ev)))
            type_index[name] = nid
            parsed_types.append((nid,name,fqcn,rel,text,bstart,bend,body,ann))

        # tests not necessarily inside first class
        if "/test/" in rel.lower() or "src/test/" in rel.lower() or "test" in p.name.lower():
            for mm in _method_matches(text):
                if any(a in TEST_ANN for a,_ in _anns(mm.group("anns"))):
                    tid = f"test:{pkg_name}:{p.stem}#{mm.group('name')}:{line_of(text,mm.start())}"
                    graph.add_node(Node(tid,"test",mm.group("name"),rel,{"framework":"JUnit","test_method_name":mm.group("name"),"test_class":p.stem},Evidence(evidence=[f"{rel}:{line_of(text,mm.start())}"])))

    # second pass once type index is known
    for nid,name,fqcn,rel,text,bstart,bend,body,type_anns in parsed_types:
        base_route = ""
        for a,raw in type_anns:
            if a == "RequestMapping":
                base_route = _str_arg(raw)

        # fields / injection dependency map
        vars_to_type = {}
        for fm in FIELD_RE.finditer(body):
            typ = re.split(r'[<\[\], ?]', fm.group("type").strip())[0].split(".")[-1]
            vars_to_type[fm.group("name")] = typ
            if typ in type_index:
                graph.add_edge(Edge(nid,type_index[typ],"depends_on",[rel]))

        for mm in _method_matches(body):
            # only methods whose declaration begins at class top level approximately
            absolute = bstart + mm.start()
            method_name = mm.group("name")
            mid = f"method:{fqcn}#{method_name}:{line_of(text,absolute)}"
            anns = _anns(mm.group("anns"))
            mev = [f"{rel}:{line_of(text,absolute)}"]
            graph.add_node(Node(mid,"method",method_name,rel,{
                "owner":nid,"visibility":mm.group("vis") or "package-private",
                "return_type":" ".join(mm.group("ret").split()),
                "params":" ".join(mm.group("params").split()),
                "annotations":[a for a,_ in anns], "is_test_code": _is_test_path(rel),
            },Evidence(evidence=mev)))
            graph.add_edge(Edge(nid,mid,"declares",mev))

            # method body and calls
            mblock = balanced_block(body, mm.end())
            if mblock:
                ms,me = mblock
                mbody = body[ms:me]
                for cm in CALL_RE.finditer(mbody):
                    var, called = cm.group(1), cm.group(2)
                    typ = vars_to_type.get(var)
                    if typ and typ in type_index:
                        graph.add_edge(Edge(mid,type_index[typ],"calls_dependency",mev))
                        # method target is evidence-level, even if overload cannot be resolved
                        graph.add_edge(Edge(mid,f"method-name:{typ}#{called}","calls_method_name",mev))

            for a,raw in anns:
                if a in HTTP_ANN:
                    child = _str_arg(raw)
                    route = _join(base_route,child)
                    rid = f"route:{HTTP_ANN[a]}:{route}:{fqcn}#{method_name}"
                    graph.add_node(Node(rid,"route",f"{HTTP_ANN[a]} {route}",rel,{
                        "http_method":HTTP_ANN[a],"path":route,"handler":mid,"framework":"Spring"
                    },Evidence(evidence=mev)))
                    graph.add_edge(Edge(rid,mid,"handled_by",mev))

        ext = next((n.metadata.get("extends") for n in graph.nodes if n.id==nid), None)
        if ext:
            simple = re.split(r'[<,\s]',ext.strip())[0].split(".")[-1]
            if simple in type_index:
                graph.add_edge(Edge(nid,type_index[simple],"extends",[rel]))
        impl = next((n.metadata.get("implements") for n in graph.nodes if n.id==nid), None)
        if impl:
            for token in impl.split(","):
                simple = re.split(r'[<\s]',token.strip())[0].split(".")[-1]
                if simple in type_index:
                    graph.add_edge(Edge(nid,type_index[simple],"implements",[rel]))

    return graph
