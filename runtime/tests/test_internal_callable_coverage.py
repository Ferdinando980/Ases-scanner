"""Internal source bodies are inspectable without becoming public entry points."""

from ases.pipeline import scan_project


def analyze(tmp_path, name, text):
    source = tmp_path / 'src'
    source.mkdir()
    (source / name).write_text(text, encoding='utf-8')
    return scan_project(source, tmp_path / 'result.ases')['engineering_model']


def test_private_helper_is_local_and_does_not_import_callee_facts(tmp_path):
    model = analyze(tmp_path, 'api.py',
                    "def other(store):\n    store.save(1)\n    return 'other'\n"
                    "def _helper():\n    other(None)\n    return 'own'\n")
    record = next(x for x in model['recovered_requirements'] if x['name'] == '_helper')
    assert record['entry_scope'] == 'implementation-local'
    assert record['entry_visibility'] == 'private-convention'
    assert len(record['entity_refs']) == 1
    assert not record['effects']
    assert {x['expression'] for x in record['returns']} == {"'own'"}
    operation = next(x for x in model['operations'] if x['name'] == '_helper')
    assert operation['entry_scope'] == 'implementation-local'


def test_explicit_private_java_method_is_never_a_public_fallback(tmp_path):
    model = analyze(tmp_path, 'Api.java',
                    'public class Api { private int hidden() { return 3; } '
                    'public int visible() { return 4; } }')
    hidden = next(x for x in model['recovered_requirements'] if x['name'] == 'hidden')
    assert hidden['entry_scope'] == 'implementation-local'
    assert hidden['entry_visibility'] == 'private'
    assert hidden['coverage']['max_entities'] == 1
    assert not next(x for x in model['recovered_requirements'] if x['name'] == 'visible').get('entry_scope')


def test_conditional_module_homonyms_have_separate_bodies_and_context(tmp_path):
    model = analyze(tmp_path, 'api.py',
                    "if feature:\n    def select():\n        return 'yes'\n"
                    "else:\n    def select():\n        return 'no'\n"
                    "def caller():\n    return select()\n")
    records = [x for x in model['recovered_requirements'] if x['name'] == 'select']
    assert len(records) == 2
    assert len({x['entry_ref'] for x in records}) == 2
    assert all(x['entry_scope'] == 'conditional-local' for x in records)
    assert {x['declaration_context'][0]['branch'] for x in records} == {'then', 'else'}
    assert {x['returns'][0]['expression'] for x in records} == {"'yes'", "'no'"}
    caller = next(x for x in model['recovered_requirements'] if x['name'] == 'caller')
    assert not any(x['expression'] in {"'yes'", "'no'"} for x in caller['returns'])


def test_declaration_in_try_or_loop_is_not_promoted_to_always_available(tmp_path):
    model = analyze(tmp_path, 'api.py',
                    'try:\n    def from_try():\n        return 1\n'
                    'except Exception:\n    def from_handler():\n        return 2\n'
                    'for item in values:\n    def from_loop():\n        return 3\n')
    records = model['recovered_requirements']
    assert {x['name'] for x in records} == {'from_try', 'from_handler', 'from_loop'}
    assert all(x['entry_scope'] == 'conditional-local' for x in records)
    assert all(x['conditional_declaration'] for x in records)
    assert all(x['coverage']['max_call_depth'] == 0 for x in records)


def test_empty_body_has_position_bound_coverage_without_fake_requirement(tmp_path):
    model = analyze(tmp_path, 'Api.java', 'public class Api { public void flush() {} }')
    assert not model['recovered_requirements']
    coverage = next(x for x in model['behavior_coverage']
                    if x.get('body_evidence_status') == 'interpreted-no-admitted-facts')
    assert coverage['entity_ref'] and coverage['locations'][0]['line'] == 1
    assert 'no behavior' in coverage['reason']


def test_internal_js_name_has_own_body_summary(tmp_path):
    model = analyze(tmp_path, 'api.js', 'export function _identity(value) { return value; }')
    record = next(x for x in model['recovered_requirements'] if x['name'] == '_identity')
    assert record['entry_scope'] == 'implementation-local'
    assert record['coverage']['max_call_depth'] == 0
    assert record['returns'][0]['expression'] == 'value'


def test_conditional_redefinition_does_not_reuse_unconditional_call_binding(tmp_path):
    model = analyze(tmp_path, 'api.py',
                    "def select():\n    return 'original'\n"
                    "if feature:\n    def select():\n        return 'replacement'\n"
                    "def caller():\n    return select()\n")
    caller = next(x for x in model['recovered_requirements'] if x['name'] == 'caller')
    assert len(caller['entity_refs']) == 1
    assert {x['expression'] for x in caller['returns']} == {'select()'}
    assert all(x['expression'] not in {"'original'", "'replacement'"} for x in caller['returns'])


def test_conditional_factory_context_reaches_descendant_route_decorators(tmp_path):
    source = tmp_path / 'src'
    source.mkdir()
    (source / 'api.py').write_text(
        "from flask import Flask\napp = Flask(__name__)\n"
        "if enabled:\n    def factory():\n"
        "        def middle():\n"
        "            @app.get('/conditional')\n"
        "            def handler():\n                return 'inner'\n"
        "            return handler\n        return middle\n", encoding='utf-8')
    result = scan_project(source, tmp_path / 'result.ases')
    assert not any(x['kind'] == 'route' for x in result['graph']['nodes'])
    model = result['engineering_model']
    handler = next(x for x in model['api'] if x['qualified_name'] == 'factory.middle.handler')
    assert handler['conditional_declaration'] is True
    assert handler['declaration_context'] == [{'kind':'if', 'expression':'enabled', 'branch':'then', 'line':3}]
    summary = next(x for x in model['recovered_requirements'] if x['name'] == 'handler')
    assert summary['entry_scope'] == 'conditional-local'
    assert summary['conditional_declaration'] is True
    assert 'non è stabilito' in summary['statement_it']


def test_internal_functions_never_displace_primary_entry_budget(tmp_path):
    text = ''.join(f'def _helper_{n}():\n    return {n}\n' for n in range(1002))
    text += 'def public_entry():\n    return 99\n'
    model = analyze(tmp_path, 'api.py', text)
    records = model['recovered_requirements']
    assert len(records) == 1000
    assert any(x['name'] == 'public_entry' and not x.get('entry_scope') for x in records)
    assert sum(x.get('entry_scope') == 'implementation-local' for x in records) == 999
    assert any('3 excluded by the 1000-entry budget' in x.get('reason', '') for x in model['behavior_coverage'])


def test_conditional_context_change_requires_document_review(tmp_path):
    from ases.engineering.model import engineering_diff
    source = tmp_path / 'src'
    source.mkdir()
    f = source / 'api.py'
    f.write_text('if flag:\n    def select():\n        return 1\n', encoding='utf-8')
    before = scan_project(source, tmp_path / 'before.ases')['engineering_model']
    f.write_text('if enabled:\n    def select():\n        return 1\n', encoding='utf-8')
    after = scan_project(source, tmp_path / 'after.ases')['engineering_model']
    record = next(x for x in after['recovered_requirements'] if x['name'] == 'select')
    delta = engineering_diff(before, after)
    assert record['id'] in delta['changed_supported_fields']
    assert 'RAD' in delta['sections_to_review']
    assert 'condizionale' in record['statement_it']
    assert 'internal' in record['statement_en']
