"""Physical template line terminators differ from explicit escape sequences."""
import pytest
from ases.engineering.claim_evaluation import expression, score_claims


@pytest.mark.parametrize('terminator', ['\r\n', '\r'])
@pytest.mark.parametrize('prefix', ['', 'String.raw'])
def test_js_template_physical_line_terminators_follow_template_values(terminator, prefix):
    source = prefix + '`first' + terminator + 'second ${name}`'
    expected = prefix + '`first\nsecond ${name}`'
    assert expression(source, 'javascript') == expression(expected, 'javascript')


def test_js_template_escaped_carriage_return_stays_distinct():
    assert expression(r'`first\r\nsecond`', 'javascript') != expression('`first\nsecond`', 'javascript')
    assert expression(r'String.raw`first\nsecond`', 'javascript') != expression('String.raw`first\nsecond`', 'javascript')


def test_template_literal_spaces_are_not_erased_and_method_is_reported():
    assert expression('`first second`', 'javascript') != expression('`first  second`', 'javascript')
    label = {'select': {'name': 'read'}, 'oracle': 'Explicit no-throw local body.',
             'closed': ['errors'], 'errors': []}
    result = score_claims({'recovered_requirements': [{'name': 'read'}]}, [label])
    assert result[0]['expression_profile'] == 'syntax-tokens/3'
