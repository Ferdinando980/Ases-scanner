"""Regression matrix for the three discrepancies measured by the accuracy corpus."""
from pathlib import Path

import pytest

from ases.accuracy import evaluate_corpus
from ases.pipeline import scan_project
from ases.scanners.javascript import EXTENSIONS, scan_javascript


def write(root, name, source):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


@pytest.mark.parametrize("binding,call", [
    ("import path from 'node:path';", "path.join('a', 'b')"),
    ("import * as p from 'path';", "p.join('a', 'b')"),
    ("const p = require('node:path');", "p.resolve('a')"),
    ("import {join as merge} from 'node:path';", "merge('a', 'b')"),
    ("import helpers from 'lodash';", "helpers.merge({}, {})"),
    ("import api from 'my-openai-utils';", "api.merge({}, {})"),
])
def test_imported_utilities_remain_calls_without_becoming_boundaries(tmp_path, binding, call):
    write(tmp_path, "server.mjs", binding + f"\nfunction handler() {{ return {call}; }}\napp.get('/local', handler);")
    out = tmp_path / "scan.ases"
    scan = scan_project(tmp_path, out)
    graph = scan["graph"]
    calls = [n for n in graph["nodes"] if n["kind"] == "library_call"]
    assert len(calls) == 1 and calls[0]["name"] == call.split("(")[0]
    assert calls[0]["metadata"]["imports"] and not calls[0]["metadata"]["client_call_observed"]
    assert any(edge["target"] == calls[0]["id"] and edge["relation"] == "calls" for edge in graph["edges"])
    assert not any(n["kind"] == "external_api_call" for n in graph["nodes"])
    assert not scan["semantic_model"]["sensitive_paths"]
    assert scan["validation"]["status"] == "PASS"


@pytest.mark.parametrize("package", ["openai", "@anthropic-ai/sdk", "@aws-sdk/client-s3"])
def test_service_clients_keep_static_usage_without_claiming_execution(tmp_path, package):
    write(tmp_path, "server.mjs", f"import Client from '{package}';\nconst client = new Client();\nfunction handler() {{ return client.send({{}}); }}\napp.post('/remote', handler);")
    scan = scan_project(tmp_path, tmp_path / "scan.ases")
    clients = [n for n in scan["graph"]["nodes"] if n["kind"] == "external_api_call"]
    assert len(clients) == 1 and clients[0]["metadata"]["client_call_observed"]
    assert clients[0]["metadata"]["network_effect"] == "unverified"
    assert scan["semantic_model"]["sensitive_paths"][0]["destination"]["kind"] == "external_api_call"


@pytest.mark.parametrize("binding,call", [
    ("import transport from 'node:https';", "transport.get('https://example.test')"),
    ("const transport = require('http');", "transport.request(options)"),
    ("import {get as download} from 'https';", "download('https://example.test')"),
])
def test_node_http_requests_are_not_lost_when_module_utilities_are_separated(tmp_path, binding, call):
    write(tmp_path, "server.mjs", binding + f"\nfunction handler(){{return {call};}}\napp.get('/proxy', handler);")
    scan = scan_project(tmp_path, tmp_path / "scan.ases")
    assert len([n for n in scan["graph"]["nodes"] if n["kind"] == "external_api_call"]) == 1
    assert scan["semantic_model"]["sensitive_paths"]


def test_node_http_server_construction_is_not_an_outbound_request(tmp_path):
    write(tmp_path, "server.mjs", "import http from 'node:http'; function setup(){return http.createServer(handler);}")
    graph = scan_javascript(tmp_path)
    assert any(n.kind == "library_call" and n.name == "http.createServer" for n in graph.nodes)
    assert not any(n.kind == "external_api_call" for n in graph.nodes)


@pytest.mark.parametrize("extension", sorted(EXTENSIONS))
def test_observer_suffix_matrix_positive_and_near_negatives(tmp_path, extension):
    write(tmp_path, "direct" + extension,
          "function notifyAll(){ mailListener.update(); auditListener.update(); billingListener.update(); }")
    write(tmp_path, "noise" + extension, '''// mailListener.update(); auditListener.update(); billingListener.update();
const example = "mailListener.update(); auditListener.update(); billingListener.update();";
const mailListener = 1, auditListener = 2, billingListener = 3;
''')
    model = scan_project(tmp_path, tmp_path / "scan.ases")["semantic_model"]
    findings = [f for f in model["pattern_findings"] if f["rule_id"] == "opportunity.observer_fanout"]
    assert len(findings) == 1
    assert all(item.startswith("direct" + extension + ":") for item in findings[0]["evidence"])


