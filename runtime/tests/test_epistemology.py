from pathlib import Path
import json
from ases.diffing import diff_findings
from ases.pipeline import scan_project


def test_stable_pattern_fingerprint_ignores_line_number(tmp_path):
    root=tmp_path/'repo'; root.mkdir()
    src=root/'Game.java'
    src.write_text('class Game { void run(Mode mode) { switch (mode) { case A: a(); break; case B: b(); break; case C: c(); break; } } }')
    a=scan_project(root,tmp_path/'a')['semantic_model']
    first=next(x for x in a['pattern_findings'] if x['status'] in {'OPPORTUNITY','HINT'})
    src.write_text('\n\n'+src.read_text())
    b=scan_project(root,tmp_path/'b')['semantic_model']
    second=next(x for x in b['pattern_findings'] if x['rule_id']==first['rule_id'])
    assert first['fingerprint']==second['fingerprint']


def test_diff_uses_fingerprints():
    before={'findings':[{'id':'old','fingerprint':'abc','status':'OBSERVED','confidence':'high','message':'x','counter_evidence':[],'evidence':['A.java:1']}],'hints':[]}
    after={'findings':[{'id':'new','fingerprint':'abc','status':'OBSERVED','confidence':'high','message':'x','counter_evidence':[],'evidence':['A.java:9']}],'hints':[]}
    report=diff_findings(before,after)
    assert report['summary']['new']==0
    assert report['summary']['resolved']==0
    assert report['summary']['changed']==0
    assert report['summary']['unchanged']==1


def test_asesignore_marks_finding_suppressed(tmp_path):
    root=tmp_path/'repo'; root.mkdir()
    (root/'Game.java').write_text('class Game { void run(Mode mode) { switch (mode) { case A: a(); break; case B: b(); break; case C: c(); break; } } }')
    (root/'.asesignore').write_text('opportunity.strategy_dispatch | intentionally kept simple\n')
    out=tmp_path/'out'; scan_project(root,out)
    feed=json.loads((out/'scanner-findings.json').read_text())
    assert any(x['status']=='SUPPRESSED' for x in feed['suppressed'])


def test_finding_disappearance_needs_rule_coverage_and_comparable_profile():
    row = {'id': 'one', 'rule_id': 'rule', 'evidence': ['server.ts:1']}
    before = {'findings': [row], 'analysis_profile': {'parser': '1'}}
    after = {'findings': [], 'analysis_profile': {'parser': '1'}, 'file_coverage': {'server.ts': {'status': 'ANALYZED'}}}
    report = diff_findings(before, after)
    assert report['schema'] == 'ases-finding-diff/2.0'
    assert report['summary']['resolved'] == 0 and report['unknown_count'] == 1
    after['finding_coverage'] = {'rule': {'server.ts': {'status': 'ANALYZED'}}}
    assert diff_findings(before, after)['summary']['resolved'] == 1
    after['analysis_profile'] = {'parser': '2'}
    assert diff_findings(before, after)['summary']['resolved'] == 0


def test_finding_evidence_preserves_url_ports():
    before = {'findings': [{'id': 'call', 'evidence': ['http://localhost:8080']}]}
    after = {'findings': [{'id': 'call', 'evidence': ['http://localhost:9090']}]}
    assert diff_findings(before, after)['summary']['changed'] == 1
