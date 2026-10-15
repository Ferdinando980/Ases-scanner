"""Small independent oracles for defects observed in public upstream repositories."""
import pytest

from ases.pipeline import scan_project
from ases.scanners.java import scan_java
from ases.scanners.javascript import scan_javascript
from ases.scanners.python import scan_python
from ases.semantic_diff import load_context, semantic_diff


def write(root, name, source):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


@pytest.mark.parametrize("methods,expected", [
    ("", {"GET /auth/login"}),
    (", methods=('GET', 'POST')", {"GET /auth/login", "POST /auth/login"}),
    (", methods=['get', 'POST', 'GET']", {"GET /auth/login", "POST /auth/login"}),
])
def test_flask_blueprint_literal_prefix_and_methods(tmp_path, methods, expected):
    write(tmp_path, "auth.py", f'''from flask import Blueprint as BP
bp = BP('auth', __name__, url_prefix='/auth')
@bp.route('/login'{methods})
def login(): return 'ok'
''')
    graph = scan_python(tmp_path)
    routes = [n for n in graph.nodes if n.kind == "route"]
    assert {n.name for n in routes} == expected
    assert all(n.metadata["route_scope"] == "declared-static" for n in routes)
    assert len([e for e in graph.edges if e.relation == "handled_by"]) == len(expected)


def test_flask_app_keyword_rule_and_blueprint_method_shortcuts(tmp_path):
    write(tmp_path, "app.py", '''import flask as f
app = f.Flask(__name__)
bp = f.Blueprint('api', __name__, url_prefix='/v1')
@app.route(rule='/health')
def health(): return 'ok'
@bp.post('/items')
def create(): return 'ok'
''')
    assert {n.name for n in scan_python(tmp_path).nodes if n.kind == "route"} == {"GET /health", "POST /v1/items"}


def test_flask_local_registration_prefix_override_and_multiple_mounts(tmp_path):
    write(tmp_path, "app.py", '''from flask import Flask, Blueprint
app = Flask(__name__)
bp = Blueprint('api', __name__, url_prefix='/default')
@bp.route('/items', methods=('GET',))
def items(): return []
app.register_blueprint(bp, url_prefix='/v1')
app.register_blueprint(bp, url_prefix='/v2', name='second')
''')
    assert {n.name for n in scan_python(tmp_path).nodes if n.kind == "route"} == {"GET /v1/items", "GET /v2/items"}


@pytest.mark.parametrize("prefix,methods,registration", [
    ("prefix_from_config", "('GET',)", ""),
    ("'/auth'", "methods_from_config", ""),
    ("'/auth'", "('GET',)", "app.register_blueprint(bp, url_prefix=from_config)"),
    ("'/auth'", "('GET',)", "app.register_blueprint(bp, **options)"),
])
def test_flask_dynamic_route_inputs_remain_unknown(tmp_path, prefix, methods, registration):
    write(tmp_path, "app.py", f'''from flask import Blueprint
bp = Blueprint('auth', __name__, url_prefix={prefix})
@bp.route('/login', methods={methods})
def login(): return 'ok'
{registration}
''')
    graph = scan_python(tmp_path)
    assert not any(n.kind == "route" for n in graph.nodes)
    assert any(u["reason"].startswith("python_flask_") for u in graph.unknowns)
    assert any(n.name == "login" and n.kind == "function" for n in graph.nodes)


def test_flask_unrelated_or_rebound_constructor_does_not_authorize_routes(tmp_path):
    write(tmp_path, "app.py", '''from flask import Blueprint
Blueprint = custom_factory
bp = Blueprint('auth', __name__, url_prefix='/auth')
@bp.route('/not-proven')
def not_proven(): pass
other = custom_router()
@other.route('/also-not-proven')
def unrelated(): pass
''')
    assert not any(n.kind == "route" for n in scan_python(tmp_path).nodes)


def test_flask_blueprint_test_routes_are_not_production_behaviors(tmp_path):
    write(tmp_path, "tests/test_app.py", '''from flask import Blueprint
bp = Blueprint('fixture', __name__, url_prefix='/fixture')
@bp.route('/login', methods=('GET', 'POST'))
def login(): pass
''')
    model = scan_project(tmp_path, tmp_path / "output.ases")["semantic_model"]
    assert not model["behaviors"]


@pytest.mark.parametrize("asynchronous", ["", "async "])
def test_python_factory_routes_keep_handler_and_lexical_helper(tmp_path, asynchronous):
    write(tmp_path, "app.py", f'''def other_factory():
    def helper(): return 2
    return helper
def create_app():
    app = make_app()
    def helper(): return 1
    @app.get('/login')
    {asynchronous}def login(): return helper()
    return app
''')
    graph = scan_python(tmp_path)
    nodes = {n.id: n for n in graph.nodes}
    route = next(n for n in graph.nodes if n.kind == "route" and n.name == "GET /login")
    handler = nodes[route.metadata["handler"]]
    assert handler.name == "login" and nodes[handler.metadata["owner"]].name == "create_app"
    called = [nodes[e.target] for e in graph.edges if e.source == handler.id and e.relation == "calls"]
    assert len(called) == 1 and called[0].name == "helper"
    assert nodes[called[0].metadata["owner"]].name == "create_app"


