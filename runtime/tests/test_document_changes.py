"""R4 document change acceptance sequence; review candidates never migrate notes."""
from copy import deepcopy
from pathlib import Path
import re
import pytest

from ases.pipeline import scan_project
from ases.engineering.model import engineering_diff
from ases.engineering.service import apply_review, regenerate
from ases.engineering.views import anchor


def scan(tmp_path, label, files, **options):
    root=tmp_path/label;root.mkdir()
    for name,text in files.items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')
    result=scan_project(root,tmp_path/(label+'.ases'),**options)
    return result['engineering_model'],tmp_path/(label+'.ases')


SOURCE='def read(value):\n    if value < 0:\n        return 0\n    return value\n'


def test_formatting_changes_source_without_claiming_changed_supported_behavior(tmp_path):
    before,_=scan(tmp_path,'before',{'api.py':SOURCE})
    after,_=scan(tmp_path,'after',{'api.py':'\n\ndef read( value ):\n    if value<0:\n        return 0\n    return value\n'})
    delta=engineering_diff(before,after)
    assert 'api.py' in delta['source_changes']
    assert any('supported-content-unchanged; inspect-source-or-formatting' in r['reasons'] for r in delta['record_changes'])
    assert not any('supported-behavior-changed' in r['reasons'] for r in delta['record_changes'])
    assert 'equivalence' in delta['identity_policy']


def test_moved_declaration_is_only_a_candidate_and_old_review_conflicts(tmp_path):
    before,_=scan(tmp_path,'before',{'api.py':SOURCE})
    after,_=scan(tmp_path,'after',{'moved.py':SOURCE})
    old=before['recovered_requirements'][0]
    review={'schema':'ases-engineering-review/1.0','operations':[{'action':'confirm','record_id':old['id'],'expected_digest':old['record_digest'],'note':'Checked against the former source.'}]}
    delta=engineering_diff(before,after)
    assert delta['missing'] and delta['added']
    assert any(r['basis']=='candidate-relocation' for r in delta['record_changes'])
    revised=apply_review(after,review)
    assert revised['review_state']['conflicts']
    assert not any(r.get('review') for r in revised['recovered_requirements'])


@pytest.mark.parametrize('replacement,reason', [
    ('def read(value, extra=None):\n    return value\n','signature-changed'),
    (SOURCE.replace('value < 0','value <= 0'),'supported-behavior-changed'),
])
def test_signature_and_condition_have_distinct_reasons(tmp_path,replacement,reason):
    before,_=scan(tmp_path,'before',{'api.py':SOURCE})
    after,_=scan(tmp_path,'after',{'api.py':replacement})
    assert any(reason in r['reasons'] for r in engineering_diff(before,after)['record_changes'])


def test_changed_requirement_and_removed_source_are_not_resolution(tmp_path):
    spec='requirements:\n  - id: RF_DEMO_1\n    kind: functional\n    statement: The caller shall receive an identifier.\n'
    before,_=scan(tmp_path,'before',{'api.py':SOURCE,'requirements.yaml':spec})
    after,_=scan(tmp_path,'after',{'requirements.yaml':spec.replace('an identifier','a receipt')})
    delta=engineering_diff(before,after)
    assert delta['missing'] and 'api.py' in delta['source_changes']
    assert any('statement-changed' in r['reasons'] for r in delta['record_changes'])
    assert 'resolved' not in delta
    assert {'RAD','SDD','ODD'} <= set(delta['sections_to_review'])


def test_configuration_scope_and_method_changes_are_separate(tmp_path):
    before,_=scan(tmp_path,'before',{'api.py':SOURCE,'experiment.py':'def unused():\n    return 1\n'})
    after,_=scan(tmp_path,'after',{'api.py':SOURCE,'experiment.py':'def unused():\n    return 1\n'},exclude=['experiment.py'])
    delta=engineering_diff(before,after)
    assert delta['configured_scope_changed'] and delta['source_set_changed']
    changed=deepcopy(before);changed['narrative_profile']='future-profile'
    delta=engineering_diff(before,changed)
    assert delta['narrative_method_changed'] and not delta['configured_scope_changed']
    assert 'RAD' in delta['sections_to_review']


