import json
from pathlib import Path

from ases.engineering.inputs import read_input
from ases.engineering.render import render_documents
from ases.engineering.views import overview
from ases.pipeline import scan_project
from ases.scanners.python import scan_python


def test_arbitrary_structured_data_is_not_document_prose(tmp_path):
    path = tmp_path / 'measurements.json'
    path.write_text(json.dumps({'samples': [{'value': i} for i in range(10000)]}, indent=2))
    units, status, notes, metadata = read_input(path, lambda: None)
    assert status == 'unsupported'
    assert units == [] and metadata == {}
    assert 'not interpreted as prose' in notes[0]
    path.write_text(json.dumps({'requirements': [{'id': 'RF_USER_1', 'statement': 'The caller shall receive a receipt.'}]}))
    units, status, _, metadata = read_input(path, lambda: None)
    assert status == 'complete'
    assert units and metadata['structured_requirements'][0]['id'] == 'RF_USER_1'


def test_custom_http_handler_is_an_explicit_unknown_not_zero_routes_proof(tmp_path):
    (tmp_path / 'server.py').write_text('from http.server import BaseHTTPRequestHandler as Base\ndef factory():\n    class Handler(Base):\n        def do_GET(self):\n            dispatch(self)\n    return Handler\n')
    graph = scan_python(tmp_path)
    unknown = next(row for row in graph.unknowns if row['reason'] == 'python_custom_http_routing_not_reconstructed')
    assert unknown['path'] == 'server.py' and unknown['line'] == 3
    assert not any(node.kind == 'route' for node in graph.nodes)


def test_overview_separates_missing_declarations_from_source_tests():
    model = {'snapshot_id': 'snapshot:example', 'requirements': [], 'operations': [],
             'recovered_requirements': [], 'sources': [{'extraction': 'unsupported'}],
             'structure': {'tests': [{'id': 'test:example'}]}}
    text = overview(model, True)
    assert 'non dimostra che il progetto' in text
    assert '| Definizioni di test riconosciute nel codice | 1 |' in text
    assert '| Casi di test documentati riconosciuti | 0 |' in text
    assert 'Nessuna specifica originale recuperata' not in text


def test_document_links_are_indexed_once_for_all_api_rows(tmp_path):
    root = tmp_path / 'project'
    root.mkdir()
    (root / 'lib.py').write_text('def read(value):\n    return value\n')
    model = scan_project(root, tmp_path / 'result.ases')['engineering_model']
    api_entities = {row['id']: row.get('entity_ref') for row in model['api']}
    for link in model['links']:
        if link['relation'] == 'supported-by-interface-body':
            assert link['locations']
            assert all(loc['entity_ref'] == api_entities[link['target']] for loc in link['locations'])
    # Repeated API rows expose quadratic rescans without timing-sensitive assertions.
    model['api'] *= 100
    class Counted(list):
        iterations = 0
        def __iter__(self):
            self.iterations += 1
            return super().__iter__()
    for key in ('relations', 'links'):
        model[key] = Counted(model[key])
    documents = render_documents(model)
    assert 'ODD.md' in documents
    assert model['relations'].iterations == 1
    assert model['links'].iterations <= 4
