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
    # '$' is a valid Java identifier character (and the whole identifier in
    # Vavr's utility type named '$'). Keep this declaration index aligned with
    # the Java grammar used for method bodies and API recovery.
    r'(?P<kind>class|interface|enum|record)\s+(?P<name>[A-Za-z_$][\w$]*)'
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

def _java_lexical_spans(text):
    """Return comment and literal spans without treating comment markers in strings as comments."""
    spans = []
    index = 0
    while index < len(text):
        if text.startswith("//", index):
            end = text.find("\n", index + 2)
            end = len(text) if end < 0 else end
            spans.append((index, end, "comment"))
            index = end
            continue
        if text.startswith("/*", index):
            close = text.find("*/", index + 2)
            end = len(text) if close < 0 else close + 2
            spans.append((index, end, "comment"))
            index = end
            continue
        if text.startswith('"""', index):
            end = index + 3
            while end < len(text):
                if text.startswith('"""', end):
                    slashes, cursor = 0, end - 1
                    while cursor >= index and text[cursor] == "\\":
                        slashes += 1
                        cursor -= 1
                    if slashes % 2 == 0:
                        end += 3
                        break
                end += 1
            spans.append((index, end, "literal"))
            index = end
            continue
        if text[index] in {"\"", "'"}:
            quote = text[index]
            end = index + 1
            while end < len(text):
                if text[end] == "\\":
                    end += 2
                    continue
                if text[end] == quote:
                    end += 1
                    break
                end += 1
            spans.append((index, min(end, len(text)), "literal"))
            index = end
            continue
        index += 1
    return spans

def _mask_java_comments(text, spans=None):
    spans = spans if spans is not None else _java_lexical_spans(text)
    chars = list(text)
    for start, end, kind in spans:
        if kind == "comment":
            for index in range(start, end):
                if chars[index] not in "\r\n":
                    chars[index] = " "
    return "".join(chars)

def _method_matches(text):
    # Keep offsets and line numbers intact while allowing declarations with a
    # trailing comment after an annotation (for example `@Override // note`).
    # Matching the original text misses the annotation and shifts declaration
    # identity to the following modifier line.
    spans = _java_lexical_spans(text)
    literals = [(start, end) for start, end, kind in spans if kind == "literal"]
    masked = _mask_java_comments(text, spans)
    def name_is_literal(match):
        offset = match.start("name")
        return any(start <= offset < end for start, end in literals)
    matches = {m.start("name"): m for m in METHOD_RE.finditer(masked) if not name_is_literal(m)}
    for match in JUNIT_METHOD_RE.finditer(masked):
        if name_is_literal(match):
            continue
        if any(name in TEST_ANN for name, _ in _anns(match.group("anns"))):
            matches[match.start("name")] = match
    yield from (match for _, match in sorted(matches.items()))


def scan_java(root: Path) -> FactGraph:
    graph = FactGraph()
    type_index = {}
    parsed_types = []

    for p in [p for p in iter_owned_files(root) if p.suffix == ".java"]:
        rel = p.relative_to(root).as_posix()
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            from .filesystem import source_unavailable
            source_unavailable(root,p,graph)
            continue
        pkg = PACKAGE_RE.search(text)
        pkg_name = pkg.group(1) if pkg else ""
        imports = IMPORT_RE.findall(text)
        non_code = [(m.start(), m.end()) for m in NON_CODE_RE.finditer(text)]

        for tm in TYPE_RE.finditer(text):
            # Prose such as "this class enforces limits" is not a declaration.
            if any(start <= tm.start("kind") < end for start, end in non_code):
                continue
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
            # Nested declarations are visited under their own parsed type.
            if body[:mm.start()].count("{") - body[:mm.start()].count("}") != 1:
                continue
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

    # Recover method bodies the regex inventory intentionally cannot assign:
    # implicit-public interface defaults, enum-constant bodies, and bounded
    # package-private methods declared in ordinary classes.
    from .java_syntax import parse as parse_java, walk as walk_java, field as java_field, text as java_text
    for p in [p for p in iter_owned_files(root) if p.suffix == ".java"]:
        rel = p.relative_to(root).as_posix()
        try:
            source = p.read_text(encoding="utf-8", errors="ignore")
            syntax = parse_java(source)
        except (OSError, ValueError):
            continue
        for declaration in (n for n in walk_java(syntax) if n.type == "method_declaration"):
            name_node = java_field(declaration, "name")
            name = java_text(name_node)
            if not name_node or not name:
                continue
            line = declaration.start_point.row + 1
            ancestors = []
            current = declaration.parent
            while current:
                if current.type in {"class_declaration", "interface_declaration", "enum_declaration", "record_declaration", "enum_constant"}:
                    ancestors.append(current)
                current = current.parent
            enum_constant = next((n for n in ancestors if n.type == "enum_constant"), None)
            owner_type = next((n for n in ancestors if n.type in {"class_declaration", "interface_declaration", "enum_declaration", "record_declaration"}), None)
            if not owner_type:
                continue
            owner_name = java_text(java_field(owner_type, "name"))
            package = PACKAGE_RE.search(source)
            package_name = package.group(1) if package else ""
            owner_id = f"type:{package_name + '.' if package_name else ''}{owner_name}"
            if owner_id not in {n.id for n in graph.nodes}:
                continue
            modifiers = java_text(next((c for c in declaration.named_children if c.type == "modifiers"), None))
            implicit_interface = owner_type.type == "interface_declaration" and "private" not in modifiers
            body_node = java_field(declaration, "body")
            modifier_node = next((c for c in declaration.named_children if c.type == "modifiers"), None)
            explicit_visibility = any(n.type in {"public", "protected", "private"}
                                      for n in walk_java(modifier_node)) if modifier_node else False
            package_private_class = (owner_type.type == "class_declaration" and body_node is not None
                                     and not explicit_visibility)
            if not enum_constant and not implicit_interface and not package_private_class:
                continue
            # Existing explicit declarations retain their legacy graph IDs.
            if any(n.kind == "method" and n.path == rel and n.name == name and f"{rel}:{line}" in n.provenance.evidence for n in graph.nodes):
                continue
            constant_name = java_text(java_field(enum_constant, "name")) if enum_constant else ""
            owner_chain = []
            for item in reversed(ancestors):
                if item.type in {"class_declaration", "interface_declaration", "enum_declaration", "record_declaration"}:
                    chain_name = java_text(java_field(item, "name"))
                    if chain_name:
                        owner_chain.append(chain_name)
            identity_owner = ".".join(owner_chain) if owner_chain else owner_name
            if enum_constant:
                identity_owner += f".{constant_name}"
            method_id = f"method:{package_name + '.' if package_name else ''}{identity_owner}#{name}:{line}"
            visibility = ("package-private" if package_private_class else "public" if implicit_interface else next(
                (value for value in ("private", "protected", "public") if value in modifiers), "undeclared"))
            graph.add_node(Node(method_id, "method", name, rel, {
                "owner": owner_id, "owner_chain": identity_owner, "visibility": visibility,
                "return_type": java_text(java_field(declaration, "type")),
                "params": java_text(java_field(declaration, "parameters")),
                "annotations": [], "is_test_code": _is_test_path(rel),
                "start_byte": declaration.start_byte, "end_byte": declaration.end_byte,
            }, Evidence(evidence=[f"{rel}:{line}"])))
            graph.add_edge(Edge(owner_id, method_id, "declares", [f"{rel}:{line}"]))

    return graph
