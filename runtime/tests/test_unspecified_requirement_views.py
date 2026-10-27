from ases.engineering.render import render_documents
from ases.engineering.views import overview


def model():
    row = {
        'id': 'requirement:HTML-7', 'declared_id': 'HTML-7',
        'kind': 'unspecified', 'statement': '', 'authority': 'document-declaration',
        'satisfaction': 'not-verified', 'scope': 'document', 'fields': {'status': 'Active', 'title': 'Search'},
        'locations': [{'path': 'index.html', 'sha256': 'a' * 64, 'element': '12'}],
    }
    return {
        'snapshot_id': 'snapshot:test', 'model_digest': 'digest:test', 'requirements': [row],
        'user_requirements': [], 'operations': [], 'sources': [], 'excerpts': [], 'relations': [],
        'links': [], 'recovered_requirements': [], 'scenarios': [], 'structure': {'behaviors': [], 'components': [], 'tests': []},
        'api': [], 'test_cases': [], 'test_results': [], 'unknowns': [], 'coverage': {},
        'issues': [], 'quality_controls': [], 'test_plans': [],
    }


def test_unspecified_declaration_is_visible_in_rad_and_overview_in_both_languages():
    data = model()
    for language, heading, summary_heading in (
        ('it', 'Requisiti con tipo non dichiarato', 'Requisiti con tipo non dichiarato nella fonte'),
        ('en', 'Requirements without a declared kind', 'Requirements with no kind declared in source'),
    ):
        docs = render_documents(data, language)
        summary = overview(data, language == 'it')
        assert heading in docs['RAD.md']
        assert 'HTML-7' in docs['RAD.md']
        assert 'Active' in docs['RAD.md']
        assert 'not-verified' in docs['RAD.md']
        assert ('La fonte non contiene un enunciato' if language == 'it' else 'The source contains no requirement statement') in docs['RAD.md']
        assert summary_heading in summary and '| 1 |' in summary