def test_factory_flask_bindings_and_parameter_shadowing(tmp_path):
    write(tmp_path, "app.py", '''from flask import Flask, Blueprint
def create_app():
    app = Flask(__name__)
    bp = Blueprint('api', __name__, url_prefix='/api')
    def helper(): return 1
    @bp.route('/login', methods=['GET', 'POST'])
    def login(helper): return helper()
    app.register_blueprint(bp, url_prefix='/v1')
    return app
''')
    graph = scan_python(tmp_path)
    assert {n.name for n in graph.nodes if n.kind == "route"} == {"GET /v1/login", "POST /v1/login"}
    login = next(n for n in graph.nodes if n.kind == "function" and n.name == "login")
    assert not any(e.source == login.id and e.relation == "calls" for e in graph.edges)
    assert any(u["reason"] == "python_shadowed_call" for u in graph.unknowns)


def test_factory_same_named_handlers_have_distinct_stable_identity(tmp_path):
    source = '''def first():
    app = make_app()
    @app.get('/same')
    def login(): return 1
    return app
def second():
    app = make_app()
    @app.get('/same')
    def login(): return 2
    return app
'''
    write(tmp_path, "app.py", source)
    scan_project(tmp_path, tmp_path / "before.ases")
    before = load_context(tmp_path / "before.ases")
    handlers = [e for e in before["entities"] if e["name"] == "login"]
    routes = [e for e in before["entities"] if e["kind"] == "route"]
    assert len(handlers) == len({e["id"] for e in handlers}) == 2
    assert len(routes) == len({e["id"] for e in routes}) == 2
    assert all(e["identity"]["state"] == "unique" for e in handlers + routes)
    write(tmp_path, "app.py", "\n\n# moved\n" + source.replace("    @", "\n    @"))
    scan_project(tmp_path, tmp_path / "after.ases")
    after = load_context(tmp_path / "after.ases")
    delta = semantic_diff(before, after)
    assert {e["id"] for e in before["entities"]} == {e["id"] for e in after["entities"]}
    assert delta["summary"] == {"added": 0, "removed": 0, "changed": 0}
    assert not delta["uncertain"]


def test_express_getters_are_not_routes_but_handlers_and_unknowns_are_preserved(tmp_path):
    write(tmp_path, "server.js", '''function handler(req, res) { return res.send('ok'); }
app.get('etag fn'); app.get('json escape'); app.get('/setting');
app.get('/real', handler); app.post('/post', handler);
router.get('/unknown', externalHandler);
''')
    graph = scan_javascript(tmp_path)
    routes = [n for n in graph.nodes if n.kind == "route"]
    assert {n.name for n in routes} == {"GET /real", "POST /post", "GET /unknown"}
    assert next(n for n in routes if n.name == "GET /real").metadata["handler"]
    assert next(n for n in routes if n.name == "GET /unknown").metadata["handler"] is None
    assert any(u["reason"] == "route_handler_or_middleware_unresolved" for u in graph.unknowns)


@pytest.mark.parametrize("annotation", ["Test", "ParameterizedTest", "RepeatedTest(2)", "org.junit.jupiter.api.Test"])
def test_junit_package_private_methods_and_existing_public_tests(tmp_path, annotation):
    write(tmp_path, "src/test/java/demo/ExampleTest.java", f'''package demo;
class ExampleTest {{
    @{annotation}
    void packageTest() throws Exception {{ helper(); }}
    @Test public void publicTest() {{ helper(); }}
    void helper() {{}}
}}
''')
    graph = scan_java(tmp_path)
    assert {n.name for n in graph.nodes if n.kind == "test"} == {"packageTest", "publicTest"}
    method = next(n for n in graph.nodes if n.kind == "method" and n.name == "packageTest")
    assert method.metadata["visibility"] == "package-private"
    assert method.metadata["is_test_code"] is True


def test_junit_annotations_in_comments_strings_and_helpers_are_not_tests(tmp_path):
    write(tmp_path, "src/test/java/demo/ExampleTest.java", '''package demo;
class ExampleTest {
    // @Test void fakeLine() {}
    /* @Test void fakeBlock() {} */
    String text = "@Test void fakeString() {}";
    @BeforeEach void helper() {}
    @Test
    @DisplayName("a real test")
    void realTest() {}
}
''')
    assert {n.name for n in scan_java(tmp_path).nodes if n.kind == "test"} == {"realTest"}
