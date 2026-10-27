"""R3 Java local-flow scope: inspectable paths, plus close negative cases."""
import pytest

from ases.engineering.behavior import java_facts
from ases.pipeline import scan_project


def returns(source):
    return [f for f in java_facts(source) if f['kind'] == 'return']


def scan(tmp_path, text):
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'Api.java').write_text(text, encoding='utf-8')
    return scan_project(source, tmp_path / 'result.ases')['engineering_model']


def test_early_exit_paths_and_dead_calls():
    facts = java_facts('{ if (bad) throw new Error("x"); if (empty) return 0; store.save(value); return 1; store.delete(value); }')
    assert [(f['expression'], f['conditions']) for f in facts if f['kind'] == 'return'] == [
        ('0', ['not (bad)', 'empty']), ('1', ['not (bad)', 'not (empty)'])]
    assert [(f['callee'], f['conditions']) for f in facts if f['kind'] == 'call'] == [('store.save', ['not (bad)', 'not (empty)'])]
    error = next(f for f in facts if f['kind'] == 'throw')
    assert error['expression'] == 'new Error("x")' and error['conditions'] == ['bad']


@pytest.mark.parametrize('body', [
    '{ if (ok) return 1; else return 2; return 3; }',
    '{ if (ok) { return 1; } else { return 2; } return 3; }',
    '{ return ok ? 1 : 2; return 3; }',
])
def test_alternatives_terminate_and_preserve_predicates(body):
    assert [(f['expression'], f['conditions']) for f in returns(body)] == [('1', ['ok']), ('2', ['not (ok)'])]


@pytest.mark.parametrize('operator,guard', [('&&', 'ok'), ('||', 'not (ok)')])
def test_short_circuit_calls(operator, guard):
    facts = java_facts('{ boolean changed = ok ' + operator + ' store.save(value); return changed; }')
    call = next(f for f in facts if f['kind'] == 'call')
    assert call['callee'] == 'store.save' and call['conditions'] == [guard]


def test_string_comments_text_block_and_unicode_are_inert():
    facts = java_facts('{ String text = "return 9;"; String block = """\nthrow new Danger();\n"""; /* return 8; */ return "caffè"; }', 12)
    assert [(f['expression'], f['line']) for f in facts if f['kind'] == 'return'] == [('"caffè"', 15)]
    assert not any(f['kind'] == 'throw' for f in facts)


def test_nested_lambdas_and_anonymous_classes_do_not_supply_outer_exits():
    facts = java_facts('{ Runnable r = () -> { store.delete(value); throw new Danger(); }; Object x = new Object() { public int inner() { return 7; } }; class Local { int inner() { return 8; } } return 1; }')
    assert [f['expression'] for f in facts if f['kind'] == 'return'] == ['1']
    assert not any(f['kind'] in {'throw', 'call'} for f in facts)


@pytest.mark.parametrize('compound', [
    'while (ready) { return 9; }', 'for (int i=0; i<3; i++) { return 9; }',
    'for (Object x : items) { return 9; }', 'do { return 9; } while (ready);',
    'switch (value) { case 1: return 9; default: break; }',
    'try { return 9; } finally { if (override) return 8; }',
    'try { throw new Error(); } catch (Error e) { return 9; }',
    'try (Resource r = open()) { return 9; }',
    'synchronized (lock) { return 9; }',
    'label: { return 9; }',
    'assert store.save(value);',
])
def test_unresolved_compound_joins_do_not_flatten_inner_exits(compound):
    facts = java_facts('{ ' + compound + ' return 1; }')
    assert any(f['kind'] == 'unsupported-flow' for f in facts)
    assert [f['expression'] for f in facts if f['kind'] == 'return'] == ['1']
    assert next(f for f in facts if f['kind'] == 'return')['conditions'][0].startswith('Java control flow partial;')
    assert not any(f['kind'] == 'throw' for f in facts)


