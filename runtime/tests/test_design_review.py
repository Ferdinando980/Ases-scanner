"""Responsibility reviews: useful rationale without turning names into intent."""
from pathlib import Path
import json
import jsonschema

from ases.recovery.design_review import responsibility_reviews
from ases.pipeline import scan_project


def reviews(files):
    return responsibility_reviews([(Path(path), path, code) for path, code in files.items()])


HANDLERS = '''from . import operations
def upload(h, payload):
    result = operations.execute(payload)
    operations.persist(result)
    h._json(200, result)
def change(h, payload):
    result = operations.mutate(payload)
    operations.persist(result)
    h._json(200, result)
'''


def test_service_review_links_admitted_helper_and_preserves_uncertainty():
    rows = reviews({'app/routes.py':HANDLERS, 'app/operations.py':'def execute(payload): return payload\ndef mutate(payload): return payload\ndef persist(value): pass\n'})
    service = next(r for r in rows if r['rule_id']=='review.service_responsibilities')
    assert service['status']=='HINT'
    assert any(e.startswith('app/operations.py:') for e in service['evidence'])
    assert service['review']['verdict']=='INVESTIGATE'
    assert 'Duplic' not in service['review']['problem']['en']
    assert 'not established' in service['review']['questions']['en']
    assert 'funzione ordinaria' in service['review']['simpler_alternative']['it']


def test_delegating_handlers_single_handler_and_nested_examples_are_not_service_problem():
    thin='def upload(h, payload):\n    h._json(200, application.upload(payload))\ndef change(h, payload):\n    h._json(200, application.change(payload))\n'
    assert not reviews({'routes.py':thin})
    assert not reviews({'routes.py':HANDLERS.split('def change')[0]})
    assert not reviews({'routes.py':'example='+repr(HANDLERS)})
    nested='def outer():\n    def nested(h):\n        db.mutate(); db.persist(); h._json(200,{})\n    def other(h):\n        db.mutate(); db.persist(); h._json(200,{})\n'
    assert not reviews({'routes.py':nested})


def test_shadowed_import_and_duplicate_definitions_are_not_linked_as_helpers():
    for code in (HANDLERS.replace('(h, payload)', '(h, payload, operations)'),
                 HANDLERS.replace('from . import operations', 'from . import operations\noperations = another_object')):
        row=reviews({'app/routes.py':code,'app/operations.py':'def execute(x): pass\ndef persist(x): pass\n'})[0]
        assert all(e.startswith('app/routes.py:') for e in row['evidence'])
    rows=reviews({'app/routes.py':HANDLERS,'app/operations.py':'def execute(x): pass\ndef execute(x): pass\n'})
    assert not any(e.startswith('app/operations.py:') for e in rows[0]['evidence'])


def test_strategy_is_conditional_and_requires_same_receiver_and_output_role():
    code='''def answer(payload, query):
    if payload.provider == 'fast':
        result = query.fast()
    else:
        result = query.accurate()
    return result
'''
    row=reviews({'service.py':code})[0]
    assert row['rule_id']=='review.strategy_variants' and row['status']=='HINT'
    assert row['review']['verdict']=='INVESTIGATE'
    assert len(row['evidence'])==2
    assert not reviews({'service.py':code.replace('query.accurate()', 'other.accurate()')})
    assert not reviews({'service.py':code.replace('result = query.accurate()', 'other = query.accurate()')})
    assert not reviews({'service.py':code.replace('payload.provider', 'payload.color')})


def test_existing_registry_is_not_reported_as_missing_strategy():
    code='''def load_text(): pass
def load_query(): pass
def register():
    registry.register_provider('text', load_text)
    registry.register_provider('query', load_query)
'''
    row=reviews({'product.py':code})[0]
    assert row['rule_id']=='review.provider_registry' and row['status']=='OBSERVED'
    assert row['review']['verdict']=='REUSE_EXISTING'
    assert 'interchangeable' in row['review']['questions']['en']
    assert not reviews({'product.py':code.replace('load_query)', 'missing_loader)')})


def test_export_documents_and_ui_retain_review_rationale(tmp_path):
    root=tmp_path/'app';root.mkdir()
    (root/'routes.py').write_text(HANDLERS)
    result=scan_project(root,tmp_path/'scan')
    feed=json.loads((tmp_path/'scan/scanner-findings.json').read_bytes())
    schema=json.loads((Path(__file__).parents[2]/'schemas/scanner-findings.schema.json').read_bytes())
    jsonschema.validate(feed,schema)
    row=next(r for r in feed['hints'] if r['rule_id']=='review.service_responsibilities')
    assert row['design_review']['expected_benefit']['it']
    assert not any(r['status']=='OPPORTUNITY' for r in feed['findings'])
    from ases.renderers.markdown import recovered_odd
    text=recovered_odd(result['semantic_model'],{})
    assert 'Questions before deciding' in text and 'ordinary function' in text
    from ases.ui import build_report
    # The real pipeline exports the consumer context used by the UI.
    context=json.loads((tmp_path/'scan/consumer-context.v2.json').read_bytes())
    report=build_report(result,context,feed)
    assert report['design_reviews'][0]['design_review']['problem']['it']
    odd=(tmp_path/'scan/docs/ODD.md').read_text(encoding='utf-8')
    assert 'Ragionamento sul progetto' in odd and 'Domande prima di decidere' in odd
    assert 'Regole applicate: 1' in odd
    from ases.engineering.views import design_reasoning
    engineering=json.loads((tmp_path/'scan/engineering-model.json').read_bytes())
    assert 'Simplest alternative' in '\n'.join(design_reasoning(engineering,False))


def test_invalid_or_unadmitted_python_does_not_gain_a_review():
    assert not reviews({'bad.py':'def broken(: pass', 'fake.js':HANDLERS})
