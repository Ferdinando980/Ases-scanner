from ases.engineering.model import interpret_sources
from ases.pipeline import scan_project


def source(lines, path='docs/requirements.md'):
    return {'id':'doc:sample','path':path,'sha256':'a'*64,'role':'GUIDE',
            'format':'md','units':[{'line':i+1,'text':s} for i,s in enumerate(lines)]}


def test_obligation_sentences_retain_words_provenance_and_no_fabricated_declared_id():
    lines=['# Requisiti', 'Il sistema deve consentire la ricerca dei documenti.',
           'The system shall respond within 200 milliseconds.',
           'Quando la ricerca termina, il sistema deve mostrare i risultati trovati.']
    rows=interpret_sources([source(lines)])['requirements']
    assert [r['statement'] for r in rows]==lines[1:]
    assert [r['kind'] for r in rows]==['functional','nonfunctional','functional']
    assert all(r['declared_id'] is None and r['authority']=='document-declaration' for r in rows)
    assert all(r['satisfaction']=='not-verified' and r['locations'][0]['sha256']=='a'*64 for r in rows)
    moved=interpret_sources([source(['',*lines])])['requirements']
    assert [r['id'] for r in rows]==[r['id'] for r in moved]


def test_labels_examples_code_and_developer_instructions_are_not_requirements():
    lines=['# Uso','Ricerca dei documenti','You must install Python before starting.',
           '```text','The system shall delete all stored documents.','```',
           '# Examples','The system shall create a fake receipt.',
           '# Requisiti','The system might support optional exports.']
    assert not interpret_sources([source(lines)])['requirements']


def test_explicit_ids_do_not_create_duplicate_prose_records():
    src=source(['RF_USER_1 The system shall allow the user to read documents.'])
    src['role']='RAD'
    rows=interpret_sources([src])['requirements']
    assert len(rows)==1 and rows[0]['declared_id']=='RF_USER_1'


def test_scan_and_rad_render_prose_in_both_languages(tmp_path):
    root=tmp_path/'project';root.mkdir()
    (root/'README.md').write_text('# Requirements\nThe system shall export a report for the user.\n',encoding='utf-8')
    model=scan_project(root,tmp_path/'result')['engineering_model']
    assert len(model['requirements'])==1
    from ases.engineering.render import render_documents
    for language in ('it','en'):
        docs=render_documents(model,language)
        assert 'The system shall export a report for the user.' in docs['RAD.md']
        assert 'prose:' not in docs['RAD.md'].split('### ')[1].splitlines()[0]


def test_quality_obligations_and_archived_applicability_are_not_current_features():
    src=source(['Il sistema deve essere estensibile attraverso nuove primitive.',
                'Il sistema non deve sacrificare correttezza per migliorare la velocità.',
                'The system shall authenticate the user before showing private records.'],
               path='docs/archive/requirements.md')
    rows=interpret_sources([src])['requirements']
    assert [r['kind'] for r in rows]==['nonfunctional','nonfunctional','functional']
    assert all('current release applicability not established' in r['scope'] for r in rows)
