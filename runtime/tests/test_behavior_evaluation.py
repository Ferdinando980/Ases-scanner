"""Closed-flow scoring must expose false claims, omissions and invalid oracles."""
import ast
from copy import deepcopy
import json
from pathlib import Path

import pytest

from ases.engineering.claim_evaluation import canonical, predicate, score_claims, validate_oracles
from ases.engineering.evaluate import evaluate_documents
from ases.engineering.flow import python_facts, js_facts
from ases.scanners.javascript import parse, walk, FUNCTIONS
from ases.pipeline import scan_project


def oracle():
    return {"select":{"name":"read"}, "oracle":"Manual: id is returned only when flag is true.", "closed":["outcomes","errors","effects"],
            "outcomes":[{"expression":"{'id': 1}","conditions":["flag"],"output_fields":["id"]}],"errors":[],"effects":[]}


def model():
    return {"recovered_requirements":[{"name":"read","entry_points":["entry"], "external_outcomes":[{"entity_ref":"entry","expression":"{'id':1}","conditions":["flag"],"output_fields":["id"]}], "errors":[],"effects":[]}]}


def test_behavior_scoring_detects_reversed_condition_false_effect_and_missing_outcome():
    data=model();label=oracle()
    assert score_claims(data,[label])[0]["passed"]
    data["recovered_requirements"][0]["external_outcomes"][0]["conditions"]=["not flag"]
    data["recovered_requirements"][0]["effects"]=[{"entity_ref":"entry","callee":"store.delete","conditions":[]}]
    result=score_claims(data,[label])[0]
    assert not result["passed"]
    assert result["categories"]["outcomes"]["TP"]==0
    assert result["categories"]["outcomes"]["FP"]==result["categories"]["outcomes"]["FN"]==1
    assert result["categories"]["effects"]["FP"]==1


def test_conditions_normalize_predicates_without_reversing_or_erasing_meaning():
    assert predicate("not (not title)")==predicate("(title)")
    assert predicate("!(!req.title)")==predicate("req.title")
    assert predicate("!req.title")!=predicate("req.title")
    assert predicate("notabc")!=predicate("abc")
    a={"expression":"'a b'","conditions":[],"output_fields":[]}
    b={**a,"expression":"'ab'"}
    assert canonical(a,"outcomes")!=canonical(b,"outcomes")
    assert canonical({**a,"expression":"new Error('x')"},"outcomes")!=canonical({**a,"expression":"newError('x')"},"outcomes")


def test_compound_negation_and_other_language_precedence_are_not_erased():
    assert predicate('!a && b','javascript')!=predicate('!(a && b)','javascript')
    assert predicate('not a and b')!=predicate('not (a and b)')
    left={'expression':'a & b == c','conditions':[],'output_fields':[]}
    right={**left,'expression':'(a & b) == c'}
    assert canonical(left,'outcomes','javascript')!=canonical(right,'outcomes','javascript')
    call={**left,'conditions':['not(flag)'],'condition_predicates':[{'expression':'not(flag)','negated':False}]}
    negated={**left,'conditions':['not (flag)'],'condition_predicates':[{'expression':'flag','negated':True}]}
    assert canonical(call,'outcomes','javascript')!=canonical(negated,'outcomes','javascript')


def test_structured_predicate_cannot_override_visible_oracle_text():
    label=oracle();label['outcomes'][0]['condition_predicates']=[{'expression':'different','negated':False}]
    with pytest.raises(ValueError,match='displayed condition'):validate_oracles([label])


@pytest.mark.parametrize('left,right', [('`a  b`','`a b`'),('/a  b/','/a b/')])
def test_javascript_literal_whitespace_is_not_erased(left,right):
    row={'expression':left,'conditions':[],'output_fields':[]}
    assert canonical(row,'outcomes','javascript')!=canonical({**row,'expression':right},'outcomes','javascript')


def test_transitive_claims_are_visible_but_outside_local_oracle():
    data=model()
    data["recovered_requirements"][0]["effects"]=[{"entity_ref":"helper","callee":"db.save","conditions":[]}]
    result=score_claims(data,[oracle()])[0]
    assert result["passed"]
    assert result["categories"]["effects"]["precision"] is None
    assert result["transitive_claims_outside_oracle"]["effects"][0]["entity_ref"]=="helper"


@pytest.mark.parametrize("change",["missing-category","duplicate-predicate","unknown-category","invalid-category","duplicate-entry"])
def test_invalid_behavior_oracles_are_rejected(change):
    label=oracle();labels=[label]
    if change=="missing-category":del label["effects"]
    elif change=="duplicate-predicate":label["outcomes"].append({**label["outcomes"][0],"conditions":["not (not flag)"]})
    elif change=="unknown-category":label["closed"].append("security")
    elif change=="invalid-category":label["closed"].append({})
    elif change=="duplicate-entry":labels.append(deepcopy(label))
    with pytest.raises(ValueError):validate_oracles(labels)


def test_invalid_late_labels_preserve_existing_evaluation(tmp_path):
    corpus={"schema":"ases-document-corpus/1","label_review":"Own manual test oracle", "cases":[{"id":"one","files":{"api.py":"def read():\n    return 1\n"},"requirements":[]}]}
    path=tmp_path/'corpus.json';path.write_text(json.dumps(corpus));out=tmp_path/'results'
    evaluate_documents(path,out);saved=(out/'document-accuracy.json').read_bytes()
    corpus["cases"].append({"id":"bad","files":{"bad.py":"pass\n"},"requirements":[],"behaviors":[{"select":{"name":"x"}}]})
    path.write_text(json.dumps(corpus))
    with pytest.raises(ValueError):evaluate_documents(path,out)
    assert (out/'document-accuracy.json').read_bytes()==saved


