from pathlib import Path

import pytest

from ases.scanners.python import scan_python
from ases.engineering.entry_selection import prioritize

SERVER = '''from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

def factory():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            dispatch_get(self)
        def do_POST(self):
            dispatch_post(self)
    return Handler

def pick(path, exact, prefixes):
    selected = exact.get(path)
    if selected is not None:
        return selected
    return None

def dispatch_get(request):
    parsed = urlparse(request.path)
    route = parsed.path
    selected = pick(route, READERS, ())
    if selected is not None:
        selected(request)

def dispatch_post(request):
    route = urlparse(request.path).path
    selected = WRITERS.get(route)
    if selected is not None:
        selected(request)

def read(request):
    return {'items': []}

def write(request):
    return {'created': True}

READERS = {'/items': read}
WRITERS = {'/items': write}
UNUSED = {'/not-a-route': read}
'''


def scan(tmp_path, source):
    (tmp_path/'server.py').write_text(source, encoding='utf-8')
    return scan_python(tmp_path)


def test_exact_stdlib_dispatch_tables_have_handlers_and_evidence(tmp_path):
    graph = scan(tmp_path, SERVER)
    routes = [n for n in graph.nodes if n.kind == 'route']
    assert {n.name for n in routes} == {'GET /items','POST /items'}
    assert {n.metadata['handler'] for n in routes} == {'function:server:read','function:server:write'}
    assert all(n.provenance.state == 'INFERRED' and len(n.provenance.evidence) >= 3 for n in routes)
    assert any(u['reason']=='python_custom_http_routing_partial' for u in graph.unknowns)


@pytest.mark.parametrize('suffix', ["\nREADERS['/items'] = write\n", '\nREADERS.update({})\n', '\nREADERS = {}\n', '\nalias = READERS\n', '\nconsume(READERS)\n', '\nconsume(table=READERS)\n', '\naliases = [READERS]\n'])
def test_changed_or_escaped_registry_is_not_a_declared_route(tmp_path, suffix):
    graph = scan(tmp_path, SERVER+suffix)
    assert {n.name for n in graph.nodes if n.kind=='route'} == {'POST /items'}


@pytest.mark.parametrize('before,after', [
    ('selected = pick(route, READERS, ())', "selected = pick('/fixed', READERS, ())"),
    ('selected = pick(route, READERS, ())', 'selected = pick(route, READERS, ())\n    selected = other'),
    ('dispatch_get(self)', 'unrelated(self)'),
    ('def factory():', 'def factory(BaseHTTPRequestHandler):'),
    ('selected = exact.get(path)', 'exact.clear()\n    selected = exact.get(path)'),
    ('selected = exact.get(path)', 'alias = exact\n    selected = exact.get(path)'),
    ('route = parsed.path', 'route = parsed.path\n    route: str = "/fixed"'),
    ('selected = pick(route, READERS, ())', 'selected = pick(route, READERS, ())\n    selected: object = other'),
])
def test_unproven_lookup_or_binding_is_not_a_get_route(tmp_path, before, after):
    graph = scan(tmp_path, SERVER.replace(before, after))
    assert 'GET /items' not in {n.name for n in graph.nodes if n.kind=='route'}


def test_entry_budget_prioritizes_runtime_and_spreads_files():
    nodes = {'b'+str(i):{'path':'benchmarks/a.py'} for i in range(12)}
    nodes.update({'p'+str(i):{'path':'src/a.py'} for i in range(12)})
    nodes['other']={'path':'src/z.py'}
    entries = [(key,key,[key],{}) for key in nodes]
    ordered = prioritize(entries,nodes,budget=5)
    assert {e[0] for e in ordered[:2]} == {'p0','other'}
    assert all(not e[0].startswith('b') for e in ordered[:5])
    assert sorted(e[0] for e in entries)==sorted(e[0] for e in ordered)
    assert prioritize(entries,nodes,budget=100) is entries


