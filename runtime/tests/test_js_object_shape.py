"""Local const shape support must cite declarations and withhold unsafe aliases."""
import pytest
from ases.pipeline import scan_project
from ases.engineering.flow import js_facts
from ases.scanners.javascript import parse,walk,FUNCTIONS

def facts(source):
    return js_facts(next(n for n in walk(parse(source,'.ts')) if n.type in FUNCTIONS))

def test_const_object_shape_has_both_return_and_declaration_evidence(tmp_path):
    root=tmp_path/'source';root.mkdir()
    (root/'api.ts').write_text('export function read(rest) {\n const result = {...rest, id:1, name:"demo"};\n return result;\n}',encoding='utf-8')
    model=scan_project(root,tmp_path/'scan')['engineering_model'];row=model['recovered_requirements'][0]
    outcome=row['external_outcomes'][0]
    assert outcome['expression']=='result' and outcome['output_fields']==['id','name']
    assert outcome['output_fields_complete'] is False and outcome['shape_source_line']==2
    assert 'elenco parziale' in row['statement_it']
    refs=row['explanation']['clauses'][0]['fact_refs'];support=[f for f in row['facts'] if f['fact_id'] in refs]
    assert {(f['kind'],f['line']) for f in support}=={('object-shape',2),('return',3)}
    assert model['behavior_profile']=='branch-local-flow/12' and model['narrative_profile']=='controlled-narrative/6'

@pytest.mark.parametrize('middle', ['result.id=2;', 'delete result.id;', 'mutate(result);', 'const alias=result;',
                                  'const wrap={result};', 'function nested(){return result;}',
                                  'if(flag){const result={fake:1};}', 'result=other;', 'eval("delete result.id");'])
def test_mutation_escape_shadowing_and_reassignment_withhold_shape(middle):
    values=facts('function read(flag){const result={id:1};'+middle+'return result;}')
    outcome=next(f for f in values if f['kind']=='return')
    assert outcome['output_fields']==[] and not outcome['output_fields_complete']
    assert not any(f['kind']=='object-shape' for f in values)

def test_mutable_conditional_and_factory_bindings_are_not_resolved():
    for source in ('function read(){let result={id:1};return result;}',
                   'function read(flag){if(flag){const result={id:1};return result;}return other;}',
                   'function read(){const result=make();return result;}'):
        assert all(not f['output_fields'] for f in facts(source) if f['kind']=='return')

def test_only_preceding_const_declarations_support_return_shapes():
    values=facts('function read(flag){if(flag)return result;const result={id:1};return result;}')
    returns=[f for f in values if f['kind']=='return']
    assert returns[0]['output_fields']==[] and returns[1]['output_fields']==['id']
    assert returns[1]['output_fields_complete'] is True

def test_direct_object_spreads_and_computed_keys_are_explicitly_partial():
    outcome=next(f for f in facts('function read(rest,key){return {...rest,id:1,[key]:2};}') if f['kind']=='return')
    assert outcome['output_fields']==['id'] and not outcome['output_fields_complete']

def test_same_line_declarations_cite_the_matching_object_only(tmp_path):
    root=tmp_path/'source';root.mkdir()
    (root/'api.js').write_text('export function read(flag){const first={id:1}, second={name:2};if(flag)return first;return second;}')
    row=scan_project(root,tmp_path/'scan')['engineering_model']['recovered_requirements'][0]
    for clause in row['explanation']['clauses']:
        support=[f for f in row['facts'] if f['fact_id'] in clause['fact_refs']]
        returned=next(f for f in support if f['kind']=='return')
        shape=next(f for f in support if f['kind']=='object-shape')
        assert shape['binding_name']==returned['expression']
        assert len(support)==2

@pytest.mark.parametrize('value', ['{__proto__: null,id:1}', '{"__proto__":null,id:1}', '{1e3:1,id:1}',
                                  r'{"a\u0062":1,id:1}', r'{a\u0062:1,id:1}'])
def test_prototype_and_coercion_or_escape_dependent_keys_are_not_invented(value):
    outcome=next(f for f in facts('function read(){return '+value+';}') if f['kind']=='return')
    assert outcome['output_fields']==['id'] and not outcome['output_fields_complete']

def test_quotes_inside_literal_keys_are_not_stripped():
    outcome=next(f for f in facts('''function read(){return {"'quoted'":1,"1":2};}''') if f['kind']=='return')
    assert outcome['output_fields']==["'quoted'",'1'] and outcome['output_fields_complete']

def test_proto_shorthand_is_a_normal_declared_own_property():
    outcome=next(f for f in facts('function read(__proto__){return {__proto__};}') if f['kind']=='return')
    assert outcome['output_fields']==['__proto__'] and outcome['output_fields_complete']
