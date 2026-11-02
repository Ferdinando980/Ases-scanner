"""Ordinary actions count as features only when stated as modal predicates."""
import pytest

from ases.engineering.requirements import classify_statement


@pytest.mark.parametrize('statement', [
    'The analyst shall review every submitted request.',
    'The analyst shall carefully review every submitted request.',
    'The user must enter a valid code.',
    'The service shall log each rejected attempt.',
    'The client must supply the required details.',
    'The editor shall insert the selected value.',
    'The build tool must compile the project.',
    'The evaluator shall score each response.',
    'The administrator must maintain the account.',
    'The operator shall define a processing window.',
    'The interface must mark incomplete fields.',
    'The interface must contrassegnare i campi incompleti.',
    'The report shall indicate the current status.',
    'The user must change the selected option.',
    'The service shall end the active session.',
    'The service shall be able to review submitted requests.',
    "L'analista deve revisionare ogni richiesta inviata.",
    "L'utente deve inserire un codice valido.",
    'Il servizio deve registrare ogni tentativo rifiutato.',
    'Il client deve fornire i dettagli richiesti.',
    "L'editor deve inserire il valore selezionato.",
    'Lo strumento deve compilare il progetto.',
    'Il valutatore deve valutare ogni risposta.',
    "L'amministratore deve mantenere l'account.",
    "L'operatore deve definire una finestra di elaborazione.",
    "L'interfaccia deve indicare lo stato corrente.",
    'Il servizio deve terminare la sessione attiva.',
])
def test_ordinary_modal_predicate_actions_are_functional(statement):
    assert classify_statement(statement)['kind'] == 'functional'


@pytest.mark.parametrize('statement', [
    'The review shall satisfy the agreed condition.',
    'The system shall satisfy the review condition.',
    'The system shall satisfy the requested format.',
    'The request must remain available.',
    'The analyst reviews each case.',
    'A change in account status is described in the report.',
])
def test_action_nouns_and_unmodalized_descriptions_do_not_become_features(statement):
    assert classify_statement(statement)['kind'] == 'unspecified'


def test_quality_signal_precedes_new_modal_action():
    result = classify_statement('The reviewer shall review each clause within 2s.')
    assert result['kind'] == 'nonfunctional'
    assert 'performance' in result['categories']
    assert result['functional_evidence'] == ['review']


@pytest.mark.parametrize(('section', 'kind'), [
    ('Functional requirements', 'functional'),
    ('Non-functional requirements', 'nonfunctional'),
])
def test_declared_section_remains_authoritative_for_new_actions(section, kind):
    result = classify_statement('The reviewer shall review every request.', section)
    assert result['kind'] == kind
    assert result['origin'] == 'declared-section'
