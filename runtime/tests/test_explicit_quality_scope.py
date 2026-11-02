"""Explicit quality constraints must be distinguished from quality topics."""

import pytest

from ases.engineering.requirements import classify_statement


@pytest.mark.parametrize(('statement', 'category'), [
    # Security obligations: a control is imposed on system behavior.
    ('The service must protect stored reports from automated attacks.', 'security'),
    ('Private records are accessible only to authorized staff.', 'security'),
    ('Access to the archive shall be restricted to accounts with assigned permissions.', 'security'),
    ('Users must provide a username and a password before opening the workspace.', 'security'),
    ('Authentication and authorization are required before a user can open restricted records.', 'security'),
    ('Il servizio deve proteggere i dati archiviati dagli attacchi automatizzati.', 'security'),
    ('I documenti riservati sono accessibili solo al personale autorizzato.', 'security'),
    ('L’accesso all’archivio deve essere limitato agli account con permessi assegnati.', 'security'),
    ('Gli utenti devono inserire un nome utente e una password prima di aprire l’area di lavoro.', 'security'),
    ('Autenticazione e autorizzazione sono richieste prima di aprire i documenti riservati.', 'security'),
    # Usability obligations: concrete interaction, novice success, or assistance.
    ('An operator must be able to complete the intake using a mouse or keyboard.', 'usability'),
    ('At least 80% of novice users shall be able to use the scheduling screen.', 'usability'),
    ('The help section shall explain what to do when users have difficulty using the importer.', 'usability'),
    ('Un operatore deve poter completare la richiesta usando il mouse o la tastiera.', 'usability'),
    ('Almeno l’80% degli utenti principianti deve poter usare la schermata di pianificazione.', 'usability'),
    ('La sezione di aiuto deve spiegare come procedere quando gli utenti incontrano difficoltà nell’uso dell’importatore.', 'usability'),
    # Portability and cadence constraints.
    ('The application shall be platform independent.', 'portability'),
    ('L’applicazione deve essere indipendente dalla piattaforma.', 'portability'),
    ('Software updates shall take one day to complete.', 'performance'),
    ('Le operazioni di aggiornamento devono richiedere un giorno.', 'performance'),
    ('The service shall run its periodic queries once a week.', 'performance'),
    ('Il servizio deve eseguire le interrogazioni periodiche una volta alla settimana.', 'performance'),
])
def test_explicit_quality_constraints_are_classified_with_literal_evidence(statement, category):
    result = classify_statement(statement)

    assert result['kind'] == 'nonfunctional'
    assert result['origin'] == 'text-heuristic'
    assert category in result['categories']
    assert result['evidence']
    assert all(reason in statement for reason in result['evidence'])


@pytest.mark.parametrize('statement', [
    'The dashboard shall display reports about protection from automated attacks.',
    'The catalog shall export a list of authorized staff and their permissions.',
    'The account page shall display the username and password policy.',
    'Il cruscotto deve mostrare un rapporto sugli attacchi automatizzati.',
    'Il catalogo deve esportare l’elenco del personale autorizzato e dei relativi permessi.',
    'La pagina dell’account deve mostrare la politica per nome utente e password.',
])
def test_security_topics_that_are_only_reported_remain_functional(statement):
    assert classify_statement(statement)['kind'] == 'functional'


@pytest.mark.parametrize('statement', [
    'The dashboard shall display the percentage of novice users who can use the screen with a mouse or keyboard.',
    'The help section shall export a report about users who experienced difficulties with the importer.',
    'Il cruscotto deve mostrare la percentuale di utenti principianti che sanno usare la schermata con mouse o tastiera.',
    'La sezione di aiuto deve esportare un rapporto sulle difficoltà incontrate dagli utenti con l’importatore.',
    'The settings page shall display whether the application is platform independent.',
    'The report shall export the planned update duration and weekly query schedule.',
    'La pagina delle impostazioni deve mostrare se l’applicazione è indipendente dalla piattaforma.',
    'Il rapporto deve esportare la durata pianificata degli aggiornamenti e il calendario settimanale delle interrogazioni.',
])
def test_reported_quality_topics_do_not_become_imposed_constraints(statement):
    assert classify_statement(statement)['kind'] == 'functional'


@pytest.mark.parametrize(('section', 'kind'), [
    ('Functional requirements', 'functional'),
    ('Non-functional requirements', 'nonfunctional'),
    ('Requisiti funzionali', 'functional'),
    ('Requisiti non funzionali', 'nonfunctional'),
])
def test_declared_section_remains_authoritative_for_explicit_quality_language(section, kind):
    result = classify_statement(
        'The service must protect stored reports from automated attacks and complete updates in one day.',
        section,
    )

    assert result['kind'] == kind
    assert result['origin'] == 'declared-section'
    assert result['evidence'] == [section]


def test_reporting_measured_usability_is_distinct_from_imposing_a_success_rate():
    statement = 'The dashboard shall display a report stating that 85% of customers are comfortable using the portal.'
    assert classify_statement(statement)['kind'] == 'functional'
    imposed = 'At least 85% of customers shall be comfortable using the portal.'
    assert classify_statement(imposed)['kind'] == 'nonfunctional'
    survey = 'A survey will show that 85% of customers are comfortable using the portal.'
    assert classify_statement(survey)['kind'] == 'nonfunctional'
    bounded = statement.rstrip('.') + ' within 300ms.'
    assert 'performance' in classify_statement(bounded)['categories']
