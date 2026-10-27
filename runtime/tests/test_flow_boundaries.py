"""R3 admitted local paths must not hide unresolved compound-flow joins."""
import ast
import pytest
from ases.engineering.flow import python_facts, js_facts
from ases.scanners.javascript import parse, walk, FUNCTIONS
from ases.pipeline import scan_project


@pytest.mark.parametrize('suffix,source', [
    ('.py', 'def read(flag):\n    try:\n        return 1\n    finally:\n        if flag:\n            return 2\n'),
    ('.js', 'export function read(flag){try{return 1;}finally{if(flag)return 2;}}'),
])
def test_conditional_finally_withholds_prior_exit_instead_of_claiming_both(tmp_path, suffix, source):
    root=tmp_path/'source';root.mkdir();(root/('api'+suffix)).write_text(source,encoding='utf-8')
    row=scan_project(root,tmp_path/'scan')['engineering_model']['recovered_requirements'][0]
    assert [f['expression'] for f in row['external_outcomes']]==['2']
    prior=next(f for f in row['facts'] if f.get('expression')=='1')
    assert prior['withheld_by_partial_finally']
    assert any('Conditional finally' in limit for limit in row['flow_limits'])


@pytest.mark.parametrize('suffix,source', [
    ('.py', 'def read(flag):\n    try:\n        work()\n    finally:\n        if flag:\n            return 2\n    return 3\n'),
    ('.js', 'export function read(flag){try{work();}finally{if(flag)return 2;}return 3;}'),
])
def test_after_conditional_finally_continuation_is_explicitly_partial(tmp_path,suffix,source):
    root=tmp_path/'source';root.mkdir();(root/('api'+suffix)).write_text(source,encoding='utf-8')
    row=scan_project(root,tmp_path/'scan')['engineering_model']['recovered_requirements'][0]
    after=next(f for f in row['external_outcomes'] if f['expression']=='3')
    assert any(c.startswith('finally continuation partial;') for c in after['conditions'])
    assert 'parzialmente' in row['statement_it']


@pytest.mark.parametrize('source', [
    'def f(items):\n    for x in items:\n        break\n    return 1\n',
    'def f(items):\n    while items:\n        continue\n    return 1\n',
])
def test_python_loop_continuation_is_not_unconditional(source):
    row=next(f for f in python_facts(ast.parse(source).body[0]) if f['kind']=='return')
    assert any(c.startswith('loop continuation partial;') for c in row['conditions'])


@pytest.mark.parametrize('loop', ['while(flag){break;}', 'do {continue;} while(flag);', 'for(let i=0;i<3;i++){continue;}'])
def test_javascript_loop_continuation_is_not_unconditional(loop):
    tree=parse('function f(){'+loop+'return 1;}', '.js')
    node=next(n for n in walk(tree) if n.type in FUNCTIONS)
    row=next(f for f in js_facts(node) if f['kind']=='return')
    assert any(c.startswith('loop continuation partial;') for c in row['conditions'])


def test_switch_does_not_invent_unconditional_effects():
    tree=parse('function f(value){switch(value){case 1:store.save();break;default:store.delete();}return 1;}', '.js')
    node=next(n for n in walk(tree) if n.type in FUNCTIONS)
    facts=js_facts(node)
    assert not any(f['kind']=='call' for f in facts)
    assert any(f['kind']=='unsupported-flow' for f in facts)


def test_python_literal_false_loop_does_not_execute_body_syntax():
    facts=python_facts(ast.parse('def f():\n    while False:\n        store.delete()\n    return 1\n').body[0])
    assert not any(f['kind']=='call' for f in facts)


@pytest.mark.parametrize('assignment', ['exports.read', 'module.exports.read', 'reader'])
def test_static_function_assignment_keeps_body_and_syntax_identity(tmp_path,assignment):
    root=tmp_path/'source';root.mkdir()
    (root/'api.js').write_text(assignment+' = function(flag){if(flag)return 1;return 2;};',encoding='utf-8')
    model=scan_project(root,tmp_path/'scan')['engineering_model']
    name=assignment.rsplit('.',1)[-1]
    row=next(r for r in model['recovered_requirements'] if r['name']==name)
    assert [f['expression'] for f in row['external_outcomes']]==['1','2']
    api=next(r for r in model['api'] if r['name']==name)
    assert api['entity_ref'] and api['syntax_start_byte']>=0


def test_computed_assignment_name_is_not_guessed(tmp_path):
    root=tmp_path/'source';root.mkdir()
    (root/'api.js').write_text('exports[key] = function(){return 1;};',encoding='utf-8')
    model=scan_project(root,tmp_path/'scan')['engineering_model']
    assert not model['recovered_requirements']


@pytest.mark.parametrize('source,name', [('module.exports = function(flag){return flag ? 1 : 2;};','module.exports'),('export default function(flag){return flag ? 1 : 2;}', 'default')])
def test_default_exports_keep_explicit_syntactic_name(tmp_path,source,name):
    root=tmp_path/'source';root.mkdir();(root/'api.js').write_text(source,encoding='utf-8')
    model=scan_project(root,tmp_path/'scan')['engineering_model']
    row=next(r for r in model['recovered_requirements'] if r['name']==name)
    assert [f['expression'] for f in row['external_outcomes']]==['1','2']
