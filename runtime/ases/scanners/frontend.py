from __future__ import annotations
from pathlib import Path
import re
import os
from .filesystem import iter_owned_files
from .filesystem import FRONTEND_INPUTS
from .common import line_of
from ..source_roles import classify_source
from ..model import FactGraph, Node, Edge, Evidence

SCRIPT_EXTS={'.js','.jsx','.mjs','.cjs','.ts','.tsx','.mts','.cts','.vue','.svelte'}
TEMPLATE_EXTS=set(FRONTEND_INPUTS) - {'.vue', '.svelte'}


def scan_frontend(root: Path) -> FactGraph:
    root = root.absolute().resolve()
    graph=FactGraph(); modules={}; records=[]
    for p in iter_owned_files(root):
        rel=p.relative_to(root).as_posix(); meta=classify_source(rel, root)
        if meta['scope']!='frontend' or meta['role']!='OWNED_SOURCE': continue
        ext=p.suffix.lower()
        if ext not in SCRIPT_EXTS|TEMPLATE_EXTS: continue
        try:
            if ext in SCRIPT_EXTS:
                from .javascript import MAX_BYTES
                if p.stat().st_size > MAX_BYTES:
                    graph.coverage[rel] = {'status': 'UNKNOWN', 'basis': 'source_byte_limit', 'omitted_count': None}
                    graph.unknowns.append({'path': rel, 'reason': 'source_byte_limit', 'state': 'UNKNOWN'})
                    continue
            text=p.read_bytes().decode('utf-8',errors='strict' if ext in SCRIPT_EXTS else 'ignore')
        except OSError:
            from .filesystem import source_unavailable
            source_unavailable(root,p,graph)
            continue
        except UnicodeError:
            graph.coverage[rel] = {'status': 'UNKNOWN', 'basis': 'invalid_utf8', 'omitted_count': None}
            graph.unknowns.append({'path': rel, 'reason': 'invalid_utf8', 'state': 'UNKNOWN'})
            continue
        if ext in SCRIPT_EXTS - {'.vue', '.svelte'}:
            from .javascript import syntax_text
            try:
                text = syntax_text(text, ext)
            except ValueError:
                continue
        if (root/'angular.json').is_file() and p.name.endswith('.routes.ts'):
            from .javascript import parse, walk, field, literal, text as node_text
            for route in walk(parse(text, ext)):
                if route.type != 'pair' or node_text(field(route, 'key')).strip("\"'") != 'path':
                    continue
                declared = literal(field(route, 'value'))
                if declared is None:
                    continue
                ev=[f'{rel}:{route.start_point.row + 1}']
                graph.add_node(Node(f'frontend-route:{rel}:{route.start_point.row + 1}:{route.start_byte}',
                    'frontend_route',declared or '/',rel,{
                        'scope':'frontend','framework':'Angular','declared_path':declared,
                        'source_role':meta['role']},Evidence(evidence=ev)))
        if ext in TEMPLATE_EXTS:
            nid=f'frontend-template:{rel}'
            graph.add_node(Node(nid,'frontend_template',p.stem,rel,{
                'scope':'frontend','source_role':meta['role'],
                'framework':'Thymeleaf' if re.search(r'\bth:[\w-]+=',text) else ('Angular' if (root/'angular.json').is_file() and rel.startswith('src/app/') else 'template')
            },Evidence(evidence=[rel])))
            _form_calls(graph,rel,text,nid)
            continue

        kind=_script_kind(p,text)
        nid=f'frontend:{kind}:{rel}'
        graph.add_node(Node(nid,kind,p.stem,rel,{
            'scope':'frontend','source_role':meta['role'],'lines':text.count('\n')+1,
            'framework':'Angular' if (root/'angular.json').is_file() and rel.startswith('src/app/') else None,
            'has_state':bool(re.search(r'\b(useState|useReducer|createStore|writable\s*\(|ref\s*\(|reactive\s*\()',text)),
            'has_validation':bool(re.search(r'(?i)\b(validate|validation|required|invalid|errorMessage|errors\b)',text)),
        },Evidence(evidence=[rel])))
        modules[p.stem.lower()]=nid; records.append((p,rel,text,nid,kind))
        _script_calls(graph,rel,text,nid)

    # Resolve only literal imports to a unique inventoried service path.
    from .javascript import parse, walk, field, literal
    service_by_path = {n.path: n.id for n in graph.nodes if n.kind == 'frontend_service'}
    for p,rel,text,nid,kind in records:
        if p.suffix.lower() in {'.vue', '.svelte'}:
            continue
        try:
            tree = parse(text, p.suffix.lower())
            for statement in walk(tree):
                if statement.type != 'import_statement' or statement.text.startswith(b'import type'):
                    continue
                imported = literal(field(statement, 'source'))
                if not imported or not imported.startswith('.'):
                    continue
                base = Path(os.path.normpath(p.parent / imported))
                candidates = [base] + [Path(str(base) + ext) for ext in ('.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.mts', '.cts')]
                targets = {service_by_path[c.relative_to(root).as_posix()] for c in candidates
                           if c.is_relative_to(root) and c.relative_to(root).as_posix() in service_by_path}
                if len(targets) == 1:
                    graph.add_edge(Edge(nid,next(iter(targets)),'depends_on',[rel], {'basis': 'literal-module-resolution'}))
        except ValueError:
            continue
    return graph