def test_frozen_behavior_corpus_and_explanations(tmp_path):
    corpus=Path(__file__).parent/'fixture_documents/behavior-corpus.json'
    result=evaluate_documents(corpus,tmp_path/'evaluation')
    assert len(result['cases'])==11 and all(c['passed'] for c in result['cases'])
    categories=result['behavior_claims']['categories']
    assert categories['outcomes']['TP']==15
    assert categories['errors']['TP']==categories['effects']['TP']==1
    assert all(not r['FP'] and not r['FN'] for r in categories.values())
    guarded=next(c for c in result['cases'] if c['id']=='python-short-circuit-effect')['behaviors'][0]
    assert 'flag' in guarded['statement_it'] and 'può chiamare' in guarded['statement_it']
    assert 'Behavior outcomes' in (tmp_path/'evaluation/DOCUMENT-ACCURACY.md').read_text(encoding='utf-8')


def test_literal_false_and_nested_functions_do_not_supply_reachable_effects():
    node=ast.parse('def read():\n    if False:\n        db.delete()\n    def nested():\n        db.save()\n    return 1\n').body[0]
    facts=python_facts(node)
    assert not any(f['kind']=='call' for f in facts)
    assert [f['expression'] for f in facts if f['kind']=='return']==['1']


def test_javascript_short_circuit_and_rebound_response_parameter():
    source='function read(req,res){flag && store.delete();res=other;res.json({fake:true});}'
    tree=parse(source,'.js');node=next(n for n in walk(tree) if n.type in FUNCTIONS)
    facts=js_facts(node,http_handler=True)
    call=next(f for f in facts if f.get('callee')=='store.delete')
    assert call['conditions']==['flag']
    assert not any(f['kind']=='response' for f in facts)


def test_caught_error_and_finally_cleanup_preserve_exit_scope(tmp_path):
    root=tmp_path/'lib';root.mkdir()
    (root/'api.py').write_text('def recover():\n    try:\n        raise ValueError("handled")\n    except ValueError:\n        return 1\n\ndef finish(store):\n    try:\n        return {"id":1}\n    finally:\n        store.save()\n    store.delete()\n',encoding='utf-8')
    data=scan_project(root,tmp_path/'scan')['engineering_model']
    recover=next(r for r in data['recovered_requirements'] if r['name']=='recover')
    assert not recover['errors']
    assert any(f.get('caught_locally') for f in recover['facts'] if f['kind']=='throw')
    finish=next(r for r in data['recovered_requirements'] if r['name']=='finish')
    assert len(finish['external_outcomes'])==1 and finish['external_outcomes'][0]['conditions']==[]
    assert [f['callee'] for f in finish['effects']]==['store.save']


def test_source_disappearing_during_behavior_read_is_an_explicit_gap(tmp_path):
    from ases.engineering.behavior import recover_behavior_facts
    graph={'nodes':[{'id':'entry','kind':'function','name':'gone','path':'gone.py','metadata':{}}]}
    facts,coverage=recover_behavior_facts(tmp_path,{'source_manifest':[]},graph)
    assert not facts and coverage[0]['status']=='failed'


def test_dead_helper_is_not_reintroduced_through_structural_call_edges(tmp_path):
    root=tmp_path/'app';root.mkdir()
    (root/'api.py').write_text('from fastapi import FastAPI\napp=FastAPI()\ndef live():\n    return 1\ndef dead(store):\n    store.delete()\n    raise ValueError("unreachable helper")\n@app.get("/items")\ndef read(store):\n    live(); return {"id":1}; dead(store)\n',encoding='utf-8')
    model=scan_project(root,tmp_path/'scan')['engineering_model']
    row=next(r for r in model['recovered_requirements'] if r['name']=='GET /items')
    assert any(ref.endswith(':live') for ref in row['entity_refs'])
    assert not any(ref.endswith(':dead') for ref in row['entity_refs'])
    assert not row['effects'] and not row['errors']
    assert all('unreachable helper' not in f.get('expression','') for f in row['facts'])


def test_reachable_javascript_import_alias_keeps_its_helper_evidence(tmp_path):
    root=tmp_path/'app';root.mkdir()
    (root/'helper.js').write_text('export function original(){ return {value:1}; }',encoding='utf-8')
    (root/'api.js').write_text("import {original as alias} from './helper.js';\nexport function read(){ alias(); return {id:1}; }",encoding='utf-8')
    model=scan_project(root,tmp_path/'scan')['engineering_model']
    row=next(r for r in model['recovered_requirements'] if r['name']=='read')
    assert any(f.get('expression')=='{value:1}' for f in row['facts'])
    assert any(loc['path']=='helper.js' for loc in row['locations'])


def test_behavior_provenance_is_stable_between_hash_seeds(tmp_path):
    import os
    import subprocess
    import sys
    root=tmp_path/'app';root.mkdir()
    (root/'api.py').write_text('def one():\n    return 1\ndef two():\n    return 2\ndef combine():\n    one()\n    two()\n    return 3\n',encoding='utf-8')
    program='import json,sys;from pathlib import Path;from ases.pipeline import scan_project;m=scan_project(Path(sys.argv[1]),Path(sys.argv[2]))["engineering_model"];print(json.dumps({r["name"]:r["record_digest"] for r in m["recovered_requirements"]},sort_keys=True))'
    values=[]
    for seed in ('1','22'):
        env={**os.environ,'PYTHONHASHSEED':seed}
        result=subprocess.run([sys.executable,'-c',program,str(root),str(tmp_path/('scan-'+seed))],env=env,capture_output=True,text=True,check=True)
        values.append(json.loads(result.stdout))
    assert values[0]==values[1]
