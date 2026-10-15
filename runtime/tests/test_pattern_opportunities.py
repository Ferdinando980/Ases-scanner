from pathlib import Path
import json
import jsonschema
from ases.pipeline import scan_project


def _model(tmp_path, name, files):
    root=tmp_path/name
    root.mkdir()
    for filename,code in files.items():
        path=root/filename
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(code,encoding='utf-8')
    return scan_project(root,tmp_path/f'{name}-out')['semantic_model']


def _opportunities(model):
    return model['pattern_opportunities']


def _hints(model):
    return model['pattern_hints']


def test_state_and_strategy_dispatch_use_precision_thresholds(tmp_path):
    model=_model(tmp_path,'dispatch',{
        'StateGame.java':'class Game { void run(State state) { switch (state) { case A: a(); break; case B: b(); break; case C: c(); break; } } }',
        'ModeGame.java':'class ModeGame { void run(Mode mode) { switch (mode) { case A: a(); break; case B: b(); break; case C: c(); break; } } }',
    })
    assert any(x['pattern']=='State' for x in _opportunities(model))
    assert any(x['pattern']=='Strategy' for x in _hints(model))
    assert not any(x['pattern']=='Strategy' for x in _opportunities(model))


def test_factory_requires_creation_policy_and_filters_noise(tmp_path):
    model=_model(tmp_path,'factory',{
        'Selected.java':'class Selected { Object make(Type t) { if (t==A) return new AlphaService(); if (t==B) return new BetaService(); return new GammaService(); } }',
        'Noise.java':'class Noise { void x(){ new IllegalArgumentException(); new RuntimeException(); new UserDTO(); new LoginResponse(); new Date(); } }',
    })
    factories=[x for x in _opportunities(model) if x['pattern']=='Factory']
    assert len(factories)==1
    assert factories[0]['evidence'][0].startswith('Selected.java:')


def test_test_code_never_generates_pattern_opportunities(tmp_path):
    model=_model(tmp_path,'tests',{
        'src/test/java/demo/UtenzaServiceTest.java':'class UtenzaServiceTest { void x(){ if(a) new AlphaService(); else if(b) new BetaService(); else new GammaService(); } }'
    })
    assert not model['pattern_opportunities']
    assert not model['pattern_hints']


def test_behavioral_observer_chain_template_rules(tmp_path):
    model=_model(tmp_path,'behavioral',{
        'Events.java':'class Events { void fire(){ notifyEmail(); notifySms(); notifyAudit(); } }',
        'Router.java':'class Router { Object route(Request r){ if(a(r)) return alphaHandler(r); if(b(r)) return betaHandler(r); if(c(r)) return gammaHandler(r); return null; } }',
        'BaseJob.java':'abstract class BaseJob { void run(){ prepare(); validate(); execute(); cleanup(); } void prepare(){} void validate(){} void execute(){} void cleanup(){} }',
    })
    patterns={x['pattern'] for x in _opportunities(model)}
    assert {'Observer','Chain of Responsibility','Template Method'} <= patterns


def test_adapter_proxy_and_decorator_are_evidence_gated(tmp_path):
    model=_model(tmp_path,'structural',{
        'vendor_integration.ts':'async function map(vendor){ const r=await fetch(url); return { userId: vendor.id, fullName: vendor.name, total: vendor.amount }; }',
        'remote.ts':'async function go(){ await fetch(a); await fetch(b); const token=authToken; retry(); cache(); }',
        'wrap.java':'class X { Object x = new LoggingService(new CachingService(new CoreService())); }',
        'account_mapper.ts':'const mapped={ userId: source.id, fullName: source.name, total: source.amount };',
    })
    opportunities={x['pattern'] for x in _opportunities(model)}
    assert {'Adapter','Proxy','Decorator'} <= opportunities
    assert any(x['pattern']=='Adapter' for x in _hints(model))  # mapping_only lacks external boundary evidence


def test_native_http_client_concerns_are_proxy_hints(tmp_path):
    model=_model(tmp_path,'native-client',{
        'frontend/src/user.service.ts':'''import { HttpClient } from '@angular/common/http';
class UserService {
  private http: HttpClient;
  load() { this.http.get('/user'); this.http.post('/login', {}); retry(); cache(); authToken(); }
}''',
    })
    assert not any(x['pattern']=='Proxy' for x in _opportunities(model))
    assert any(x['pattern']=='Proxy' for x in _hints(model))


