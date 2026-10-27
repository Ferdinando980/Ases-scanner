from ases.pipeline import scan_project
from ases.source_roles import classify_source
from ases.recovery.patterns import _dispatch_findings,_observer_findings,_notification_text,_factory_findings
from ases.ui import review_highlights


def test_vendor_staging_is_recognized_without_claiming_all_work_is_vendor():
    assert classify_source('work/vendor-update/three-0.186.1/extracted/three.core.js')['role']=='VENDORED'
    for path in ('src/vendor_update_service.py','work/application/server.py','vendor-update/custom_app.py'):
        assert classify_source(path)['role']=='OWNED_SOURCE'


def test_single_switch_is_a_hint_and_repeated_cases_need_distinct_callables():
    switch='switch(mode){case 1:a();break;case 2:b();break;case 3:c();break;case 4:d();break;}'
    single='function first(mode){'+switch+'}'
    assert all(r['status']=='HINT' for r in _dispatch_findings('app.js',single))
    assert all(r['status']=='HINT' for r in _dispatch_findings('app.js','function first(mode){'+switch+switch+'}'))
    repeated=single+'\nfunction second(mode){'+switch+'}'
    rows=_dispatch_findings('app.js',repeated)
    assert rows and all(r['status']=='OPPORTUNITY' and len(r['evidence'])==2 for r in rows)


def test_switch_count_is_not_taken_from_nearby_cases_or_string_examples():
    code='''const example="switch(mode){case A:case B:case C:case D:}";
// switch(mode){case A:case B:case C:case D:}
function first(mode){switch(mode){case 1:a();break;case 2:b();break;}}
function second(mode){switch(mode){case 3:c();break;case 4:d();break;}}
'''
    assert not _dispatch_findings('app.js',code)
    nested='function run(mode){switch(mode){case 1:switch(other){case 1:a();case 2:b();case 3:c();case 4:d();}break;case 2:b();}}'
    rows=_dispatch_findings('app.js',nested)
    assert len(rows)==1 and all(r['status']=='HINT' for r in rows)


def test_data_updates_do_not_establish_observer_consumers():
    assert not _observer_findings('app.py','def run():\n    first.update(data)\n    second.update(data)\n    third.update(data)\n')
    assert _observer_findings('events.py','def run():\n    mailListener.update()\n    auditListener.update()\n    billingListener.update()\n')
    assert not _observer_findings('app.py',_notification_text('app.py','''# mailListener.update(); auditListener.update(); billingListener.update()
example="mailListener.update();auditListener.update();billingListener.update()"
'''))
    assert not _observer_findings('app.py',_notification_text('app.py','example=f"mailListener.update();auditListener.update();billingListener.update()"'))


def test_factory_does_not_mix_native_arrays_or_unrelated_callables():
    native='function make(kind){if(kind===1)return new Float32Array(2);if(kind===2)return new Uint8Array(2);return new Uint32Array(2);}'
    assert not _factory_findings('arrays.js',native,'arrays')
    unrelated='function a(flag){if(flag)return new AlphaService();} function b(flag){if(flag)return new BetaService();}'
    assert not _factory_findings('app.js',unrelated,'app')
    same_role='function make(kind){if(kind===1)return new AlphaService();if(kind===2)return new BetaService();}'
    assert _factory_findings('app.js',same_role,'app')


def test_auxiliary_opportunities_are_kept_as_hints_and_ids_are_unique(tmp_path):
    root=tmp_path/'app';(root/'benchmarks').mkdir(parents=True)
    switch='switch(mode){case 1:a();break;case 2:b();break;case 3:c();break;case 4:d();break;}'
    code='function first(mode){'+switch+'}\nfunction second(mode){'+switch+'}'
    (root/'app.js').write_text(code)
    (root/'benchmarks/sample.js').write_text(code)
    result=scan_project(root,tmp_path/'scan')
    rows=result['semantic_model']['pattern_findings']
    assert len({r['id'] for r in rows})==len(rows)
    assert any(r['status']=='OPPORTUNITY' and r['evidence'][0].startswith('app.js') for r in rows)
    aux=[r for r in rows if any(e.startswith('benchmarks/') for e in r['evidence'])]
    assert aux and all(r['status']=='HINT' for r in aux)
    assert all(r['counter_evidence'] for r in aux)
    assert result['inventory']['parser_profile']['patterns']=='pattern-opportunities/4'


def test_highlights_group_repeated_families_without_discarding_feed_rows():
    rows=[{'id':str(i),'pattern':'Strategy','status':'OPPORTUNITY','location':{'path':'app'+str(i)+'.js'}} for i in range(20)]
    rows.extend({'id':pattern,'pattern':pattern,'status':'OPPORTUNITY'} for pattern in ('Observer','Adapter'))
    result=review_highlights(rows)
    assert len(result)==3 and {r['pattern'] for r in result}=={'Strategy','Observer','Adapter'}
    assert next(r for r in result if r['pattern']=='Strategy')['group_count']==20
    assert len(rows)==22
