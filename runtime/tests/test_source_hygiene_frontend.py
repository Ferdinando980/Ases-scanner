import json
from ases.pipeline import scan_project


def _write(root, rel, text):
    p=root/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding='utf-8'); return p


def test_generated_vendored_and_tooling_never_drive_analysis(tmp_path):
    root=tmp_path/'repo'; root.mkdir()
    _write(root,'src/main/java/demo/AppController.java','@Controller class AppController {}')
    _write(root,'src/test/java/demo/AppTest.java','class AppTest { @Test public void ok(){} }')
    _write(root,'docs/jacoco/demo/FakeController.java.html','<html>class FakeController</html>')
    _write(root,'docs/jacoco/prettify.js','switch(mode){case 1:break;case 2:break;case 3:break;case 4:break;}')
    _write(root,'src/main/resources/static/js/lib/typeahead.bundle.min.js','switch(x){case 1:break;case 2:break;case 3:break;case 4:break;}')
    _write(root,'.mvn/wrapper/MavenWrapperDownloader.java','class MavenWrapperDownloader {}')
    result=scan_project(root,tmp_path/'out')
    inv=result['inventory']; model=result['semantic_model']
    assert inv['source_roles']['GENERATED'] >= 2
    assert inv['source_roles']['VENDORED'] == 1
    assert inv['source_roles']['TOOLING'] == 1
    assert len(model['tests']) == 1
    assert not any('prettify.js' in e or 'typeahead.bundle.min.js' in e for f in model['pattern_findings'] for e in f.get('evidence',[]))


def test_dao_serviceimpl_layering_and_named_external_adapter(tmp_path):
    root=tmp_path/'repo'; root.mkdir()
    _write(root,'src/main/java/demo/AppController.java','@Controller class AppController {\nprivate UserService service;\npublic void x(){ service.go(); }\n}')
    _write(root,'src/main/java/demo/UserService.java','interface UserService {}')
    _write(root,'src/main/java/demo/UserServiceImpl.java','@Service class UserServiceImpl implements UserService {\nprivate UserDAO userDAO;\npublic void go(){ userDAO.findAll(); }\n}')
    _write(root,'src/main/java/demo/UserDAO.java','interface UserDAO {}')
    _write(root,'src/main/java/demo/BookApiAdapter.java','interface BookApiAdapter { Object get(String id); }')
    _write(root,'src/main/java/demo/GoogleBookApiAdapterImpl.java','class GoogleBookApiAdapterImpl implements BookApiAdapter { public Object get(String id){ try { return new java.net.URL("https://example.com"); } catch(Exception e){ return null; } } }')
    model=scan_project(root,tmp_path/'out')['semantic_model']
    patterns={f['pattern'] for f in model['pattern_findings'] if f['status']=='OBSERVED'}
    assert {'Layered Architecture','Repository','Service Layer','Adapter'} <= patterns


def test_frontend_service_conformance_and_cross_boundary_contract(tmp_path):
    root=tmp_path/'repo'; root.mkdir()
    _write(root,'src/main/java/demo/UserController.java','@Controller class UserController { @GetMapping("/api/users") public String users(){ return "ok"; } @PostMapping("/api/login") public String login(){ return "ok"; } }')
    _write(root,'frontend/src/api/userApi.ts','export async function users(){ return fetch("/api/users"); }')
    _write(root,'frontend/src/components/UserPage.tsx','import { users } from "../api/userApi"; export function UserPage(){ return (<div/>); }')
    _write(root,'frontend/src/components/LoginPage.tsx','export function LoginPage(){ fetch("/api/login", {method:"POST"}); return (<div/>); }')
    _write(root,'frontend/src/components/HomePage.tsx','export function HomePage(){ return (<div/>); }')
    out=tmp_path/'out'; model=scan_project(root,out)['semantic_model']
    front=model['frontend_findings']; cross=model['cross_boundary_findings']
    assert any(f['pattern']=='Component-based UI' and f['status']=='OBSERVED' for f in front)
    assert any(f['pattern']=='Frontend API Service Layer' and f['status']=='OBSERVED' for f in front)
    assert any(f['status']=='CONTRADICTED' and f['rule_id']=='frontend.conformance.api_service_bypass' for f in front)
    assert any(f['rule_id']=='cross_boundary.route_contract' and f['status']=='OBSERVED' for f in cross)
    scanner=json.loads((out/'scanner-findings.json').read_text())
    assert scanner['schema']=='ases-scanner-findings/1.3'
    assert all('actionability' in f and 'entity' in f and 'surface' in f for f in scanner['findings'])
