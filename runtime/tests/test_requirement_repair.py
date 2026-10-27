import json

from ases.engineering.model import interpret_sources
from ases.pipeline import scan_project


def test_modalities_broader_subjects_and_uncertain_kind_keep_original_sentence():
    sentences = ['Registered customers shall export their transaction history.',
                 'The interface should be intuitive to new users.',
                 'Each administrator will receive a monthly report.',
                 'The product must meet the agreed condition.']
    source = {'id': 'd', 'path': 'docs/needs.txt', 'sha256': 'a'*64,
              'role': 'GUIDE', 'format': 'txt',
              'units': [{'line': i+1, 'text': t} for i, t in enumerate(sentences)]}
    rows = interpret_sources([source])['requirements']
    assert [r['statement'] for r in rows] == sentences
    assert [r['modality'] for r in rows] == ['mandatory', 'recommendation', 'stated-behavior', 'mandatory']
    assert [r['kind'] for r in rows] == ['functional', 'nonfunctional', 'functional', 'unspecified']
    assert all(r['declared_id'] is None and r['satisfaction'] == 'not-verified' for r in rows)
    assert rows[-1]['classification']['origin'] == 'unspecified'


def test_document_template_functionality_is_not_an_example_section():
    from ases.engineering.requirements import prose_requirement
    text = 'Users shall create a reusable document template from the active document.'
    assert prose_requirement(text, 'Document templates') is not None
    assert prose_requirement(text, 'Examples of document templates') is None


def test_native_scanning_preserves_declared_types_unknowns_and_reference_scope(tmp_path):
    root = tmp_path/'project'; root.mkdir()
    data = {'id': 'P', 'documents': [{'id': 'SRS', 'attributes': {'type': {'values': [
        {'key': 'FR', 'label': 'Functional Requirement'}, {'key': 'REQ', 'label': 'Requirement'}]}},
        'data': [{'id': '1', 'type': 'FR', 'text': '<p>The service shall be intuitive.</p>',
                  'priority': 'High', 'verMethod': 'T', 'links': {'satisfaction': ['SRS-2']}},
                 {'id': '2', 'type': 'REQ', 'text': '<p>The service shall export its records.</p>'}]}]}
    (root/'original.reqw').write_text(json.dumps(data), encoding='utf-8')
    model = scan_project(root, tmp_path/'snapshot')['engineering_model']
    rows = {r['id']: r for r in model['requirements']}
    assert rows['P-SRS-1']['kind'] == 'functional'  # source outranks text heuristic
    assert rows['P-SRS-2']['kind'] == 'unspecified'
    assert rows['P-SRS-1']['declared_id'] == 'P-SRS-1'
    assert rows['P-SRS-1']['native_declared_id'] == '1'
    assert rows['P-SRS-1']['fields']['source_attributes']['verMethod'] == 'T'
    assert rows['P-SRS-1']['locations'][0]['document'] == 'SRS'
    assert rows['P-SRS-1']['locations'][0]['path'] == 'original.reqw'
    links = [r for r in model['links'] if r['relation'] == 'declared-document-reference']
    assert len(links) == 1 and links[0]['resolved']
    assert 'satisfaction not established' in links[0]['status']
    assert model['document_profile'] == 'inert-documents/9'


def test_arff_row_keys_are_scoped_and_auxiliary_reqview_fields_cannot_drop_text(tmp_path):
    root = tmp_path/'project'; root.mkdir()
    arff = '@relation sample\n@attribute ProjectID string\n@attribute ID string\n@attribute Statement string\n@data\n'
    (root/'a.arff').write_text(arff + "'one','R-1','A first declared requirement.'\n'other','R-1','A different requirement.'\n", encoding='utf-8')
    (root/'b.arff').write_text(arff + "'one','R-1','Another source declaration.'\n", encoding='utf-8')
    data = {'id': 'P', 'documents': [{'id': 'SRS', 'attributes': {'type': {'values': [{'key': 'FR', 'label': 'Functional Requirement'}]}},
            'data': [{'id': '1', 'type': 'FR', 'status': 42, 'text': '<p>Preserve the original declaration.</p>'}]}]}
    (root/'aux.reqw').write_text(json.dumps(data), encoding='utf-8')
    rows = scan_project(root, tmp_path/'snapshot')['engineering_model']['requirements']
    assert len(rows) == 4 and len({r['id'] for r in rows}) == 4
    assert len([r for r in rows if r['declared_id'] == 'R-1']) == 3
    native = next(r for r in rows if r['id'] == 'P-SRS-1')
    assert native['statement'] == 'Preserve the original declaration.'
    assert native['fields']['source_attributes']['status'] == 42
    assert native['locations'][0]['native_path'] == ['1']
