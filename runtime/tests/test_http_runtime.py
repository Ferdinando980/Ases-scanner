from http.server import ThreadingHTTPServer
import threading
from urllib.request import urlopen
import pytest
from ases.pipeline import scan_project
from ases.engineering.runtime_evidence import template,correlate


def test_controlled_dynamic_http_execution_is_imported_without_promoting_static_routes(tmp_path):
    # The only executed source is this test-authored fixture, never user project code.
    source='''from http.server import BaseHTTPRequestHandler
routes={path:200 for path in ['/dynamic']}
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(routes.get(self.path,404))
        self.end_headers()
    def log_message(self,*args):pass
'''
    root=tmp_path/'fixture';root.mkdir();(root/'server.py').write_text(source)
    result=scan_project(root,tmp_path/'snapshot')
    assert not result['engineering_model']['recovered_requirements'] or not any(r['name']=='GET /dynamic' for r in result['engineering_model']['recovered_requirements'])
    namespace={};exec(compile(source,'controlled-fixture.py','exec'),namespace)
    server=ThreadingHTTPServer(('127.0.0.1',0),namespace['Handler'])
    thread=threading.Thread(target=server.serve_forever);thread.start()
    try:
        with urlopen(f'http://127.0.0.1:{server.server_port}/dynamic',timeout=3) as response:status=response.status
    finally:server.shutdown();thread.join();server.server_close()
    supplied=template(tmp_path/'snapshot');supplied['collector']={'name':'controlled-fixture-test','independent':False}
    supplied['environment']={'fixture':'test-authored-http-server'}
    supplied['observations']=[{'method':'GET','path':'/dynamic','status':status}]
    report=correlate(tmp_path/'snapshot',supplied)
    assert report['counts']['dynamic-or-unreconstructed']==1
    assert report['matches'][0]['status']==200 and not report['matches'][0]['execution_verified_by_ases']
    supplied['source_digest']='wrong'
    with pytest.raises(ValueError,match='different snapshot'):correlate(tmp_path/'snapshot',supplied)


def test_overlapping_prefixes_and_exact_candidates_remain_ambiguous(monkeypatch):
    from ases.engineering import runtime_evidence as runtime
    context={'snapshot_id':'snapshot:test','source_manifest':[], 'entities':[
        {'id':'exact','kind':'route','properties':{'http_method':'GET','path':'/items/one'}},
        {'id':'prefix','kind':'route','properties':{'http_method':'GET','match_kind':'prefix','path_prefix':'/items/'}}]}
    monkeypatch.setattr(runtime,'load_context',lambda _,**kw:context)
    supplied=runtime.template('unused');supplied['observations']=[{'method':'GET','path':'/items/one','status':200}]
    report=runtime.correlate('unused',supplied)
    assert report['counts']['ambiguous']==1
    supplied['observations'][0]['path']='/items/one?token=private'
    with pytest.raises(ValueError,match='query'):runtime.correlate('unused',supplied)