def test_switch_expression_does_not_invent_unconditional_calls():
    facts = java_facts('{ return switch (value) { case 1 -> store.save(value); default -> 0; }; }')
    assert any(f['kind'] == 'unsupported-flow' for f in facts)
    assert not any(f['kind'] == 'call' for f in facts)


def test_malformed_body_withholds_claims():
    facts = java_facts('{ if ( }')
    assert len(facts) == 1 and facts[0]['kind'] == 'unsupported-flow'


def test_fact_and_depth_limits_are_reported():
    facts = java_facts('{ ' + 'store.save(value);' * 600 + ' }')
    assert len(facts) == 500 and facts[-1]['kind'] == 'unsupported-flow'
    nested = '{ ' + 'if (ok) {' * 150 + 'return 1;' + '}' * 150 + ' }'
    facts = java_facts(nested)
    assert any('depth limit' in f.get('expression', '') for f in facts)
    assert not any(f['kind'] == 'return' for f in facts)


def test_abstract_method_cannot_borrow_next_method_body(tmp_path):
    model = scan(tmp_path, 'public abstract class Api {\n public abstract int absent();\n public int present() { return 7; }\n}')
    rows = model['recovered_requirements']
    assert [r['name'] for r in rows] == ['present']
    assert rows[0]['external_outcomes'][0]['expression'] == '7'


def test_same_line_overloads_are_left_unresolved(tmp_path):
    model = scan(tmp_path, 'public class Api { public int value() { return 1; } public int value(int x) { return 2; } }')
    assert not model['recovered_requirements']
    assert any('not uniquely located' in c['reason'] for c in model['behavior_coverage'])


def test_method_location_uses_unicode_safe_syntax_coordinates(tmp_path):
    model = scan(tmp_path, '// caffè 🍵\npublic class Api {\n @Deprecated\n public int answer() { return 42; }\n}')
    row = next(r for r in model['recovered_requirements'] if r['name'] == 'answer')
    assert row['external_outcomes'][0]['expression'] == '42'
    assert row['external_outcomes'][0]['line'] == 4
    assert model['behavior_profile'] == 'branch-local-flow/12'
    assert model['behavior_parser_profiles']['java']['method'] == 'java-local-flow/1'


def test_dead_java_helper_is_not_reintroduced_by_structural_links(tmp_path):
    model = scan(tmp_path, 'class Worker {\n public int write() { store.save(1); return 2; }\n}\npublic class Api {\n private Worker worker;\n public int answer() { return 1; worker.write(); }\n}')
    row = next(r for r in model['recovered_requirements'] if r['name'] == 'answer')
    assert not row['effects']
    assert not any('Worker#write' in ref for ref in row['entity_refs'])


def test_parser_change_requests_document_review_even_without_source_changes():
    from ases.engineering.model import engineering_diff
    base = {'behavior_profile': 'branch-local-flow/3', 'behavior_parser_profiles': {'java': {'grammar': 'old'}}}
    after = {**base, 'behavior_parser_profiles': {'java': {'grammar': 'new'}}}
    delta = engineering_diff(base, after)
    assert delta['behavior_parser_changed'] and not delta['behavior_method_changed']
    assert set(delta['sections_to_review']) == {'RAD', 'SDD', 'ODD'}


def test_javadoc_cannot_create_a_second_owner_and_hide_methods(tmp_path):
    model = scan(tmp_path, '/** This class enforces limits. */\npublic class Api {\n public int answer() { return 1; }\n}')
    row = next(r for r in model['recovered_requirements'] if r['name'] == 'answer')
    assert row['external_outcomes'][0]['expression'] == '1'
    assert not any(r.get('name') == 'enforces' for r in model['api'])


@pytest.mark.parametrize('language', ['java', 'javascript'])
def test_python_precedence_is_not_used_to_explain_other_languages(language):
    from ases.engineering.behavior import explain_expression
    # In Java/JS, equality binds tighter than bitwise &, unlike Python.
    value = explain_expression('a & b == c', source_language=language)
    assert 'confronto' not in value and 'non tradotta' in value and 'a & b == c' not in value
