"""Acceptance oracles from the roadmap audit; expected facts are hand labelled."""
from copy import deepcopy
from hashlib import sha256
import pytest

from ases.evidence import location, seal_context, validate_context
from ases.pipeline import scan_project
from ases.scanners.javascript import api_calls, scan_javascript
from ases.semantic_diff import load_context, semantic_diff


def write(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8")
    return target


def snapshot(root, label):
    out = root.parent / (root.name + label + ".ases")
    scan_project(root, out)
    return load_context(out)


@pytest.mark.parametrize("path", ["server.mjs", "client/api.ts"])
def test_repeated_request_sites_keep_callers_and_survive_formatting(tmp_path, path):
    source = "function a(){fetch('/x');return fetch('/x');} function b(){return fetch('/x');} app.get('/a', a); app.get('/b', b);"
    write(tmp_path, path, source)
    before = snapshot(tmp_path, "before")
    write(tmp_path, path, "// harmless\n" + source.replace("}", "}\n").replace(";", ";\n"))
    after = snapshot(tmp_path, "after")
    for context in (before, after):
        requests = [e for e in context["entities"] if e["kind"] in {"external_api_call", "frontend_api_call"}]
        assert len(requests) == 3
        owners = {e["id"]: e["name"] for e in context["entities"]}
        assert sorted(owners[e["properties"]["owner"]] for e in requests) == ["a", "a", "b"]
        assert all(e["identity"]["state"] == "unique" for e in requests)
    assert {e["id"] for e in before["entities"]} == {e["id"] for e in after["entities"]}
    assert {p["id"] for p in before["sensitive_paths"]} == {p["id"] for p in after["sensitive_paths"]}
    assert semantic_diff(before, after)["summary"] == {"added": 0, "removed": 0, "changed": 0}


@pytest.mark.parametrize("source", [
    "const axios = {get(x){return x;}}; function handler(){return axios.get('/local');}",
    "import axios from 'axios'; function handler(axios){return axios.get('/local');}",
    "import axios from 'axios'; function handler({axios}){return axios.get('/local');}",
    "import axios from 'axios'; axios = local; axios.get('/local');",
    "import axios from 'axios'; axios.get = local; axios.get('/local');",
    "import type axios from 'axios'; axios.get('/local');",
    "const http = {get(x){return x;}}; http.get('/local');",
    "const $ = {ajax(x){return x;}}; $.ajax({url:'/local'});",
    "function f(fetch) { fetch('/local'); }",
    "const {fetch} = local; fetch('/local');",
    "class X { http = local; load(){this.http.get('/local');} }",
    "try { opaque(); } catch(fetch) { fetch('/local'); }",
    "function f(){ if (maybe) { var fetch = local; } fetch('/local'); }",
    "function f(){ fetch = local; } fetch('/local');",
    "axios.get('/local'); http.get('/local'); $.ajax({url:'/local'});",
    "function require(name){return local;} const axios = require('axios'); axios.get('/local');",
    "import {HttpClient} from '@angular/common/http'; class X { constructor(private http: HttpClient){} load(){function nested(){this.http.get('/local');}} }",
])
def test_local_or_mutated_request_receivers_are_not_network(tmp_path, source):
    assert list(api_calls(source, ".ts")) == []
    write(tmp_path, 'client/api.ts', source)
    assert not any(n.kind in {'external_api_call', 'frontend_api_call'} for n in scan_javascript(tmp_path).nodes)


def test_supported_request_clients_use_import_and_declared_type_authority(tmp_path):
    source = """import transport from 'axios'; import jq from 'jquery';
import {HttpClient as Client} from '@angular/common/http';
transport.get('/axios'); jq.ajax({url:'/jquery', method:'POST'});
const commonjs = require('axios'); commonjs.get('/commonjs');
class Api { constructor(private wire: Client) {} load(){return this.wire.get('/angular');} }
fetch('/ambient');"""
    assert {(method, target) for _, method, target in api_calls(source, '.ts')} == {
        ('GET', '/axios'), ('POST', '/jquery'), ('GET', '/angular'), ('GET', '/ambient'), ('GET', '/commonjs')}
    write(tmp_path, 'client/api.ts', source)
    context = snapshot(tmp_path, 'clients')
    assert len([e for e in context['entities'] if e['kind'] == 'frontend_api_call']) == 5
    assert not any(e['kind'] == 'external_api_call' for e in context['entities'])


def test_named_function_expression_does_not_shadow_ambient_fetch_outside_it():
    source = "const obj = {fetch(){}}; const local = function fetch(){return fetch('/local');}; fetch('/ambient');"
    assert [(method, target) for _, method, target in api_calls(source, '.js')] == [('GET', '/ambient')]


def test_request_shadowing_in_a_block_and_lexical_this_in_arrow():
    source = """import axios from 'axios'; import {HttpClient} from '@angular/common/http';
{ const axios = local; axios.get('/local'); } axios.get('/real');
class X { constructor(private wire: HttpClient) {} load(){ return () => this.wire.get('/arrow'); } }"""
    assert {(method, target) for _, method, target in api_calls(source, '.ts')} == {('GET', '/real'), ('GET', '/arrow')}


def call_pairs(graph):
    nodes = {n.id: n for n in graph.nodes}
    return {(nodes[e.source].name, nodes[e.target].name, nodes[e.target].path)
            for e in graph.edges if e.relation == 'calls'}


def test_export_star_chains_explicit_precedence_and_cycle_exit(tmp_path):
    write(tmp_path, 'repo.mjs', 'export function read(){} export default function hidden(){}')
    write(tmp_path, 'other.mjs', 'export function read(){}')
    write(tmp_path, 'one.mjs', "export * from './two.mjs'; export * from './repo.mjs';")
    write(tmp_path, 'two.mjs', "export * from './one.mjs';")
    write(tmp_path, 'explicit.mjs', "export * from './other.mjs'; export {read} from './repo.mjs';")
    write(tmp_path, 'server.mjs', """import {read} from './two.mjs'; import {read as preferred} from './explicit.mjs';
function chain(){read();} function explicit(){preferred();}""")
    assert {('chain', 'read', 'repo.mjs'), ('explicit', 'read', 'repo.mjs')} <= call_pairs(scan_javascript(tmp_path))


def test_export_star_ambiguity_default_type_only_and_empty_cycles_stay_unknown(tmp_path):
    write(tmp_path, 'repo.ts', 'export function read(){} export default function hidden(){}')
    write(tmp_path, 'other.ts', 'export function read(){}')
    write(tmp_path, 'ambiguous.ts', "export * from './repo'; export * from './other';")
    write(tmp_path, 'typed.ts', "export type * from './repo';")
    write(tmp_path, 'cycle1.ts', "export * from './cycle2';")
    write(tmp_path, 'cycle2.ts', "export * from './cycle1';")
    write(tmp_path, 'server.ts', """import {read} from './ambiguous'; import hidden from './ambiguous';
import {read as typed} from './typed'; import {missing} from './cycle1';
function uncertain(){read();hidden();typed();missing();}""")
    graph = scan_javascript(tmp_path)
    assert not any(src == 'uncertain' for src, _, _ in call_pairs(graph))
    assert any(u['reason'] == 'call_target_unresolved' for u in graph.unknowns)


def test_export_resolution_limit_preserves_unknown_instead_of_guessing(tmp_path, monkeypatch):
    from ases.scanners import javascript
    monkeypatch.setattr(javascript, 'MAX_BINDING_DEPTH', 2)
    write(tmp_path, 'repo.mjs', 'export function read(){}')
    write(tmp_path, 'one.mjs', "export * from './repo.mjs';")
    write(tmp_path, 'two.mjs', "export * from './one.mjs';")
    write(tmp_path, 'server.mjs', "import {read} from './two.mjs'; function handler(){read();}")
    graph = scan_javascript(tmp_path)
    assert not any(src == 'handler' for src, _, _ in call_pairs(graph))
    assert any(row['reason'] == 'export_resolution_limit' for row in graph.unknowns)


@pytest.mark.parametrize('statement, expected', [
    ("import type {Reader} from './repo';", {'imports_type'}),
    ("import {type Reader} from './repo';", {'imports_type'}),
    ("export type {Reader} from './repo';", {'imports_type'}),
    ("import Client, {type Reader} from './repo';", {'imports', 'imports_type'}),
])
def test_module_relations_preserve_type_only_authority(tmp_path, statement, expected):
    write(tmp_path, 'repo.ts', 'export interface Reader {} export default class Client {}')
    write(tmp_path, 'server.ts', statement)
    graph = scan_javascript(tmp_path)
    assert {e.relation for e in graph.edges if e.source == 'module:javascript:server.ts' and e.target == 'module:javascript:repo.ts'} == expected


def test_artifact_requests_obey_the_same_receiver_boundary(tmp_path):
    from ases.artifacts import inspect_artifact
    write(tmp_path, 'app.js', "const axios={get(x){return x;}}; axios.get('/local'); fetch('/real');")
    artifact = inspect_artifact(tmp_path)
    assert [r['endpoint'] for r in artifact['files'][0]['literal_requests']] == ['/real']


@pytest.mark.parametrize('suffix', ['html', 'htm', 'jsp', 'hbs', 'ejs', 'pug', 'twig'])
def test_template_form_locations_keep_byte_provenance_and_identity(tmp_path, suffix):
    path = 'client/page.' + suffix
    form = "<form action='/users' method='post'><input name='email'></form>"
    file = write(tmp_path, path, form)
    before = snapshot(tmp_path, 'before')
    call = next(e for e in before['entities'] if e['kind'] == 'frontend_api_call')
    obs = next(o for o in before['observations'] if o['id'] in call['observation_refs'])
    assert obs['locations'] == [{'kind': 'source', 'path': path, 'line': 1}]
    assert obs['source_hashes'] == {path: sha256(file.read_bytes()).hexdigest()}
    file.write_text('\n\n' + form, encoding='utf-8')
    after = snapshot(tmp_path, 'after')
    assert semantic_diff(before, after)['summary'] == {'added': 0, 'removed': 0, 'changed': 0}
    assert location('https://host.test:8080') == {'kind': 'source', 'path': 'https://host.test:8080', 'line': None}


def test_family_coverage_has_independent_methods_scopes_and_limits(tmp_path):
    write(tmp_path, 'server.ts', "import {read} from './repo'; function handler(){read(); opaque[key]();}")
    write(tmp_path, 'repo.ts', 'export function read(){}')
    write(tmp_path, 'opaque.rs', 'fn main() {}')
    context = snapshot(tmp_path, 'coverage')
    families = context['coverage']['relationship_families']
    assert set(families['server.ts']) == {'declarations', 'imports', 'calls', 'type_heritage', 'controls', 'tests'}
    assert families['server.ts']['declarations']['status'] == 'ANALYZED'
    assert families['server.ts']['imports']['status'] == 'ANALYZED'
    assert families['server.ts']['calls']['status'] == 'PARTIAL'
    assert families['server.ts']['calls']['reasons']
    assert families['opaque.rs']['calls']['status'] == 'UNKNOWN'
    for groups in families.values():
        for row in groups.values():
            assert row['method'] and row['scope'] and isinstance(row['reasons'], list)
    malformed = deepcopy(context)
    malformed['coverage']['relationship_families']['server.ts']['calls']['scope'] = 42
    seal_context(malformed)
    with pytest.raises(ValueError, match='coverage'):
        validate_context(malformed)


def test_diff_uses_only_relevant_relationship_family_and_missing_coverage_is_uncertain():
    entities = [{'id': 'a', 'path': 'server.ts'}, {'id': 'b', 'path': 'repo.ts'}]
    coverage = {'files': {p: {'status': 'ANALYZED'} for p in ['server.ts', 'repo.ts']},
                'relationship_families': {'server.ts': {
                    'calls': {'status': 'ANALYZED', 'method': 'fixture', 'scope': {'path': 'server.ts', 'admitted': 'direct calls'}},
                    'imports': {'status': 'PARTIAL'}}}}
    relation = {'id': 'r', 'from': 'a', 'to': 'b', 'relation': 'calls'}
    before = {'schema': 'ases-consumer-context/2.0', 'analysis_profile': {}, 'entities': entities,
              'structural_relations': [relation], 'coverage': coverage}
    after = {**before, 'structural_relations': []}
    assert semantic_diff(before, after)['summary']['removed'] == 1
    for family in ['imports', 'extends', 'protects', 'tests', 'unrecognized']:
        uncertain = {**before, 'structural_relations': [{**relation, 'relation': family}]}
        assert semantic_diff(uncertain, after)['summary']['removed'] == 0
    missing = {**after, 'coverage': {'files': coverage['files']}}
    assert semantic_diff(before, missing)['summary']['removed'] == 0
    changed_profile = {**after, 'analysis_profile': {'coverage': 'another-method'}}
    assert semantic_diff(before, changed_profile)['summary']['removed'] == 0
    changed_scope = deepcopy(after)
    changed_scope['coverage']['relationship_families']['server.ts']['calls']['scope']['admitted'] = 'another subset'
    assert semantic_diff(before, changed_scope)['summary']['removed'] == 0


def test_declaration_coverage_does_not_certify_absent_request_entities():
    before = {'schema': 'ases-consumer-context/2.0', 'analysis_profile': {},
              'coverage': {'files': {'api.ts': {'status': 'ANALYZED'}}},
              'entities': [{'id': 'request', 'kind': 'frontend_api_call', 'path': 'api.ts'}]}
    assert semantic_diff(before, {**before, 'entities': []})['summary']['removed'] == 0


def test_old_profile_snapshots_remain_readable_but_cannot_certify_relation_absence(tmp_path):
    write(tmp_path, 'server.mjs', "function handler(){} app.get('/x', handler);")
    context = snapshot(tmp_path, 'new')
    old = deepcopy(context)
    old['analysis_profile'].update(identity='source-symbol/1', relations='static/1', coverage='scoped/1')
    del old['coverage']['relationship_families']
    seal_context(old)
    validate_context(old)
    after = {**old, 'structural_relations': []}
    assert semantic_diff(old, after)['summary']['removed'] == 0