def test_json_response_requires_the_writer_proof_and_actual_route(tmp_path):
    from ases.pipeline import scan_project
    source = SERVER.replace('from urllib.parse import urlparse','from urllib.parse import urlparse\nimport json')
    wrapper = '''        def emit(self, status, payload):
            data = json.dumps(payload).encode('utf-8')
            self.transmit(status, data, 'application/json')
        def transmit(self, status, data, kind):
            self.send_response(status)
            self.end_headers()
            self.wfile.write(data)
'''
    source = source.replace('        def do_GET(self):',wrapper+'        def do_GET(self):')
    source = source.replace("return {'items': []}","request.emit(200, {'items': []})")
    root = tmp_path/'app'; root.mkdir()
    (root/'server.py').write_text(source)
    model = scan_project(root,tmp_path/'snapshot')['engineering_model']
    entry = next(r for r in model['recovered_requirements'] if r['name']=='GET /items')
    response = next(f for f in entry['external_outcomes'] if f['kind']=='response')
    assert response['http_status']==200 and response['output_fields']==['items']
    assert response['wrapper_evidence'] and entry['entry_declaration_locations']
    assert 'risposta JSON HTTP 200' in entry['statement_it']
    # A method called emit is insufficient without the declared HTTP writer.
    (root/'server.py').write_text(source.replace('self.wfile.write(data)','sink(data)'))
    model = scan_project(root,tmp_path/'no-writer')['engineering_model']
    entry = next(r for r in model['recovered_requirements'] if r['name']=='GET /items')
    assert not any(f['kind']=='response' for f in entry['external_outcomes'])


def test_imported_handler_overwritten_by_a_function_is_not_trusted(tmp_path):
    graph = scan(tmp_path, SERVER+'\ndef BaseHTTPRequestHandler():\n    pass\n')
    assert not any(n.kind=='route' for n in graph.nodes)


def test_http_bodies_are_read_before_benchmarks_consume_the_fact_budget(tmp_path, monkeypatch):
    from ases.pipeline import scan_project
    from ases.engineering import behavior
    monkeypatch.setattr(behavior,'BODY_FACT_BUDGET',20)
    root=tmp_path/'app';(root/'benchmarks').mkdir(parents=True);(root/'src').mkdir()
    (root/'benchmarks/early.py').write_text('\n'.join(f'def probe_{i}(flag):\n    if flag:\n        return 1\n    return 2\n' for i in range(30)))
    (root/'src/server.py').write_text(SERVER)
    model=scan_project(root,tmp_path/'result')['engineering_model']
    rows={row['name']:row for row in model['recovered_requirements']}
    assert {'GET /items','POST /items'} <= rows.keys()
    assert rows['GET /items']['returns'][0]['output_fields']==['items']
    assert rows['POST /items']['returns'][0]['output_fields']==['created']
    assert not rows['GET /items']['external_outcomes']  # The dispatcher ignores the callable's return.
    assert not rows['POST /items']['external_outcomes']
    assert any('20 behavior-fact budget' in row['reason'] for row in model['behavior_coverage'])


PREFIX_SERVER = SERVER.replace('    return None\n\ndef dispatch_get', '''    for prefix, candidate in prefixes:
        if path.startswith(prefix):
            return candidate
    return None

def dispatch_get''').replace('pick(route, READERS, ())', 'pick(route, READERS, PREFIXES)') + '''
PREFIXES = (('/assets/', read), ('/assets/icons/', write))
'''


def test_prefix_dispatch_is_distinct_from_exact_routes(tmp_path):
    graph = scan(tmp_path, PREFIX_SERVER)
    routes = {n.name:n for n in graph.nodes if n.kind=='route'}
    assert set(routes)=={'GET /items','POST /items','GET /assets/*','GET /assets/icons/*'}
    prefix = routes['GET /assets/*']
    assert prefix.metadata['match_kind']=='prefix'
    assert prefix.metadata['path_prefix']=='/assets/'
    assert prefix.metadata['route_scope']=='declared-static-prefix-table'
    assert 'shadow' in prefix.metadata['dispatch_precedence']
    assert prefix.provenance.state=='INFERRED'


@pytest.mark.parametrize('before,after', [
    ('path.startswith(prefix)', 'path.endswith(prefix)'),
    ('return candidate', 'return other'),
    ('for prefix, candidate in prefixes:', 'prefixes.clear()\n    for prefix, candidate in prefixes:'),
    ('for prefix, candidate in prefixes:', 'alias = prefixes\n    for prefix, candidate in prefixes:'),
    ('for prefix, candidate in prefixes:', 'path = "/fixed"\n    for prefix, candidate in prefixes:'),
    ('pick(route, READERS, PREFIXES)', 'pick("/fixed", READERS, PREFIXES)'),
])
def test_unproven_prefix_lookup_is_not_a_route(tmp_path, before, after):
    graph=scan(tmp_path,PREFIX_SERVER.replace(before,after))
    assert not any(n.kind=='route' and n.metadata.get('match_kind')=='prefix' for n in graph.nodes)


def test_prefix_mutation_or_escape_prevents_promotion(tmp_path):
    for suffix in ('\nPREFIXES += (("/other/", read),)\n','\nconsume(PREFIXES)\n'):
        graph=scan(tmp_path,PREFIX_SERVER+suffix)
        assert not any(n.kind=='route' and n.metadata.get('match_kind')=='prefix' for n in graph.nodes)
