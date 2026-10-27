"""Behavioral checks for source assertions and inspectable constraint suggestions."""
import pytest

from ases.engineering.requirements import classify_statement, prose_requirement
from ases.engineering.model import interpret_sources


@pytest.mark.parametrize('statement,category', [
    ('The client should render updated data within 2s.', 'performance'),
    ('The service shall not block its event loop longer than 40ms.', 'performance'),
    ('Each document shall use at most 250MiB of memory.', 'capacity'),
    ('The service shall reject uploaded files larger than 8 MBs.', 'capacity'),
    ('The endpoint shall validate all inputs supplied by users.', 'security'),
    ('The renderer shall sanitize all inputs before inserting markup.', 'security'),
    ('The renderer shall escape HTML before producing a page.', 'security'),
    ('Only reviewers can access unpublished submissions.', 'security'),
    ('The application shall never write sensitive data to diagnostic logs.', 'security'),
    ('All executable packages shall be digitally signed.', 'security'),
    ('The service shall run in a sandbox separated from user content.', 'security'),
    ('The software build shall be reproducible.', 'maintainability'),
    ('The source shall be stored in a version control system.', 'maintainability'),
    ('Third-party dependencies shall be reviewed before building release artifacts.', 'maintainability'),
    ('The application shall support Firefox for its browser interface.', 'portability'),
    ('The product shall use readable navigation labels.', 'usability'),
    ('The display shall refresh every 15 seconds.', 'performance'),
    ('The site shall remain available 24 hours per day.', 'availability'),
    ('The product shall operate in offline mode during network outages.', 'reliability'),
    ('The user interface shall have a consistent colour scheme.', 'appearance'),
    ('The software shall follow the applicable accounting standards.', 'compliance'),
])
def test_explicit_constraints_have_inspectable_nonfunctional_signals(statement, category):
    result = classify_statement(statement)
    assert result['kind'] == 'nonfunctional'
    assert category in result['categories'] and result['evidence']
    assert all(value in statement for value in result['evidence'])
    assert result['origin'] == 'text-heuristic'


@pytest.mark.parametrize('statement', [
    'The system shall authenticate the user before showing private records.',
    'The form shall validate the invoice identifier.',
    'The application shall display a security report.',
    'The application shall export a performance report.',
    'The application shall display memory usage statistics.',
    'The interface shall display the size of the selected file.',
    'The editor shall focus the selected paragraph.',
    'The application shall persist the draft when the user saves it.',
])
def test_topic_names_and_ordinary_validation_are_not_quality_constraints(statement):
    assert classify_statement(statement)['kind'] == 'functional'


def test_source_declared_type_remains_authoritative_and_unknown_stays_unknown():
    assert classify_statement('The client shall respond within 2s.', 'Functional requirements')['kind'] == 'functional'
    result = classify_statement('The component shall meet the agreed condition.')
    assert result['kind'] == 'unspecified' and result['origin'] == 'unspecified'


@pytest.mark.parametrize('statement', [
    'Only the owner can delete an active workspace.',
    'A revoked account can only be restored by an administrator.',
    'The data returned by the endpoint are expressed in degrees Celsius.',
    'Out of 200 requests the service is available 199 times.',
    'Shall preserve an audit record for each rejected request.',
])
def test_restricted_capabilities_descriptions_and_partial_subjects_preserve_text(statement):
    source = {'id': 'd', 'path': 'docs/needs.md', 'sha256': 'a'*64, 'role': 'GUIDE', 'format': 'md',
              'units': [{'line': 1, 'text': statement}]}
    row = interpret_sources([source])['requirements'][0]
    assert row['statement'] == statement and row['satisfaction'] == 'not-verified'
    assert row['declared_id'] is None
    assert row['subject_missing'] is statement.startswith('Shall ')
    if ' can ' in statement: assert row['modality'] == 'capability'
    if ' are ' in statement or ' is available ' in statement: assert row['modality'] == 'stated-behavior'


@pytest.mark.parametrize('statement', [
    'Developers can run the example before installing the package.',
    'The project is maintained by several volunteers.',
    'Should we allow deletion of the entire workspace?',
    'A reviewer can provide useful feedback on this proposal.',
    'Must install Python before running the development examples.',
])
def test_general_project_prose_and_questions_are_not_recovered_needs(statement):
    assert prose_requirement(statement) is None