@pytest.mark.parametrize("binding,constructor", [
    ("import {EventEmitter} from 'node:events';", "EventEmitter"),
    ("import {EventEmitter as Bus} from 'events';", "Bus"),
    ("import Bus from 'node:events';", "Bus"),
    ("import * as events from 'node:events';", "events.EventEmitter"),
    ("const {EventEmitter: Bus} = require('events');", "Bus"),
    ("const Bus = require('node:events');", "Bus"),
    ("const events = require('node:events');", "events.EventEmitter"),
])
def test_existing_event_emitters_are_counterevidence_not_a_new_opportunity(tmp_path, binding, constructor):
    write(tmp_path, "events.mjs", binding + f"""
const mailListener = new {constructor}();
const auditListener = new {constructor}();
const billingListener = new {constructor}();
function publish() {{
 mailListener.emit('updated'); auditListener.emit('updated'); billingListener.emit('updated');
}}
""")
    scan = scan_project(tmp_path, tmp_path / "scan.ases")
    emissions = [n for n in scan["graph"]["nodes"] if n["name"].endswith(".emit")]
    assert len(emissions) == 3
    assert all(n["metadata"].get("pubsub_receiver") == "node-events" for n in emissions)
    assert not any(f["rule_id"] == "opportunity.observer_fanout" for f in scan["semantic_model"]["pattern_findings"])


def test_pubsub_does_not_silence_direct_calls_or_shadowed_receivers(tmp_path):
    write(tmp_path, "events.js", """import {EventEmitter} from 'node:events';
const mail = new EventEmitter(), audit = new EventEmitter(), billing = new EventEmitter();
function publish(){ mail.emit('updated'); audit.emit('updated'); billing.emit('updated'); }
function direct(mail, audit, billing){
 mail.emit('updated'); audit.emit('updated'); billing.emit('updated');
}
""")
    model = scan_project(tmp_path, tmp_path / "scan.ases")["semantic_model"]
    findings = [f for f in model["pattern_findings"] if f["rule_id"] == "opportunity.observer_fanout"]
    assert len(findings) == 1
    assert "3 distinct notification consumers" in findings[0]["signals"]["positive"]


def test_same_line_shadowing_is_not_suppressed_as_proven_pubsub(tmp_path):
    write(tmp_path, "events.js", """import {EventEmitter} from 'node:events';
const mail = new EventEmitter(), audit = new EventEmitter(), billing = new EventEmitter();
function publish(){mail.emit('x');audit.emit('x');billing.emit('x');} function direct(mail,audit,billing){mail.emit('x');audit.emit('x');billing.emit('x');}
""")
    model = scan_project(tmp_path, tmp_path / "scan.ases")["semantic_model"]
    assert any(f["rule_id"] == "opportunity.observer_fanout" for f in model["pattern_findings"])


@pytest.mark.parametrize("mutation", [
    "alias.emit = local;",
    "alias['emit'] = local;",
    "EventEmitter = local;",
])
def test_mutated_instances_or_constructors_do_not_supply_counterevidence(tmp_path, mutation):
    write(tmp_path, "events.js", """import {EventEmitter} from 'node:events';
const bus = new EventEmitter();
const alias = bus;
""" + mutation + "\nfunction publish(){bus.emit('x');alias.emit('y');}\n")
    emissions = [n for n in scan_javascript(tmp_path).nodes if n.name.endswith(".emit")]
    assert all("pubsub_receiver" not in node.metadata for node in emissions)


def test_parser_unknown_scope_cannot_be_bypassed_by_new_suffix_rules(tmp_path):
    (tmp_path / "invalid.mjs").write_bytes(b"\xff mailListener.update();auditListener.update();billingListener.update();")
    scan = scan_project(tmp_path, tmp_path / "scan.ases")
    assert scan["graph"]["coverage"]["invalid.mjs"]["status"] == "UNKNOWN"
    assert not any(f["rule_id"] == "opportunity.observer_fanout" for f in scan["semantic_model"]["pattern_findings"])


def test_original_accuracy_labels_all_pass_after_corrections(tmp_path):
    corpus = Path(__file__).parent / "fixture_accuracy/corpus.json"
    result = evaluate_corpus(corpus, tmp_path / "accuracy.ases")
    assert result["passed"]
    assert len(result["cases"]) == 16
    assert all(all(row["metamorphic"].values()) for row in result["cases"].values())
