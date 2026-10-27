"""Quality obligations and feature topics must not be confused."""
import pytest

from ases.engineering.requirements import classify_statement


@pytest.mark.parametrize('statement,category', [
    ('The query must finish in an acceptable time.', 'performance'),
    ('The recovery job shall take no more than 12min.', 'performance'),
    ('The renderer shall minimize processing overhead.', 'performance'),
    ('The transport shall implement load balancing across workers.', 'performance'),
    ('The operator shall complete the checklist in a timely manner.', 'performance'),
    ('Technical support shall be available for 12 hours.', 'availability'),
    ('The site shall continue to work when an upstream service fails.', 'reliability'),
    ('The archive must prevent corrupt data from being stored.', 'reliability'),
    ('Only auditors shall inspect confidential transaction records.', 'security'),
    ('Unverified accounts must not have access to payroll records.', 'security'),
    ('One tenant shall not retrieve another tenant data.', 'security'),
    ('The platform must handle at least 25 000 customers.', 'scalability'),
    ('The processor shall handle a minimum of 2 million transactions per year.', 'scalability'),
    ('The server shall allow 80 users to work at the same time.', 'scalability'),
    ('Application updates shall occur during the agreed maintenance period.', 'maintainability'),
    ('All changes must appear in system documentation before release.', 'maintainability'),
    ('The service shall work with multiple database management systems.', 'portability'),
    ('The program must operate on each supported platform.', 'portability'),
    ('The software must be written using the approved runtime libraries.', 'portability'),
    ('Users should create a ticket in at most 3 clicks.', 'usability'),
    ('At least 80% of surveyed users shall feel satisfied with navigation.', 'usability'),
    ('The interface must use the agreed branding guidelines.', 'appearance'),
    ('The dashboard must use a 1280 by 720 pixel resolution.', 'appearance'),
    ('Il servizio deve completare la ricerca entro 15ms.', 'performance'),
    ('Il modulo deve consentire la conferma in al massimo 2 clic.', 'usability'),
])
def test_constraint_signals_keep_exact_source_reasons(statement, category):
    result = classify_statement(statement)
    assert result['kind'] == 'nonfunctional'
    assert category in result['categories']
    assert all(reason in statement for reason in result['evidence'])
    assert result['profile'] == 'constraint-signals/3'


@pytest.mark.parametrize('statement', [
    'The application shall display customer satisfaction statistics.',
    'The dashboard shall show latency and throughput measurements.',
    'The form shall record the number of mistakes in a submitted exercise.',
    'The system shall export the database management systems inventory.',
    'The application shall display a load balancing report.',
    'The editor shall reset the current selection.',
    'The application shall offer the ability to pause the transfer.',
    'The search shall locate the record with the chosen identifier.',
    'The importer shall merge the selected datasets.',
])
def test_features_and_metric_reports_remain_functional(statement):
    assert classify_statement(statement)['kind'] == 'functional'


def test_exposing_metric_does_not_erase_a_separate_constraint():
    result = classify_statement('The dashboard shall display latency statistics within 200ms.')
    assert result['kind'] == 'nonfunctional'
    assert 'performance' in result['categories']
    assert any('200ms' in reason for reason in result['evidence'])


def test_declared_authority_and_unknowns_survive_expanded_signals():
    statement = 'The program must work with several database management systems.'
    assert classify_statement(statement, 'Functional requirements')['origin'] == 'declared-section'
    assert classify_statement(statement, 'Functional requirements')['kind'] == 'functional'
    assert classify_statement('The component shall meet the agreed condition.')['kind'] == 'unspecified'