def test_facade_opportunity_requires_matching_ordered_workflow(tmp_path):
    model=_model(tmp_path,'facade',{
        'A.java':'''@Service class A {}''',
        'B.java':'''@Service class B {}''',
        'C.java':'''@Service class C {}''',
        'One.java':'''@Service class One {
private A a;
private B b;
private C c;
public void run(){ a.go(); b.go(); c.go(); }
}''',
        'Two.java':'''@Service class Two {
private A a;
private B b;
private C c;
public void run(){ a.go(); b.go(); c.go(); }
}''',
        'dom.js':'''function x(){ document.querySelector('a'); response.json(); classList.add('x'); event.preventDefault(); }''',
    })
    facades=[x for x in _opportunities(model) if x['pattern']=='Facade']
    assert len(facades)==1
    assert facades[0]['scope']=='project'
    assert 'same order' in facades[0]['reason']
    assert any('matching ordered collaborator sequence' in signal for signal in facades[0]['signals']['positive'])
    assert not any('dom.js' in e for x in facades for e in x['evidence'])


def test_facade_shared_collaborators_without_workflow_overlap_are_hints(tmp_path):
    model=_model(tmp_path,'facade-hint',{
        'A.java':'''@Service class A {
private X x;
private Y y;
private Z z;
public void first(){ x.go(); }
public void second(){ y.go(); }
public void third(){ z.go(); }
}''',
        'B.java':'''@Service class B {
private X x;
private Y y;
private Z z;
public void load(){ z.go(); }
public void update(){ x.go(); }
public void remove(){ y.go(); }
}''',
        'X.java':'@Repository class X {}',
        'Y.java':'@Repository class Y {}',
        'Z.java':'@Repository class Z {}',
    })
    facades=[x for x in _opportunities(model) if x['pattern']=='Facade']
    hints=[x for x in _hints(model) if x['pattern']=='Facade']
    assert not facades
    assert len(hints)==1
    assert hints[0]['confidence']=='low'
    assert 'matching ordered call sequence was not established' in hints[0]['reason']


def test_architectural_patterns_are_observed_from_graph(tmp_path):
    model=_model(tmp_path,'architecture',{
        'src/main/java/demo/AppController.java':'''@Controller class AppController {
private AppService appService;
}''',
        'src/main/java/demo/AppService.java':'''@Service class AppService {
private AppRepository appRepository;
}''',
        'src/main/java/demo/AppRepository.java':'@Repository class AppRepository {}',
        'src/main/java/demo/User.java':'@Entity class User {}',
        'src/main/resources/templates/home.html':'<html></html>',
    })
    patterns={x['pattern'] for x in model['architecture_patterns']}
    assert {'Layered Architecture','Repository','MVC'} <= patterns


def test_repository_interfaces_complete_layered_dependencies(tmp_path):
    model=_model(tmp_path,'repository-interfaces',{
        'src/main/java/demo/web/OwnerController.java': '@Controller class OwnerController {\nprivate ClinicService clinicService;\n}',
        'src/main/java/demo/service/ClinicService.java': 'interface ClinicService {}',
        'src/main/java/demo/service/ClinicServiceImpl.java': '@Service class ClinicServiceImpl implements ClinicService {\nprivate OwnerRepository ownerRepository;\n}',
        'src/main/java/demo/repository/OwnerRepository.java': 'interface OwnerRepository {}',
        'src/main/java/demo/repository/jdbc/JdbcOwnerRepository.java': '@Repository class JdbcOwnerRepository implements OwnerRepository {}',
    })
    patterns={x['pattern'] for x in model['architecture_patterns']}
    assert {'Layered Architecture','Repository'} <= patterns


def test_scanner_feed_separates_hints_from_actionable_findings(tmp_path):
    model=_model(tmp_path,'scanner-output',{
        'sample.java':'class Game { void run(Mode mode) { switch (mode) { case A: a(); break; case B: b(); break; case C: c(); break; } } }'
    })
    out=tmp_path/'scanner-output-out'
    consumer=json.loads((out/'consumer-context.json').read_text())
    scanner=json.loads((out/'scanner-findings.json').read_text())
    assert consumer['schema']=='ases-consumer-context/1.5'
    assert scanner['schema']=='ases-scanner-findings/1.3'
    assert not any(x['pattern']=='Strategy' for x in scanner['findings'])
    assert any(x['pattern']=='Strategy' for x in scanner['hints'])
    schema_path=Path(__file__).resolve().parents[2]/'schemas'/'scanner-findings.schema.json'
    jsonschema.validate(scanner,json.loads(schema_path.read_text()))
