"""Product explanations and explicit authoring: independent intent stays explicit."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from ases.engineering.claim_evaluation import canonical
from ases.engineering.model import digest, engineering_diff
from ases.engineering.narrative import condition_text, predicate
from ases.engineering.service import apply_review, load_model, load_reviewed_model, regenerate
from ases.pipeline import scan_project


@pytest.fixture
def snapshot(tmp_path):
    root=tmp_path/'app';root.mkdir()
    (root/'app.py').write_text('from fastapi import FastAPI\napp=FastAPI()\nclass Store:\n    def save(self,value):\n        return 1\nstore=Store()\n@app.post("/orders")\ndef create(title:str):\n    if not title:\n        return {"error":"required"}\n    store.save(title)\n    return {"id":1}\n',encoding='utf-8')
    output=tmp_path/'scan'
    return root,output,scan_project(root,output)['engineering_model']


def review(model, *ops):
    return {'schema':'ases-engineering-review/1.1','base_model_digest':model['model_digest'],'operations':list(ops)}


def authored(identifier='first', **changes):
    fields={'declared_id':'RF_USER_1','kind':'functional','statement':'The clerk shall receive a receipt.',
            'author':'Project owner','scope':'Proposed release','acceptance':'Given an accepted order, the clerk receives a receipt.'}
    fields.update(changes)
    return {'action':'add-requirement','record_id':'user-requirement:'+identifier,'requirement':fields}


@pytest.mark.parametrize(('raw','source','value','negative'),[
    ('not (not title)','python','title',False),('not title','python','title',True),
    ('!(!req.title)','javascript','req.title',False),('!req.title','javascript','req.title',True),
    ('!a && b','javascript','!a && b',False),('!(a && b)','javascript','a && b',True),
    ('not(flag)','javascript','not(flag)',False),('not (flag)','javascript','not (flag)',False),
    ('notabc','python','notabc',False),('value != 0','python','value != 0',False)])
def test_readable_negation_preserves_the_whole_predicate(raw,source,value,negative):
    assert predicate(raw,source)==(value,negative)


def test_partial_path_is_not_verbalized_as_a_boolean_condition():
    text=condition_text(['Java control flow partial; branch association unresolved'])
    assert 'parzialmente' in text and 'valutato come vero' not in text


def test_java_outcome_without_field_shape_does_not_crash_evaluation():
    assert canonical({'expression':'value','conditions':[]},'outcomes')==canonical({'expression':'value','conditions':[],'output_fields':[]},'outcomes')


def test_expression_explanations_do_not_assume_numeric_operands_or_fixed_expansion():
    from ases.engineering.behavior import explain_expression
    assert 'somma' not in explain_expression('left + right')
    assert 'prodotto' not in explain_expression('value * 2')
    assert 'lunghezza non ricostruita' in explain_expression('[first, *rest]')
    assert 'somma' in explain_expression('1 + 2')


def test_explanation_clauses_have_relevant_saved_facts(snapshot):
    _,_,model=snapshot;row=model['recovered_requirements'][0]
    assert 'not (not' not in row['statement_it']
    assert 'il controllo su «title» dà esito negativo' in row['statement_it']
    facts={f['fact_id']:f for f in row['facts']}
    for clause in row['explanation']['clauses']:
        assert clause['fact_refs']
        for ref in clause['fact_refs']:
            fact=facts[ref]
            if clause['kind']=='effect':assert 'può chiamare' in clause['text_it'] and 'restano da verificare' in clause['text_it']
            elif clause['kind']=='error':assert 'errore' in clause['text_it']
            else:assert all(field in clause['text_it'] for field in fact.get('output_fields',[]))
    assert row['authority']=='static-inference' and not model['requirements']


def test_js_function_named_not_is_not_confused_with_generated_negation(tmp_path):
    root=tmp_path/'app';root.mkdir()
    (root/'api.js').write_text('export function choose(flag){if(not(flag)) return {yes:1}; return {no:0};}',encoding='utf-8')
    model=scan_project(root,tmp_path/'scan')['engineering_model']
    row=next(r for r in model['recovered_requirements'] if r['name']=='choose')
    assert '“not(flag)” evaluates as true' in row['statement_en']
    assert '“not(flag)” evaluates as false' in row['statement_en']
    assert [f['conditions'] for f in row['external_outcomes']]==[['(not(flag))'],['not ((not(flag)))']]


def test_operations_merge_same_handlers_but_not_shared_helpers(tmp_path):
    root=tmp_path/'app';root.mkdir()
    (root/'app.py').write_text('from fastapi import FastAPI\napp=FastAPI()\ndef shared():\n    return 1\n@app.get("/a")\n@app.get("/alias")\ndef one():\n    shared()\n    return {"a":1}\n@app.get("/b")\ndef two():\n    shared()\n    return {"b":1}\n',encoding='utf-8')
    model=scan_project(root,tmp_path/'scan')['engineering_model']
    assert len(model['operations'])==2
    a=next(op for op in model['operations'] if '/a' in op['name'])
    assert '/alias' in a['name'] and '/b' not in a['name']
    assert all(any(s['callee']=='shared' for s in op['supported_steps']) for op in model['operations'])
    assert all({q['id'] for q in op['questions']}=={'actor','purpose','acceptance'} for op in model['operations'])


def test_context_and_confirmation_do_not_create_a_requirement_or_modify_facts(snapshot):
    _,_,model=snapshot;original=deepcopy(model);op=model['operations'][0]
    updates=review(model,{'action':'set-operation-context','record_id':op['id'],'expected_digest':op['record_digest'],
                          'context':{'title':'Record an order','actor':'Clerk','purpose':'Keep accepted orders'}},
                   {'action':'confirm','record_id':op['id'],'expected_digest':op['record_digest'],'note':'Reading reviewed'})
    revised=apply_review(model,updates)
    assert not revised['requirements'] and not revised['user_requirements']
    assert revised['operations'][0]['user_context']['actor']=='Clerk'
    assert revised['operations'][0]['authority']=='static-inference'
    assert model==original


def test_adoption_and_authored_requirement_are_explicit_and_unverified(snapshot):
    _,_,model=snapshot;op=model['operations'][0]
    adopt=authored();adopt.update(action='adopt-requirement',source_record_id=op['id'],expected_source_digest=op['record_digest'])
    manual=authored('second',declared_id='RNF_USER_2',kind='nonfunctional')
    revised=apply_review(model,review(model,adopt,manual))
    assert len(revised['user_requirements'])==2 and not revised['requirements']
    assert all(r['authority']=='user-confirmation' and r['satisfaction']=='not-verified' for r in revised['user_requirements'])
    assert revised['user_requirements'][0]['support_state']=='current-candidate'
    assert revised['user_requirements'][1]['support_state']=='user-authored'
    assert any(l['relation']=='adopted-from-candidate' and l['resolved'] for l in revised['links'])


def test_adopted_need_survives_changed_or_missing_candidate(snapshot):
    _,_,model=snapshot;op=model['operations'][0]
    adopt=authored();adopt.update(action='adopt-requirement',source_record_id=op['id'],expected_source_digest=op['record_digest'])
    saved=review(model,adopt)
    for mode in ('changed','missing'):
        changed=deepcopy(model)
        if mode=='changed':changed['operations'][0]['record_digest']='changed'
        else:changed['operations']=[]
        revised=apply_review(changed,saved)
        assert revised['user_requirements'][0]['statement']==adopt['requirement']['statement']
        assert revised['user_requirements'][0]['support_state']=='needs-review'
        assert not revised['user_requirements'][0]['locations']
        assert revised['review_state']['conflicts']
        assert not next(l for l in revised['links'] if l['relation']=='adopted-from-candidate')['resolved']


@pytest.mark.parametrize('invalid',['author','scope','acceptance','statement','kind','id','duplicate','legacy','action','context','collision'])
def test_invalid_authoring_is_rejected_before_changing_the_model(snapshot,invalid):
    _,_,model=snapshot;original=deepcopy(model);create=authored();saved=review(model,create)
    if invalid in {'author','scope','acceptance','statement'}:create['requirement'][invalid]=' '
    elif invalid=='kind':create['requirement']['kind']='implementation-proven'
    elif invalid=='id':create['record_id']='RF_FROM_SOURCE_1'
    elif invalid=='duplicate':saved['operations'].append(deepcopy(create))
    elif invalid=='legacy':saved['schema']='ases-engineering-review/1.0'
    elif invalid=='action':create['action']={}
    elif invalid=='context':
        op=model['operations'][0];saved=review(model,{'action':'set-operation-context','record_id':op['id'],'expected_digest':op['record_digest'],'context':{'verified':True}})
    elif invalid=='collision':model['requirements']=[{'id':'RF_USER_1','declared_id':'RF_USER_1'}];original=deepcopy(model)
    with pytest.raises(ValueError):apply_review(model,saved)
    assert model==original


def test_authored_documents_and_legacy_models_regenerate_without_sources(snapshot,tmp_path):
    root,output,model=snapshot
    new=review(model,authored())
    regenerate(output,tmp_path/'documents',review=new)
    rad=(tmp_path/'documents/RAD.md').read_text(encoding='utf-8')
    assert 'The clerk shall receive a receipt.' in rad and 'Project owner' in rad and 'not-verified' in rad
    assert json.loads((tmp_path/'documents/engineering-review.json').read_text())==new
    assert not load_model(tmp_path/'documents')['user_requirements']
    assert len(apply_review(load_model(tmp_path/'documents'),new)['user_requirements'])==1
    legacy=deepcopy(model)
    for key in ('operations','operations_profile','narrative_profile','user_requirements'):legacy.pop(key,None)
    legacy['model_digest']=digest({k:v for k,v in legacy.items() if k!='model_digest'})
    old=tmp_path/'legacy';old.mkdir();(old/'engineering-model.json').write_text(json.dumps(legacy),encoding='utf-8')
    regenerate(old,tmp_path/'legacy-documents',review={'schema':'ases-engineering-review/1.0','operations':[]})
    assert (tmp_path/'legacy-documents/RAD.md').is_file()


def test_stale_operation_context_is_retained_as_conflict_not_applied(snapshot):
    _,_,model=snapshot;op=model['operations'][0]
    context=review(model,{'action':'set-operation-context','record_id':op['id'],'expected_digest':'old','context':{'actor':'Clerk'}})
    revised=apply_review(model,context)
    assert 'user_context' not in revised['operations'][0] and revised['review_state']['conflicts']


def test_new_project_can_author_requirements_without_invented_implementation(tmp_path):
    root=tmp_path/'empty';root.mkdir()
    output=tmp_path/'scan';model=scan_project(root,output)['engineering_model']
    assert not model['operations'] and not model['recovered_requirements']
    revised=apply_review(model,review(model,authored()))
    assert revised['user_requirements'][0]['satisfaction']=='not-verified'
    assert not revised['api'] and not revised['requirements']


def test_document_diff_reads_user_authored_requirements_and_operation_context(snapshot,tmp_path):
    _,output,model=snapshot;op=model['operations'][0]
    updates=review(model,authored(),{'action':'set-operation-context','record_id':op['id'],'expected_digest':op['record_digest'],'context':{'actor':'Clerk'}})
    revised=tmp_path/'revised';regenerate(output,revised,review=updates)
    delta=engineering_diff(load_reviewed_model(output),load_reviewed_model(revised))
    assert 'user-requirement:first' in delta['added']
    assert op['id'] in delta['changed_supported_fields']
    assert 'RAD' in delta['sections_to_review']


def test_packaged_review_schema_covers_explicit_actions_and_legacy_reading(snapshot):
    import jsonschema
    from importlib.resources import files
    schema=json.loads(files('ases.engineering').joinpath('resources/engineering-review.schema.json').read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    _,_,model=snapshot
    jsonschema.validate(review(model,authored()),schema)
    jsonschema.validate({'schema':'ases-engineering-review/1.0','operations':[]},schema)
    with pytest.raises(jsonschema.ValidationError):jsonschema.validate({'schema':'ases-engineering-review/1.0','operations':[authored()]},schema)
