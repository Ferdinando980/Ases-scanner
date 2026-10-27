from ases.pipeline import scan_project


def test_typescript_overload_signatures_do_not_claim_the_implementation_identity(tmp_path):
    root=tmp_path/'source';root.mkdir()
    (root/'api.ts').write_text('''export class Store {
  save(value: string): string;
  save(value: number): number;
  save(value: string | number) { return this.target.save(value); }
}
''',encoding='utf-8')
    model=scan_project(root,tmp_path/'scan')['engineering_model']
    declarations=[r for r in model['api'] if r['name']=='save']
    assert len(declarations)==3
    signatures=[r for r in declarations if r['syntax_start_byte'] is None]
    implementation=next(r for r in declarations if r['syntax_start_byte'] is not None)
    assert len(signatures)==2 and all(r['entity_ref'] is None for r in signatures)
    assert implementation['entity_ref'] and len({r['id'] for r in declarations})==3
    behavior=next(r for r in model['recovered_requirements'] if r['name']=='save')
    assert behavior['entry_points']==[implementation['entity_ref']]
    assert behavior['external_outcomes'][0]['expression']=='this.target.save(value)'
    assert behavior['effects'][0]['callee']=='this.target.save'


def test_interface_signature_is_not_attached_to_an_unrelated_same_named_body(tmp_path):
    root=tmp_path/'source';root.mkdir()
    (root/'api.ts').write_text('''export interface Contract { read(value: string): string; }
export class Store { read(value: string) { return value; } }
''',encoding='utf-8')
    model=scan_project(root,tmp_path/'scan')['engineering_model']
    rows=[r for r in model['api'] if r['name']=='read']
    signature=next(r for r in rows if r['owner']=='Contract')
    implementation=next(r for r in rows if r['owner']=='Store')
    assert signature['entity_ref'] is None and implementation['entity_ref']
    assert len([r for r in model['recovered_requirements'] if r['name']=='read'])==1


def test_bare_java_candidate_calls_keep_local_conditions_and_do_not_imply_execution(tmp_path):
    root=tmp_path/'source';root.mkdir()
    (root/'Store.java').write_text('''public class Store {
 public int read(boolean flag) { if(flag) { return remove(1); } return 0; }
 public int remove(int key) { return key; }
 public int dead() { return 1; remove(2); }
}
''',encoding='utf-8')
    model=scan_project(root,tmp_path/'scan')['engineering_model']
    row=next(r for r in model['recovered_requirements'] if r['name']=='read')
    local=[f for f in row['effects'] if f['entity_ref'] in row['entry_points']]
    assert [(f['callee'],f['conditions']) for f in local]==[('remove',['flag'])]
    assert 'può chiamare' in row['statement_it']
    assert not next(r for r in model['recovered_requirements'] if r['name']=='dead')['effects']


def test_bare_python_and_js_calls_do_not_expand_the_java_candidate_profile(tmp_path):
    root=tmp_path/'source';root.mkdir()
    (root/'api.py').write_text('def read():\n    return save(1)\n',encoding='utf-8')
    (root/'api.js').write_text('export function readJs(){return save(1);}',encoding='utf-8')
    model=scan_project(root,tmp_path/'scan')['engineering_model']
    assert all(not r['effects'] for r in model['recovered_requirements'])
