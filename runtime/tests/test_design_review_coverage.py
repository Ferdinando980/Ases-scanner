import json
from pathlib import Path
import pytest

from ases.recovery.design_review import responsibility_reviews
from ases.quality_eval import evaluate_predictions
from ases.pipeline import scan_project

CASES=json.loads((Path(__file__).parent/'fixtures/design-review-cases.json').read_bytes())['cases']


@pytest.mark.parametrize('case',CASES,ids=lambda r:r['id'])
def test_controlled_review_oracles(case):
    observed=responsibility_reviews([(Path('app.py'),'app.py',case['source'])])
    result=evaluate_predictions({r['rule_id']+':'+r['status'] for r in observed},case)
    assert not result['false_positive'] and not result['false_negative'],result


def test_coverage_distinguishes_applied_unsupported_invalid_and_limits(monkeypatch):
    import ases.recovery.design_review as module
    coverage=[]
    files=[(Path('ok.py'),'ok.py','value=1'),(Path('bad.py'),'bad.py','def bad(:'),
           (Path('legacy.cs'),'legacy.cs','class Legacy {}'),(Path('large.py'),'large.py','#'+('x'*80))]
    monkeypatch.setattr(module,'MAX_BYTES',50)
    responsibility_reviews(files,coverage=coverage)
    assert {r['path']:(r['status'],r['reason']) for r in coverage}=={
        'ok.py':('ANALYZED','bounded_rules_applied'), 'bad.py':('UNKNOWN','python_syntax_unavailable'),
        'legacy.cs':('NOT_SUPPORTED','language_not_supported'),'large.py':('UNKNOWN','source_byte_limit')}
    monkeypatch.setattr(module,'MAX_NODES',1)
    coverage=[]
    responsibility_reviews(files[:1],coverage=coverage)
    assert coverage[0]['reason']=='syntax_node_limit' and coverage[0]['status']=='UNKNOWN'


def test_coverage_survives_scan_export_regeneration_and_old_snapshot(tmp_path):
    root=tmp_path/'app';root.mkdir()
    (root/'app.py').write_text('value=1')
    (root/'web.ts').write_text('const value=1;')
    (root/'legacy.cs').write_text('class Legacy {}')
    result=scan_project(root,tmp_path/'out')
    feed=json.loads((tmp_path/'out/scanner-findings.json').read_bytes())
    assert {r['status'] for r in feed['design_review_coverage']}=={'ANALYZED','NOT_SUPPORTED'}
    from ases.ui import build_report
    context=json.loads((tmp_path/'out/consumer-context.v2.json').read_bytes())
    report=build_report(result,context,feed)
    assert report['design_review_coverage']['counts']=={'ANALYZED':2,'NOT_SUPPORTED':1}
    feed.pop('design_review_coverage')
    assert build_report(result,context,feed)['design_review_coverage'] is None
    from ases.engineering.views import design_reasoning
    engineering=json.loads((tmp_path/'out/engineering-model.json').read_bytes())
    assert 'Non supportati: 1' in '\n'.join(design_reasoning(engineering,True))
    assert 'Not supported: 1' in '\n'.join(design_reasoning(engineering,False))
    assert 'Nessun suggerimento non significa nessun problema' in (tmp_path/'out/docs/ODD.md').read_text(encoding='utf-8')


def test_upstream_unknown_scope_is_not_reclassified_as_applied(tmp_path):
    from ases.model import FactGraph
    from ases.recovery.patterns import recover_pattern_findings
    (tmp_path/'app.py').write_text('value=1')
    graph=FactGraph(coverage={'app.py':{'status':'UNKNOWN'}})
    inventory={}
    recover_pattern_findings(tmp_path,graph,inventory)
    assert inventory['design_review_coverage'][0]['status']=='UNKNOWN'
