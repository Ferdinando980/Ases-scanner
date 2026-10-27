"""Readable prose must preserve evidence and abstain from unsupported semantics."""
import pytest

from ases.engineering.prose import condition, expression, result_fields, possible_call
from ases.engineering.narrative import condition_text
from ases.pipeline import scan_project


@pytest.mark.parametrize(('source','language'), [
    ('richiesta["minuti"] < 15','python'),
    ('richiesta.minuti < 15','javascript'),
    ('richiesta.minuti < 15','java'),
])
def test_comparison_explains_field_and_boundary_instead_of_quoting_code(source, language):
    text = condition(source, source_language=language)
    assert 'minuti' in text and 'richiesta' in text and 'inferiore a 15' in text
    assert source not in text and 'valutato come' not in text


@pytest.mark.parametrize(('source','language'), [
    ('not disponibilita.libera(richiesta["sala_id"])','python'),
    ('!disponibilita.libera(richiesta.sala_id)','javascript'),
    ('!disponibilita.libera(richiesta.sala_id)','java'),
])
def test_negative_call_condition_stays_a_named_control_not_a_guessed_business_fact(source, language):
    text = condition_text([source], source_language=language)
    assert 'esito negativo' in text and 'libera' in text and 'disponibilita' in text
    assert source not in text and 'non è disponibile' not in text
    assert 'su il' not in text and 'a il' not in text and 'la verifica' in text


def test_negation_of_an_unknown_boolean_expression_is_not_moved_onto_one_operand():
    positive = condition_text(['a && b'], source_language='javascript')
    negative = condition_text(['!(a && b)'], source_language='javascript')
    assert 'non tradotto' in positive and 'esito positivo' in positive
    assert 'non tradotto' in negative and 'esito negativo' in negative
    assert '«a»' not in negative


def test_unknown_arithmetic_does_not_gain_numeric_semantics_or_leak_as_the_explanation():
    text = expression('left + right')
    assert 'non tradotta' in text and 'left + right' not in text and 'somma' not in text
    assert 'somma' in expression('1 + 2')


@pytest.mark.parametrize(('source','language'), [
    ('{"stato": "occupata"}','python'), ('{stato: "occupata"}','javascript'),
])
def test_literal_return_explains_the_status_value_not_only_field_names(source, language):
    assert result_fields(source,['stato'],language) == '«stato» vale «occupata»'


def test_field_values_are_not_guessed_from_a_binding_name_or_spread():
    assert result_fields('result',['stato']) == ''
    assert result_fields('{**other}',['stato']) == ''
    assert result_fields('{...other}',['stato'],'javascript') == ''


def test_possible_call_keeps_named_operation_without_asserting_it_completed():
    text = possible_call('registro.create')
    assert 'può chiamare' in text and '«create»' in text and '«registro»' in text
    assert 'registro.create' not in text and 'salvata' not in text


def test_bilingual_scan_and_documents_keep_original_facts_but_use_italian_explanations(tmp_path):
    root=tmp_path/'source';root.mkdir()
    original='richiesta["minuti"] < 15'
    (root/'servizio.py').write_text('def prenota_sala(richiesta, registro):\n    if '+original+':\n        raise ValueError("durata insufficiente")\n    registro.create(richiesta)\n    return {"stato": "confermata"}\n',encoding='utf-8')
    result=scan_project(root,tmp_path/'snapshot');model=result['engineering_model'];row=model['recovered_requirements'][0]
    assert model['narrative_profile']=='controlled-narrative/6'
    assert 'inferiore a 15' in row['statement_it'] and '«stato» vale «confermata»' in row['statement_it']
    assert 'durata insufficiente' in row['statement_it'] and 'il salvataggio permanente dei dati restano da verificare' in row['statement_it']
    assert 'registro.create' not in row['statement_it'] and original not in row['statement_it']
    assert any('richiesta' in f.get('expression','') and f['kind']=='branch' for f in row['facts'])
    assert any(f.get('callee')=='registro.create' for f in row['effects'])
    facts={f['fact_id'] for f in row['facts']}
    assert all(c['fact_refs'] and set(c['fact_refs'])<=facts for c in row['explanation']['clauses'])
    assert 'registro.create' in row['statement_en']
    for name in ('RAD.md','SDD.md','ODD.md'):
        text=(tmp_path/'snapshot/docs'/name).read_text(encoding='utf-8')
        assert 'Come leggere questo documento' in text
    rad=(tmp_path/'snapshot/docs/RAD.md').read_text(encoding='utf-8')
    assert row['statement_it'] in rad and 'Vedi la prova' in rad and 'registro.create' in rad
    assert row['authority']=='static-inference' and not model['requirements']


def test_multiline_literals_are_not_turned_into_document_headings():
    assert '\n#' not in expression(repr('line\n# Invented heading'))


@pytest.mark.parametrize('language', ['javascript','java'])
def test_foreign_escaped_literals_are_not_decoded_with_python_rules(language):
    assert 'non tradotta' in expression('"\\u0061"',language)


@pytest.mark.parametrize(('source','language'), [
    ('{"stato":"prima", "stato":"dopo"}','python'),
    ('{stato:"prima", stato:"dopo"}','javascript'),
    ('{"stato":"prima", **other}','python'),
    ('{stato:"prima", ...other}','javascript'),
    ('{[key]:"prima", stato:"dopo"}','javascript'),
])
def test_ambiguous_or_overridden_field_values_are_not_asserted(source, language):
    assert result_fields(source,['stato'],language) == ''


def test_complex_call_arguments_are_explicitly_deferred_to_evidence():
    assert 'argomenti indicati nella prova' in expression('check(first, second)')
    assert 'argomenti indicati nella prova' in expression('check(expected=True)')
    assert 'argomento da leggere nella prova' in expression('check(left + right)')
    text=expression('identificativo not in self.occupate')
    assert 'non appartiene al campo' in text and ' a il ' not in text
