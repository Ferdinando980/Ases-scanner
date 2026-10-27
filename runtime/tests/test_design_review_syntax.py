from pathlib import Path
import json
import pytest

from ases.recovery.design_review import responsibility_reviews


def rows(code,suffix):
    coverage=[]
    result=responsibility_reviews([(Path('app'+suffix),'app'+suffix,code)],coverage=coverage)
    return result,coverage[0]


CASES=json.loads((Path(__file__).parent/'fixtures/design-review-syntax-cases.json').read_bytes())['cases']


@pytest.mark.parametrize('case',CASES,ids=lambda r:r['id'])
def test_public_native_review_oracles(case):
    from ases.quality_eval import evaluate_predictions
    result,_=rows(case['source'],case['suffix'])
    measured=evaluate_predictions({r['rule_id']+':'+r['status'] for r in result},case)
    assert not measured['false_positive'] and not measured['false_negative'],measured


@pytest.mark.parametrize('suffix',['.js','.ts','.tsx','.java'])
def test_strategy_alternatives_keep_shared_role_and_uncertainty(suffix):
    code='function run(provider,worker){let result;if(provider==="x"){result=worker.fast();}else{result=worker.slow();}return result;}'
    if suffix=='.java':code='class App { Object run(String provider, Worker worker){ Object result; if(provider.equals("x")){result=worker.fast();}else{result=worker.slow();}return result;} }'
    result,coverage=rows(code,suffix)
    assert coverage['status']=='ANALYZED'
    strategy=[r for r in result if r['rule_id']=='review.strategy_variants']
    assert strategy and strategy[0]['status']=='HINT'
    assert strategy[0]['review']['method']=='syntax-responsibilities/2'
    assert not rows(code.replace('worker.slow()', 'other.slow()'),suffix)[0]
    assert not rows(code.replace('result=worker.slow()', 'other=worker.slow()'),suffix)[0]


@pytest.mark.parametrize('suffix',['.js','.ts','.java'])
def test_branch_local_declarations_do_not_establish_common_output(suffix):
    code='function run(provider,worker){if(provider==="x"){const result=worker.fast();}else{const result=worker.slow();}}'
    if suffix=='.java':code='class App { void run(String provider,Worker worker){if(provider.equals("x")){Object result=worker.fast();}else{Object result=worker.slow();}}}'
    assert not rows(code,suffix)[0]


@pytest.mark.parametrize('suffix',['.js','.ts','.java'])
def test_service_responsibilities_require_multiple_mixed_handlers(suffix):
    code='function upload(res,memory,payload){const value=memory.ingest(payload);memory.save();res.status(200).json(value);}\nfunction change(res,memory,payload){const value=memory.mutate(payload);memory.save();res.status(200).json(value);}'
    if suffix=='.java':code='class App { Object upload(Memory memory, Object payload){Object value=memory.ingest(payload);memory.save();return ResponseEntity.ok(value);}\n Object change(Memory memory,Object payload){Object value=memory.mutate(payload);memory.save();return ResponseEntity.ok(value);} }'
    result,_=rows(code,suffix)
    assert any(r['rule_id']=='review.service_responsibilities' and r['status']=='HINT' for r in result)
    assert not rows(code.replace('memory.save();',''),suffix)[0]


@pytest.mark.parametrize('suffix',['.js','.ts','.java'])
def test_registry_is_existing_extensibility_and_keys_are_distinct(suffix):
    code='const loadText=()=>1; function loadQuery(){return 2;} function setup(registry){registry.registerProvider("text",loadText);registry.registerProvider("query",loadQuery);}'
    if suffix=='.java':code='class App { Object loadText(){return null;} Object loadQuery(){return null;} void setup(Registry registry){registry.registerProvider("text",this::loadText);registry.registerProvider("query",this::loadQuery);} }'
    result,_=rows(code,suffix)
    assert len(result)==1 and result[0]['status']=='OBSERVED'
    assert result[0]['review']['verdict']=='REUSE_EXISTING'
    assert not rows(code.replace('"query"','"text"'),suffix)[0]
    assert not rows(code.replace('this::loadQuery','this::missingLoader').replace(',loadQuery)',',missingLoader)'),suffix)[0]


def test_registry_does_not_mix_receivers_callables_or_shadowed_loaders():
    prefix='function loadText(){} function loadQuery(){} '
    for code in (
        'function setup(a,b){a.registerProvider("text",loadText);b.registerProvider("query",loadQuery);}',
        'function first(a){a.registerProvider("text",loadText);} function second(a){a.registerProvider("query",loadQuery);}',
        'function setup(a,loadQuery){a.registerProvider("text",loadText);a.registerProvider("query",loadQuery);}',
        'function setup(a){function loadQuery(){} a.registerProvider("text",loadText);a.registerProvider("query",loadQuery);}',
        'loadQuery=other; function setup(a){a.registerProvider("text",loadText);a.registerProvider("query",loadQuery);}',
        'function setup(a){a.registerProvider("text",loadText);a.registerProvider(\'text\',loadQuery);}',
    ):
        assert not rows(prefix+code,'.js')[0]


def test_python_registry_does_not_mix_scopes_or_shadowed_loaders():
    prefix='def load_text(): pass\ndef load_query(): pass\n'
    for code in (
        'def first(a):\n    a.register_provider("text",load_text)\ndef second(a):\n    a.register_provider("query",load_query)\n',
        'def setup(a,b):\n    a.register_provider("text",load_text)\n    b.register_provider("query",load_query)\n',
        'def setup(a,load_query):\n    a.register_provider("text",load_text)\n    a.register_provider("query",load_query)\n',
    ):
        assert not rows(prefix+code,'.py')[0]


def test_typed_async_typescript_and_java_overloaded_loaders_remain_distinct():
    code='async function run(provider: string, worker: Worker): Promise<Result> { if(provider==="x"){ return await worker.fast(); } else { return await worker.slow(); } }'
    assert rows(code,'.ts')[0][0]['rule_id']=='review.strategy_variants'
    overloaded='class App { Object loadText(){return null;} Object loadQuery(){return null;} Object loadQuery(int x){return null;} void setup(Registry registry){registry.registerProvider("text",this::loadText);registry.registerProvider("query",this::loadQuery);} }'
    assert not rows(overloaded,'.java')[0]


@pytest.mark.parametrize('suffix',['.js','.java'])
def test_compound_assignments_and_syntax_budgets_do_not_prove_alternatives(suffix,monkeypatch):
    code='function run(provider,worker){if(provider==="x"){result+=worker.fast();}else{result+=worker.slow();}}'
    if suffix=='.java':code='class App { void run(String provider,Worker worker){if(provider.equals("x")){result+=worker.fast();}else{result+=worker.slow();}}}'
    assert not rows(code,suffix)[0]
    import ases.recovery.design_review as module
    monkeypatch.setattr(module,'MAX_NODES',1)
    assert rows(code,suffix)[1]['status']=='UNKNOWN'
    assert rows(code,suffix)[1]['reason']=='syntax_node_limit'


@pytest.mark.parametrize('suffix',['.js','.ts','.java'])
def test_invalid_syntax_and_examples_are_not_architecture_evidence(suffix):
    assert rows('function broken( {',suffix)[1]['status']=='UNKNOWN'
    code='const example="if(provider){return worker.fast();}else{return worker.slow();}";'
    if suffix=='.java':code='class App { String example="if(provider){return worker.fast();}else{return worker.slow();}"; }'
    result,coverage=rows(code,suffix)
    assert not result and coverage['status']=='ANALYZED'
