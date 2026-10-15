from pathlib import Path
import pytest
from ases.scanners.javascript import scan_javascript
from ases.pipeline import scan_project
from ases.semantic_diff import load_context, semantic_diff


def write(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def calls(graph):
    nodes = {n.id: n for n in graph.nodes}
    return {(nodes[e.source].name, nodes[e.target].name, nodes[e.target].path)
            for e in graph.edges if e.relation == "calls"}


@pytest.mark.parametrize("project_name", ["project", "project.js"])
@pytest.mark.parametrize("binding", ["import {read} from '../..';", "const {read} = require('../..');"])
def test_root_directory_import_resolves_index_without_sibling_candidates(tmp_path, project_name, binding):
    root = tmp_path / project_name
    write(root, "index.js", "export function read() { return 1; }")
    write(root, "examples/client/main.js", binding + " function run() { return read(); }")
    write(tmp_path, project_name + ".ts", "export function read() { return 2; }")
    graph = scan_javascript(root)
    assert ("run", "read", "index.js") in calls(graph)
    assert all(node.path != "../" + project_name + ".ts" for node in graph.nodes)


def test_root_directory_import_without_entry_stays_unresolved(tmp_path):
    root = tmp_path / "project"
    write(root, "client/main.js", "import {read} from '..'; function run() { return read(); }")
    write(tmp_path, "project.js", "export function read() { return 1; }")
    graph = scan_javascript(root)
    assert not any(source == "run" for source, _, _ in calls(graph))
    assert graph.unknowns


def test_module_alias_reexport_shadowing_and_type_only_are_conservative(tmp_path):
    write(tmp_path, "repo.ts", "export function read() { return 1; }")
    write(tmp_path, "other.ts", "export function read() { return 2; }")
    write(tmp_path, "bridge.ts", "export { read as load } from './repo.js';")
    write(tmp_path, "server.ts", '''import {load as get} from './bridge';
import type {read as typed} from './other';
export function handler() { return get(); }
export function shadow(get) { return get(); }
export function destructured({get}) { return get(); }
export const arrow = get => get();
function misuse() { return typed(); }
const text = "get()"; // get(); app.get('/fake', handler);
app.get('/real', handler);''')
    graph = scan_javascript(tmp_path)
    assert ("handler", "read", "repo.ts") in calls(graph)
    assert not any(src in {"shadow", "destructured", "arrow", "misuse"} for src, _, _ in calls(graph))
    assert {n.metadata["path"] for n in graph.nodes if n.kind == "route"} == {"/real"}
    assert any(u["reason"] == "type_only_import_called" for u in graph.unknowns)


def test_commonjs_destructuring_and_lexical_reassignment(tmp_path):
    write(tmp_path, "repo.cjs", "exports.read = function read() { return 1; };")
    write(tmp_path, "server.cjs", '''const {read: load} = require('./repo.cjs');
function handler() { return load(); }
let alias = load; alias = opaque;
function uncertain() { return alias(); }''')
    graph = scan_javascript(tmp_path)
    assert ("handler", "read", "repo.cjs") in calls(graph)
    assert not any(src == "uncertain" for src, _, _ in calls(graph))


def test_type_reexport_and_reassigned_export_do_not_become_calls(tmp_path):
    write(tmp_path, "zrepo.ts", "export function read() {} export let mutable = () => 1; mutable = opaque;")
    write(tmp_path, "bridge.ts", "export type {read} from './zrepo';")
    write(tmp_path, "aserver.ts", "import {read} from './bridge'; import {mutable} from './zrepo'; function handler() { read(); mutable(); }")
    assert not any(src == "handler" for src, _, _ in calls(scan_javascript(tmp_path)))


def test_type_heritage_and_duplicate_declarations_keep_their_authority(tmp_path):
    write(tmp_path, "types.ts", "export interface Reader { read(): number; } export class Base {}")
    write(tmp_path, "server.ts", """import type {Reader} from './types'; import {Base} from './types';
class Service extends Base implements Reader { read() { return 1; } }
function duplicate() { return 1; } function duplicate() { return 2; }
function handler() { return duplicate(); } app.get('/duplicate', duplicate);""")
    graph = scan_javascript(tmp_path)
    nodes = {node.id: node for node in graph.nodes}
    inherited = {(nodes[edge.source].name, edge.relation, nodes[edge.target].name) for edge in graph.edges if edge.relation in {'extends', 'implements'}}
    assert inherited == {('Service', 'extends', 'Base'), ('Service', 'implements', 'Reader')}
    assert not any(src == 'handler' for src, _, _ in calls(graph))
    assert next(node for node in graph.nodes if node.kind == 'route').metadata['handler'] is None


@pytest.mark.parametrize('extension', ['.jsx', '.tsx', '.mjs', '.cjs', '.mts', '.cts'])
def test_root_test_files_in_module_extensions_are_not_production(tmp_path, extension):
    from ases.source_roles import classify_source
    name = 'server.spec' + extension
    write(tmp_path, name, "function handler() {} app.get('/not-production', handler); test('case', () => handler());")
    assert classify_source(name, tmp_path)['role'] == 'TEST'
    graph = scan_javascript(tmp_path)
    assert not any(node.kind == 'route' for node in graph.nodes)
    assert any(node.kind == 'test' for node in graph.nodes)
    assert all(node.metadata['is_test_code'] for node in graph.nodes if node.kind == 'function')


def test_client_call_paths_and_static_test_links(tmp_path):
    write(tmp_path, "server.ts", '''import OpenAI from 'openai';
const client = new OpenAI();
export async function ask() { return client.chat.completions.create({messages: []}); }
app.post('/ask', ask);''')
    write(tmp_path, "tests/server.test.ts", "import {ask} from '../server'; test('AI request', async () => ask());")
    output = tmp_path.parent / (tmp_path.name + ".ases")
    model = scan_project(tmp_path, output)["semantic_model"]
    assert model["external_systems"][0]["usage_basis"] == "static-client-call"
    assert model["sensitive_paths"][0]["destination"]["kind"] == "external_api_call"
    assert any(link["relation"] == "verifies" and link["basis"] == "static-call" and link["test_executed"] is False
               for link in model["trace_links"])


def test_frontend_api_syntax_ignores_comments_strings_and_shadowed_fetch(tmp_path):
    write(tmp_path, "client/api.ts", '''// fetch('/fake');
const text = "fetch('/also-fake')";
export function load() { return fetch('/users'); }
export function local(fetch) { return fetch('/shadowed'); }''')
    model = scan_project(tmp_path, tmp_path.parent / (tmp_path.name + ".ases"))["semantic_model"]
    assert {x["path"] for x in model["frontend"]["api_calls"]} == {"/users"}


def test_malformed_source_and_ambiguous_module_are_explicit(tmp_path):
    write(tmp_path, "repo.ts", "export function read() {}")
    write(tmp_path, "repo.js", "export function read() {}")
    write(tmp_path, "server.mts", "import {read} from './repo'; function f() { return read(); }")
    write(tmp_path, "broken.cts", "function bad( { return")
    graph = scan_javascript(tmp_path)
    assert not any(src == "f" for src, _, _ in calls(graph))
    assert graph.coverage["broken.cts"]["status"] == "PARTIAL"
    assert any(x["reason"] == "parser_recovery" for x in graph.unknowns)


def test_ast_identity_and_diff_ignore_formatting(tmp_path):
    write(tmp_path, "server.mjs", "export function f(x) { return x; } app.get('/x', f);")
    before = tmp_path.parent / (tmp_path.name + "-before.ases")
    after = tmp_path.parent / (tmp_path.name + "-after.ases")
    scan_project(tmp_path, before)
    write(tmp_path, "server.mjs", "\n// moved\nexport function f ( x ) {\n return x;\n}\napp.get('/x', f);")
    scan_project(tmp_path, after)
    report = semantic_diff(load_context(before), load_context(after))
    assert report["summary"] == {"added": 0, "removed": 0, "changed": 0}


def test_destructured_and_arrow_fetch_bindings_do_not_invent_network_calls(tmp_path):
    write(tmp_path, "client/api.ts", """const {fetch} = local;
export function load() { return fetch('/local'); }
export const arrow = fetch => fetch('/arrow');
export function destructured({fetch}) { return fetch('/parameter'); }""")
    model = scan_project(tmp_path, tmp_path.parent / (tmp_path.name + ".ases"))["semantic_model"]
    assert model["frontend"]["api_calls"] == []


def test_nest_di_without_call_and_controls_outside_handler_stay_separate(tmp_path):
    write(tmp_path, "users.service.ts", "export class Users { read() { return fetch('https://example.test/users'); } }")
    write(tmp_path, "users.controller.ts", """import {Users} from './users.service';
@Controller('users')
class Controller {
  constructor(private users: Users) {}
  @Get('read') @UseGuards(AuthGuard)
  read() { validateUser(); return this.users.read(); }
  @Get('unused')
  unused() { return 1; }
}
validateOutside();""")
    out = tmp_path.parent / (tmp_path.name + ".ases")
    scan_project(tmp_path, out)
    context = load_context(out)
    entities = {row["id"]: row for row in context["entities"]}
    paths = context["sensitive_paths"]
    assert paths and all(entities[path["entry_point"]]["name"] == "GET /users/read" for path in paths)
    assert all(path["status"] == "INFERRED" and path["coverage"]["status"] == "PARTIAL" and path["observation_refs"] for path in paths)
    scoped = [(entities[row["from"]], entities[row["to"]]) for row in context["structural_relations"] if row["relation"] in {"protects", "protects_or_validates"}]
    assert any(control["name"] == "UseGuards" and target["name"] == "read" for control, target in scoped)
    assert not any(control["name"] == "validateOutside(" for control, _ in scoped)
