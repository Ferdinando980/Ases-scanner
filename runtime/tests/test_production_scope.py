"""Test fixtures remain evidence about tests, never the application's production surface."""
from ases.pipeline import scan_project
from ases.source_roles import classify_source
import pytest


def test_python_and_java_fixtures_do_not_create_production_behaviors(tmp_path):
    (tmp_path / 'app.py').write_text('def read(): return 1')
    (tmp_path / 'test_web.py').write_text("""import openai
class Example(Base): pass
@app.get('/fixture-python')
def test_route():
    validateUser()
    return 1
""")
    java = tmp_path / 'tests/fixtures/Demo.java'
    java.parent.mkdir(parents=True)
    java.write_text('''@RestController class Demo {
 @GetMapping("/fixture-java") public String route(){return "fixture";}
}
@Entity class FixtureEntity {}''')
    result = scan_project(tmp_path, tmp_path.parent / (tmp_path.name + '.ases'))
    model = result['semantic_model']
    assert classify_source('test_web.py', tmp_path)['role'] == 'TEST'
    assert not model['behaviors'] and not model['sensitive_paths']
    assert not model['external_systems'] and not model['trust_boundaries']
    assert not model['assets'] and not model['controls']
    assert all(row['name'] not in {'Demo', 'FixtureEntity', 'Example', 'test_web'} for row in model['components'])
    fixture_nodes = [n for n in result['graph']['nodes'] if n['path'] in {'test_web.py', 'tests/fixtures/Demo.java'}]
    assert fixture_nodes and all(n['metadata']['is_test_code'] for n in fixture_nodes)
    assert model['tests']  # Test evidence is still retained.


@pytest.mark.parametrize('suffix', ['jsp', 'hbs', 'ejs', 'pug', 'twig'])
def test_template_suffixes_enter_frontend_inventory_without_a_client_directory(tmp_path, suffix):
    page = tmp_path / ('src/main/webapp/page.' + suffix)
    page.parent.mkdir(parents=True)
    page.write_text("<form action='/users' method='post'></form>")
    result = scan_project(tmp_path, tmp_path.parent / (tmp_path.name + '.ases'))
    assert classify_source(page.relative_to(tmp_path).as_posix(), tmp_path)['scope'] == 'frontend'
    assert len(result['semantic_model']['frontend']['templates']) == 1
    assert result['semantic_model']['frontend']['api_calls'][0]['path'] == '/users'
    assert result['inventory']['source_manifest'][0]['path'] == page.relative_to(tmp_path).as_posix()