def test_ambiguous_relocation_never_chooses_a_record(tmp_path):
    before,_=scan(tmp_path,'before',{'a.py':SOURCE,'b.py':SOURCE})
    after,_=scan(tmp_path,'after',{'c.py':SOURCE,'d.py':SOURCE})
    delta=engineering_diff(before,after)
    assert delta['ambiguous_matches']
    assert not any(r['basis']=='candidate-relocation' for r in delta['record_changes'])


def test_summary_complete_and_inverse_links_share_one_model(tmp_path):
    model,out=scan(tmp_path,'source',{'api.py':'# RF_DEMO_1\ndef read():\n    """RF_DEMO_1: return an identifier."""\n    return 1\n',
        'requirements.yaml':'requirements:\n  - id: RF_DEMO_1\n    kind: functional\n    statement: The caller shall receive an identifier.\n'})
    docs=out/'docs'
    assert model['snapshot_id'] in (docs/'OVERVIEW.md').read_text(encoding='utf-8')
    assert 'RAD.md' in (docs/'OVERVIEW.md').read_text(encoding='utf-8')
    assert 'Additional code-only baseline' not in (docs/'RAD.md').read_text(encoding='utf-8')
    trace=(docs/'TRACEABILITY.md').read_text(encoding='utf-8')
    assert 'In ingresso' in trace and 'In uscita' in trace
    assert 'requirements.yaml · line=2' in trace
    assert '|  (unresolved)' not in trace
    for file,identifier in re.findall(r'\]\((\w+\.md)#(record-[a-f0-9]+)\)',trace):
        assert 'id="'+identifier+'"' in (docs/file).read_text(encoding='utf-8')
    sdd=(docs/'SDD.md').read_text(encoding='utf-8')
    assert sdd.count('## Da completare con fonti o conferme')==1
    assert 'Non recuperato. Servono specifiche' not in sdd


def test_legacy_scope_is_unknown_and_manual_documents_still_protected(tmp_path):
    model,out=scan(tmp_path,'source',{'api.py':SOURCE})
    legacy=deepcopy(model);legacy.pop('analysis_scope')
    assert engineering_diff(legacy,model)['configured_scope_changed'] is None
    package=tmp_path/'documents';regenerate(out,package)
    (package/'OVERVIEW.md').write_text('Manual introduction',encoding='utf-8')
    with pytest.raises(ValueError,match='edited'):regenerate(out,package)
    assert (package/'OVERVIEW.md').read_text()=='Manual introduction'


def test_method_change_invalidates_operation_support_without_losing_adoption(tmp_path):
    from ases.engineering.operations import build_operations
    before,_=scan(tmp_path,'source',{'api.py':SOURCE})
    operation=before['operations'][0]
    review={'schema':'ases-engineering-review/1.1','base_model_digest':before['model_digest'],'operations':[{
        'action':'adopt-requirement','record_id':'user-requirement:method','source_record_id':operation['id'],
        'expected_source_digest':operation['record_digest'], 'requirement':{
            'declared_id':'RF_METHOD_1','kind':'functional','statement':'The caller shall receive a value.',
            'author':'Fixture owner','scope':'Owned example','acceptance':'Expected value independently agreed, test not run.'}}]}
    after=deepcopy(before);after['behavior_profile']='future-profile'
    after['operations'],_=build_operations(after)
    assert after['operations'][0]['id']==operation['id']
    assert after['operations'][0]['record_digest']!=operation['record_digest']
    revised=apply_review(after,review)
    assert revised['user_requirements'][0]['support_state']=='needs-review'
    assert revised['review_state']['conflicts']