def _script_kind(path: Path,text: str) -> str:
    stem=path.stem.lower()
    if any(x in stem for x in ('service','api','client','gateway')) and _has_remote(text): return 'frontend_service'
    if any(x in stem for x in ('store','state')) and re.search(r'(?i)redux|zustand|pinia|createStore|writable\s*\(',text): return 'frontend_store'
    if path.suffix.lower() in {'.jsx','.tsx','.vue','.svelte'} or re.search(r'@Component\b|\bReact\.Component\b|\bfunction\s+[A-Z]\w*\s*\([^)]*\)\s*{[^{}]{0,800}return\s*\(',text,re.S):
        return 'frontend_component'
    return 'frontend_module'


def _has_remote(text:str)->bool:
    return bool(re.search(r'\bfetch\s*\(|\baxios\.|\bXMLHttpRequest\b|\$\.ajax\s*\(|\bHttpClient\b',text))


def _script_calls(graph,rel,text,owner):
    from .javascript import api_calls, request_site
    suffix = Path(rel).suffix.lower()
    if suffix in {'.vue', '.svelte'}:
        graph.coverage[rel] = {'status': 'PARTIAL', 'basis': 'embedded script grammar not admitted', 'omitted_count': None}
        return
    try:
        occurrences = {}
        for node, method, target in api_calls(text, suffix):
            # AST byte offsets must be translated to the character offsets of legacy renderers.
            pos = len(text.encode('utf-8')[:node.start_byte].decode('utf-8'))
            _add_call(graph,rel,text,owner,method,target,pos,'script-ast',request_site(node,method,target,occurrences))
    except ValueError:
        graph.coverage[rel] = {'status': 'PARTIAL', 'basis': 'syntax resource limit', 'omitted_count': None}


def _form_calls(graph,rel,text,owner):
    occurrences = {}
    for m in re.finditer(r'<form\b([^>]*)>',text,re.I|re.S):
        attrs=m.group(1); action=re.search(r'\baction\s*=\s*["\']([^"\']+)["\']',attrs,re.I); method=re.search(r'\bmethod\s*=\s*["\']([^"\']+)["\']',attrs,re.I)
        if action:
            value=action.group(1)
            if value.startswith('@{'):
                value=value[2:].split('(',1)[0].rstrip('}')
            if not value.startswith(('${','#')) and value:
                verb = method.group(1).upper() if method else 'GET'
                anchor = (verb, value)
                index = occurrences.get(anchor, 0)
                occurrences[anchor] = index + 1
                from ..evidence import digest
                _add_call(graph,rel,text,owner,verb,value,m.start(),'form',f'form-site/2:{digest(anchor)}:{index}')


def _add_call(graph,rel,text,owner,method,path,pos,source,site):
    external=bool(re.match(r'https?://',path,re.I))
    cid=f'frontend-call:{rel}:{site}'
    ev=[f'{rel}:{line_of(text,pos)}']
    graph.add_node(Node(cid,'frontend_api_call',f'{method} {path}',rel,{
        'scope':'frontend','http_method':method,'path':path,'external':external,'source':source,'owner':owner,'identity_scope':site
    },Evidence(evidence=ev)))
    graph.add_edge(Edge(owner,cid,'calls_api',ev))
