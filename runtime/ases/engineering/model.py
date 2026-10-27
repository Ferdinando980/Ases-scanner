"""Recover explicit engineering records and auditable candidates, not stakeholder guesses."""
from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
from hashlib import sha256
import json
import posixpath
import re
from urllib.parse import unquote, urlsplit

from . import SCHEMA
from .api import recover_api
from .inputs import extract_sources
from .requirements import prose_requirement, CLASSIFICATION_PROFILE

TYPED_RECOGNITIONS = {"explicit-html/1", "explicit-html-heading/1", "explicit-html-paragraph/1",
                      "explicit-reqview/1", "explicit-arff/1"}

REQ = re.compile(r"\b(?:RNF|RF)[_-][A-Z][A-Z0-9_]*[_-]\d+\b", re.I)
TEST = re.compile(r"\bTC[_-]\d+(?:[._-]\d+)+\b", re.I)
SHEET_ID = re.compile(r"\s*(?:ID(?:\s+(?:requisito|requirement))?|requirement\s*ID|identificativo(?:\s+requisito)?|codice(?:\s+requisito)?)\s*", re.I)
USECASE = re.compile(r"\b(?:UC|SC|ST)[_-][A-Z][A-Z0-9_]*[_-]\d+\b", re.I)



def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def location(source, unit):
    result = {"path": source["path"], "sha256": source["sha256"]}
    result.update({k: unit[k] for k in ("line", "page", "table", "table_row", "paragraph", "sheet", "row", "element", "document", "row_id", "native_path") if k in unit})
    if unit.get("cells"):
        result["cell"] = ",".join(c["cell"] for c in unit["cells"])
    return result


def record(kind, value, source_document, unit, **extra):
    loc = location(source_document, unit)
    return {"id": kind + ":" + digest([source_document["id"], loc, value])[:24], "kind": kind,
            "authority": "document-declaration", "locations": [loc], "text": value, **extra}


def source_metadata(source):
    text = "\n".join(u["text"] for u in source["units"][:30])
    version = re.search(r"(?:versione|version|ver\.)\s*[: ]?\s*([\d.]+)", text + "\n" + source["path"], re.I)
    approved = re.search(r"(?:approvat[oa]|approved)\s*[: ]\s*([^\n]+)", text, re.I)
    return {"version_declared": version[1] if version else None, "approval_declared": approved[1] if approved else None,
            "scope": "document declaration; release applicability requires review"}


def html_location(raw, fallback):
    """Keep source positions, never accept a supplied source path or digest."""
    unit = {"line": 1, "element": fallback}
    supplied = raw.get("location")
    if isinstance(supplied, dict):
        for key in ("line", "table", "table_row"):
            if isinstance(supplied.get(key), int) and not isinstance(supplied[key], bool) and supplied[key] > 0:
                unit[key] = supplied[key]
        if isinstance(supplied.get("element"), str):
            unit["element"] = supplied["element"][:500]
        for key in ('document', 'row_id'):
            if isinstance(supplied.get(key), str):
                unit[key] = supplied[key][:500]
        if isinstance(supplied.get('path'), list) and all(isinstance(v, str) for v in supplied['path']):
            unit['native_path'] = supplied['path'][:256]
    return unit


def interpret_sources(sources):
    requirements, scenarios, excerpts, cases, results, links, issues, document_api = {}, [], [], [], [], [], [], []
    topics = {
        "purpose": r"scopo|purpose|obiettiv|ambito|scope",
        "current-proposed": r"sistema corrente|sistema proposto|current system|proposed system|prima release|future release",
        "constraint": r"vincol|constraint|must use|deve utilizzare",
        "design-goal": r"\bDG[_-]?\d|design goal|obiettivi di design",
        "decision": r"alternativ|trade.off|decision|scelt[ao]|motivazion",
        "deployment": r"deploy|installaz|installat|hardware|ambiente|environment",
        "persistence": r"persisten|database|transazion",
        "security": r"autorizza|autentica|access control|permiss|security polic",
        "concurrency": r"concorren|concurren|thread|resource|risorse",
        "boundary": r"avvio|arresto|startup|shutdown|recovery|ripristin|falliment",
        "navigation": r"navigazion|mock.?up|sequence diagram|diagramma di sequenza|modello dinamico",
        "glossary": r"glossar|acronim|definizion",
        "test-plan": r"sospension|ripresa|suspend|resume|test strategy|strategia|oracol|oracle|pass/fail|pass.?fail",
        "guide": r"manual|usage|utilizzo|installazione|quick.?start|getting started",
    }
    topics = {topic: re.compile(pattern, re.I) for topic, pattern in topics.items()}
    for source in sources:
        source.update(source_metadata(source))
        source["copy_of"] = next((s["id"] for s in sources if s is not source and s["sha256"] and s["sha256"] == source["sha256"] and s["path"] < source["path"]), None)
        for raw_index, raw in enumerate(source.get("metadata", {}).get("structured_requirements", [])):
            html = isinstance(raw, dict) and raw.get("recognition") in TYPED_RECOGNITIONS
            valid = isinstance(raw, dict) and isinstance(raw.get("id"), str) and bool(raw["id"].strip()) and isinstance(raw.get("statement"), str) and (bool(raw["statement"].strip()) or html and raw.get("statement_missing") is True)
            if valid:
                valid = all(raw.get(k) is None or isinstance(raw[k], str) for k in ("actor", "priority", "oracle", "measurement_context", "scope"))
                valid = valid and ("thresholds" not in raw or isinstance(raw["thresholds"], list) and all(isinstance(v, str) for v in raw["thresholds"]))
                if html and raw.get('recognition') != 'explicit-reqview/1':
                    valid = valid and all(raw.get(k) is None or isinstance(raw[k], str) for k in ("kind", "title", "status"))
            if valid:
                unit = html_location(raw, f"requirements[{raw_index}]") if html else {"line": 1, "element": f"requirements[{raw_index}]"}
                key = raw['id']
                if raw.get('recognition') == 'explicit-arff/1':
                    key = 'arff:' + digest([source['path'], raw.get('project_id'), raw['id']])[:24]
                add_requirement(requirements, key, raw["statement"], source, unit, structured=raw)
                if html:
                    requirements[key]["recognition"] = raw["recognition"]
                    if not raw["statement"].strip():
                        issues.append(record("declared-requirement-without-statement", "Source declares this UID but supplies no statement; content remains unknown", source, unit, record_ref=raw["id"], method="deterministic"))
            else:
                issues.append(record("invalid-structured-requirement", "Requirement record has missing or invalid ID/statement/field types; original input retained", source, {"line": 1, "element": f"requirements[{raw_index}]"}, method="deterministic"))
        table_state = {}
        scope_rules = {}
        prose_fence, prose_section = None, ''
        for index, signature in enumerate(source.get("metadata", {}).get("api_signatures", [])):
            if re.search(r"\b(public|protected|private|class|interface)\b", signature) and "(" in signature:
                document_api.append(record("document-api", signature, source, {"element": f"pre[{index + 1}]"},
                                           signature=signature, status="documented interface; not source syntax"))
        for index, unit in enumerate(source["units"]):
            text = unit["text"]
            loc = location(source, unit)
            # Recover explicit sentences, never labels, commands or fenced examples.
            stripped = text.strip()
            fence = re.match(r'^(`{3,}|~{3,})', stripped)
            if fence and source.get('format') in {'md', 'txt', 'rst', 'adoc'}:
                token = fence[1][0]
                prose_fence = None if prose_fence == token else token
            if stripped.startswith('#'):
                prose_section = stripped.lstrip('# ').casefold()
            prose = re.sub(r'^\s*(?:[-*+]\s+|\d+[.)]\s+)', '', text).strip()
            excluded_context = re.search(r'^(?:esempi|examples?|tutorial|historical|storico|future|futur)\b|^templates?$', prose_section)
            assertion = prose_requirement(prose, prose_section)
            if (assertion and not prose_fence and not fence and not excluded_context and not REQ.search(text)
                    and not unit.get('cells') and not unit.get('tables')
                    and 'structured_requirements' not in source.get('metadata', {})
                    and source.get('format') not in {'puml','mmd','plantuml','drawio','wsd'}
                    and 20 <= len(prose) <= 12000):
                rid = 'prose:' + digest([source['path'], re.sub(r'\s+', ' ', prose).casefold()])[:24]
                add_requirement(requirements, rid, prose, source, unit)
                row = requirements[rid]
                row.update(declared_id=None, identifier_origin='generated-content-key',
                           kind=assertion['classification']['kind'],
                           classification=assertion['classification'], modality=assertion['modality'],
                           modal_text=assertion['modal_text'],
                           subject_missing=assertion['subject_missing'], assertion_form=assertion['assertion_form'],
                           confidence='literal source assertion; classification heuristic; context requires review',
                           recognition='explicit-prose/3')
                if re.search(r'(?:^|/)(?:archive|archives|archivio|historical|history)(?:/|$)', source['path'], re.I):
                    row['declarations'][-1]['scope'] = 'Source path suggests archived material; current release applicability not established'
            family = re.search(r"\b(RF_[A-Z]+)\s*:", text)
            future = re.search(r"(?:non facente parte|non.{0,40}(?:previst|inclus|trattat)|not included|excluded|future).{0,100}(?:prima release|first release|release)", text, re.I | re.S)
            if family and future:
                scope_rules[family[1] + "_"] = {"statement": future[0], "locations": [loc], "status": "declared release exclusion; review versions"}
            matches = list(REQ.finditer(text))
            table_definitions = recover_table_requirements(source, unit, requirements, table_state)
            table_definitions |= recover_sheet_requirements(source, unit, requirements, table_state)
            # A row/paragraph containing an ID may be a reference, not a requirement definition.
            for n, match in enumerate(matches):
                declared_id = match[0].upper().replace("-", "_")
                end = matches[n + 1].start() if n + 1 < len(matches) else len(text)
                statement = text[match.end():end].strip(" |:;-\n")
                if unit.get("cells"):
                    candidates = [c["value"] for c in unit["cells"] if declared_id not in c["value"] and len(re.sub(r"[^A-Za-zÀ-ÿ]", "", c["value"])) > 12]
                    if candidates:
                        statement = max(candidates, key=lambda value: (bool(re.search(r"\b(deve|dovr|shall|must|sistema)\b", value, re.I)), len(value)))
                is_definition = (source["role"] == "RAD" and len(statement) > 12 or bool(unit.get("cells") and len(re.sub(r"[^A-Za-zÀ-ÿ]", "", statement)) > 12)) and declared_id not in table_definitions
                if unit.get("cells") and source["role"] not in {"RAD", "TRACEABILITY"}:
                    formal_context = re.search(r"requirement|requisit|matrix|matric|traceab|tracciab", source["path"] + " " + str(unit.get("sheet", "")), re.I)
                    obligation = re.search(r"\b(?:shall|must|sistema\s+(?:deve|dovr[àa]))\b", statement, re.I)
                    is_definition = is_definition and bool(formal_context or obligation)
                if unit.get("line") and not unit.get("cells"):
                    following = []
                    for next_unit in source["units"][index + 1:index + 15]:
                        if REQ.search(next_unit["text"]) or next_unit["text"].lstrip().startswith("#"):
                            break
                        following.append(next_unit["text"])
                    if following and source["role"] == "RAD":
                        statement += "\n" + "\n".join(following)
                        is_definition = len(statement) > 12
                if is_definition and "structured_requirements" not in source.get("metadata", {}):
                    add_requirement(requirements, declared_id, statement, source, unit)
                links.append(record("reference", text[max(0, match.start() - 50):min(len(text), match.end() + 100)], source, unit,
                                    target=declared_id, relation="mentions", status="explicit-reference; satisfaction unknown"))
            for match in USECASE.finditer(text):
                # Preserve repeated IDs and their different locations; no silent renumbering.
                scenarios.append(record("scenario", text[match.start():match.start() + 3000], source, unit,
                                        declared_id=match[0].upper(), fields_status="partial; original excerpt"))
            if source["role"] in {"TCS", "TP"} and "test_result" not in unit:
                for match in TEST.finditer(text):
                    cases.append(record("test-case", text[max(0, match.start() - 30):match.start() + 3500], source, unit,
                                        declared_id=match[0].upper(), execution="not-observed", oracle="read original excerpt; not inferred"))
            if "test_result" in unit or "counters" in unit:
                results.append(record("test-result", text, source, unit, authority="imported-result",
                                      result=unit.get("test_result"), counters=unit.get("counters"), sessions=unit.get("sessions"),
                                      independent_evidence=not bool(source["copy_of"]), revision_bound=False))
                imported = unit.get("test_result") or {}
                sheet_year = re.search(r"\b(20\d\d)\b", str(unit.get("sheet", "")))
                row_year = re.search(r"\b(20\d\d)\b", str(imported.get("timestamp", "")))
                if sheet_year and row_year and sheet_year[1] != row_year[1]:
                    issues.append(record("result-date-conflict", text[:2000], source, unit, method="deterministic",
                                         meaning="Sheet label and recorded date have different years; historical run identity requires review"))
            if "definition" in unit:
                cases.append(record("automated-definition", text, source, unit, definition=unit["definition"], execution="not-observed"))
            if len(text) > 20:
                for topic, pattern in topics.items():
                    if pattern.search(text):
                        excerpts.append(record(topic, text[:5000], source, unit, interpretation="candidate excerpt; review context"))
            if re.search(r"(?:pass|superat[oa]).{0,100}(?:divers|different|!=|≠)", text, re.I | re.S):
                issues.append(record("possible-inverted-oracle", text[:1500], source, unit, method="heuristic", severity="review"))
            for cell in unit.get("cells", []):
                formula = cell.get("formula")
                if formula:
                    issues.append(record("formula-not-execution", formula, source, unit, method="deterministic",
                                         cell=cell["cell"], cached_value=cell.get("cached_value"), meaning="Formula/cache is not evidence of implementation or execution"))
            if re.search(r"check.?list|(?<![A-Za-z0-9])CL[_-]", source["path"], re.I) and any(str(c.get("value", "")).strip().upper() in {"SI", "SÌ", "YES"} for c in unit.get("cells", [])):
                issues.append(record("checklist-self-report", text[:1000], source, unit, method="deterministic",
                                     meaning="A checklist answer is a declaration, not independent verification of content or contracts"))
        for prefix, declared_scope in scope_rules.items():
            for rid, req in requirements.items():
                if rid.startswith(prefix):
                    req.setdefault("scope_declarations", []).append(declared_scope)
    for req in requirements.values():
        declarations = [d for d in req["declarations"] if d["role"] == "RAD"] or req["declarations"]
        preferred = max(declarations, key=lambda d: (d.get("structured", False), len(d["statement"])))
        req["statement"] = preferred["statement"]
        req["fields"] = preferred["fields"]
        if req.get("recognition") in TYPED_RECOGNITIONS or req.get('recognition') in {'explicit-prose/2', 'explicit-prose/3'}:
            req["statement_missing"] = not bool(req["statement"].strip())
            if req["kind"] == "unspecified":
                issues.append({"id": "kind:" + req["id"], "kind": "requirement-kind-not-declared", "record_ref": req["id"],
                               "method": "deterministic", "meaning": "Source does not declare a functional/nonfunctional kind; classification remains unspecified", "locations": req["locations"]})
        req["scope"] = req.get("scope_declarations") or preferred.get("scope", "unspecified; review source/release")
        comparable = [d for d in req["declarations"] if d.get("structured") or d["role"] != "RAD"] or req["declarations"]
        canonical = lambda value: re.sub(r"[\W_]+", "", value.casefold())
        variants = {canonical(d["statement"]) for d in comparable}
        base_text = canonical(preferred["statement"])
        differences = [v for v in variants if v and SequenceMatcher(None, base_text, v, autojunk=False).ratio() < 0.65]
        actions = lambda value: set(re.findall(r"creat|delet|elimin|cancell|aggiorn|updat|visualizz|view|register|registr|autentic", value.casefold()))
        base_actions = actions(preferred["statement"])
        changed_actions = base_actions and any(actions(d["statement"]) and not base_actions & actions(d["statement"]) for d in comparable)
        if differences or changed_actions:
            issues.append({"id": "variant:" + req["id"], "kind": "declaration-variants", "record_ref": req["id"],
                           "method": "heuristic", "meaning": "Substantially different text for the same declared ID; may be version, excerpt or conflict. Review required.", "locations": req["locations"]})
        if req["kind"] == "nonfunctional" and not req["fields"].get("thresholds"):
            issues.append({"id": "oracle:" + req["id"], "kind": "measurement-context-needed", "record_ref": req["id"], "method": "heuristic",
                           "meaning": "No numeric threshold recovered; a qualitative oracle may still be valid", "locations": req["locations"]})
    defined = set(requirements)
    for link in links:
        link["resolved"] = link["target"] in defined
        link["resolution_scope"] = "Definitions recovered from readable sources only; unread or excluded sources may contain the target"
    # A single matrix row/paragraph can explicitly associate a requirement and test.
    # A whole PDF page containing several unrelated IDs is only co-occurrence.
    test_lookup = defaultdict(list)
    for case in cases:
        if case.get("declared_id"):
            test_lookup[case["declared_id"]].append(case)
    result_lookup = defaultdict(list)
    for result in results:
        name = (result.get("result") or {}).get("name")
        if name and TEST.fullmatch(name):
            result_lookup[name].append(result)
    source_roles = {s["path"]: s["role"] for s in sources}
    specification_lookup = {name: rows for name, rows in test_lookup.items() if any(source_roles.get(r["locations"][0]["path"]) == "TCS" for r in rows)} or test_lookup
    for name in result_lookup.keys() - specification_lookup.keys():
        issues.append({"id": "test-id:" + name, "kind": "test-id-not-in-readable-specification", "method": "deterministic",
                       "text": name, "locations": result_lookup[name][0]["locations"],
                       "meaning": "Imported result ID not found in readable specifications; inspect historical revision, scope and unread sources"})
    if result_lookup:
        for name in specification_lookup.keys() - result_lookup.keys():
            issues.append({"id": "missing-result:" + name, "kind": "test-definition-without-imported-result", "method": "deterministic",
                           "text": name, "locations": test_lookup[name][0]["locations"],
                           "meaning": "Definition not matched by supplied readable reports; this is not a failed test or proof it was never executed"})
    for name in result_lookup.keys() & test_lookup.keys():
        for result in result_lookup[name]:
            for case in test_lookup[name]:
                links.append({"id": "test-result-link:" + digest([case["id"], result["id"]])[:24], "source": case["id"], "target": result["id"],
                              "target_collection": "test_results", "relation": "imported-result-for-id", "resolved": True,
                              "status": "matching declared test ID; revision and environment may differ", "locations": result["locations"]})
    for src in sources:
        sheet_tests = {}
        sheet_cells = {(u.get("sheet"), c["cell"]): (u, c) for u in src["units"] for c in u.get("cells", [])}

        def literal_value(cell, unit):
            if not cell.get("formula"):
                return cell.get("value", ""), None
            formula = cell["formula"].removeprefix("=")
            refs = cell.get("internal_references", [])
            if not re.fullmatch(r"(?:(?:'[^'\[\]]+'|[A-Za-z_][\w ]*)!)?\$?[A-Z]{1,3}\$?\d+", formula) or len(refs) != 1:
                return "", None
            target_unit, target = sheet_cells.get((refs[0]["sheet"], refs[0]["cell"]), ({}, {}))
            if not target or target.get("formula"):
                return "", None
            return target.get("value", ""), location(src, {"sheet": target_unit["sheet"], "row": target_unit["row"], "cells": [target]})

        for unit in src["units"]:
            origins = []
            test_origins = {}
            if unit.get("cells"):
                req_ids, test_ids = set(), set()
                for cell in unit["cells"]:
                    value, origin = literal_value(cell, unit)
                    req_ids.update(REQ.findall(value))
                    test_ids.update(TEST.findall(value))
                    if origin and REQ.fullmatch(value.strip()):
                        origins.append(origin)
                if not any(c.get("formula") for c in unit["cells"]):
                    req_ids.update(REQ.findall(unit["text"]))
                    test_ids.update(TEST.findall(unit["text"]))
                if any(not c.get("formula") and SHEET_ID.fullmatch(c.get("value", "")) for c in unit["cells"]):
                    sheet_tests[unit.get("sheet")] = {
                        re.sub(r"\d+$", "", c["cell"]): (c["value"].strip().upper(), location(src, {**unit, "cells": [c]}))
                        for c in unit["cells"] if not c.get("formula") and TEST.fullmatch(c.get("value", "").strip())}
                for cell in unit["cells"]:
                    column = re.sub(r"\d+$", "", cell["cell"])
                    header = sheet_tests.get(unit.get("sheet"), {}).get(column)
                    if header and not cell.get("formula") and cell.get("value", "").strip().upper() == "X":
                        test_ids.add(header[0])
                        test_origins[header[0]] = [header[1], location(src, {**unit, "cells": [cell]})]
            else:
                req_ids, test_ids = set(REQ.findall(unit["text"])), set(TEST.findall(unit["text"]))
            req_ids = {value.upper().replace("-", "_") for value in req_ids}
            test_ids = {value.upper() for value in test_ids}
            if len(req_ids) == 1 and test_ids and ("cells" in unit or "line" in unit or "paragraph" in unit):
                requirement = next(iter(req_ids))
                for test_id in sorted(test_ids):
                    targets = test_lookup.get(test_id, []) or [None]
                    for target in targets:
                        endpoint = target["id"] if target else test_id
                        link = record("requirement-test-link", unit["text"][:2000], src, unit,
                                      source=requirement, target=endpoint, target_collection="test_cases",
                                      relation="documented-test-reference", resolved=target is not None,
                                      status="explicit association; execution and satisfaction not established" if target else
                                      "declared test ID not found exactly in readable definitions; review required")
                        link["id"] = "requirement-test-link:" + digest([link["id"], requirement, test_id, endpoint])[:24]
                        link["locations"].extend(origins)
                        if test_id in test_origins:
                            link["locations"].extend(test_origins[test_id])
                        links.append(link)
    html_reference_ids = set()
    for src in sources:
        if src.get("format") not in {"html", "htm", "reqw"}:
            continue
        for index, ref in enumerate(src.get("metadata", {}).get("structured_references", [])):
            if not isinstance(ref, dict) or ref.get("source") not in requirements:
                continue
            target, role, href = ref.get("target"), ref.get("native_role"), ref.get("href")
            native = src.get('format') == 'reqw' and href is None
            if not isinstance(target, str) or not target.strip() or not isinstance(role, str) or (not native and (role not in {"parent", "child"} or not isinstance(href, str))):
                continue
            unit = html_location(ref, f"document-reference[{index}]")
            link = record("document-reference", target, src, unit, source=ref["source"], target=target,
                          target_collection="requirements", relation="declared-document-reference", native_role=role, href=href,
                          status="author-declared document reference; execution and satisfaction not established")
            link["id"] = "document-reference:" + digest([link["id"], ref["source"], target, role, href])[:24]
            try:
                parsed = urlsplit(href or '')
                target_path = posixpath.normpath(posixpath.join(posixpath.dirname(src["path"]), unquote(parsed.path))) if parsed.path else src["path"]
                link["resolved"] = (not parsed.scheme and not parsed.netloc and target in requirements and
                                    any(loc["path"] == target_path for loc in requirements[target]["locations"]))
            except ValueError:
                link["resolved"] = False
            link["resolution_scope"] = "Exact declared UID and local document path only; external URLs and alternate document representations remain unresolved"
            if link["id"] not in html_reference_ids:
                links.append(link)
                html_reference_ids.add(link["id"])
    for collection in (requirements.values(), scenarios, cases, excerpts):
        for row in collection:
            row["record_digest"] = digest(row)
    grouped, other = {}, []
    for issue in issues:
        if issue["kind"] not in {"formula-not-execution", "checklist-self-report", "result-date-conflict"}:
            other.append(issue)
            continue
        group_key = (issue["kind"], issue["locations"][0]["path"])
        if group_key not in grouped:
            grouped[group_key] = {**issue, "id": "check:" + digest(group_key)[:24], "occurrences": 0, "locations": [],
                                  "severity": "review" if issue["kind"] == "result-date-conflict" else "information"}
        group = grouped[group_key]
        group["occurrences"] += 1
        if len(group["locations"]) < 100:
            group["locations"].extend(issue["locations"])
    issues = other + list(grouped.values())
    return {"requirements": list(requirements.values()), "scenarios": scenarios, "excerpts": excerpts,
            "test_cases": cases, "test_results": results, "document_api": document_api, "links": links, "issues": issues}


def recover_sheet_requirements(source, unit, requirements, state):
    """Use explicit worksheet headers, with independent state for each sheet."""
    if not unit.get('cells') or not unit.get('sheet'):
        return set()
    cells = {re.sub(r'\d+$', '', c['cell']): c for c in unit['cells']}
    headers = state.setdefault('sheet_headers', {})
    header_ids = [column for column, cell in cells.items()
                  if not cell.get('formula') and SHEET_ID.fullmatch(cell['value'])]
    if header_ids:
        # A new header replaces, rather than inherits, a previous table layout.
        header = {}
        for key, pattern in (('statement', r'(?:descrizione|description|statement)(?:\s+(?:del\s+)?(?:requisito|requirement))?'),
                             ('actor', r'attor[ei]|actors?'), ('priority', r'priorit[àa]|priority')):
            columns = [col for col, cell in cells.items() if not cell.get('formula') and re.fullmatch(r'\s*(?:'+pattern+r')\s*', cell['value'], re.I)]
            if len(columns) == 1: header[key] = columns[0]
        explicit_requirement = any(re.search(r'requisito|requirement', cells[col]['value'], re.I) for col in header_ids)
        admitted = source['role'] in {'RAD', 'TRACEABILITY'} or explicit_requirement
        headers[unit['sheet']] = {'id': header_ids[0], **header} if admitted and len(header_ids) == 1 and 'statement' in header else None
        return set()
    header = headers.get(unit['sheet'])
    if not header: return set()
    identifier = cells.get(header['id'], {})
    match = REQ.fullmatch(identifier.get('value', '').strip())
    statement = cells.get(header['statement'], {})
    if not match or not statement.get('value') or len(statement['value']) < 12:
        return set()
    declared_id = match[0].upper().replace('-', '_')
    if identifier.get('formula') or statement.get('formula'):
        # Cache/formula provenance remains in the source; it is not authored text.
        return {declared_id}
    fields = {'statement': statement['value']}
    for key in ('actor', 'priority'):
        cell = cells.get(header.get(key), {})
        fields[key] = None if cell.get('formula') else cell.get('value') or None
    add_requirement(requirements, declared_id, statement['value'], source, unit, structured=fields)
    return {declared_id}


def recover_table_requirements(source, unit, requirements, state=None):
    recovered = set()
    if source["role"] != "RAD":
        return recovered
    state = state if state is not None else {}
    for table_index, table in enumerate(unit.get("tables", [])):
        header, current, pieces = state.get("header") if "page" in unit else None, None, []
        def finish():
            if current is None or not header:
                return
            joined = ["\n".join(v).strip() for v in zip(*pieces)]
            description_index = next((i for i, value in enumerate(header) if re.search(r"descrizion|description|statement", value, re.I)), None)
            if description_index is None or description_index >= len(joined):
                return
            statement = joined[description_index]
            if len(statement) < 12:
                return
            fields = {"statement": statement}
            for key, pattern in (("actor", r"attor|actor"), ("priority", r"priorit")):
                column = next((i for i, value in enumerate(header) if re.search(pattern, value, re.I)), None)
                if column is not None and column < len(joined):
                    fields[key] = joined[column] or None
            priority_pattern = r"(?:Elevat[ao]|Alt[ao]|Bass[ao]|Medi[ao]|High|Low|Medium|Must|Should|Could)"
            if not fields.get("priority") or not re.fullmatch(priority_pattern, fields["priority"], re.I):
                declared_priorities = [v for v in joined if re.fullmatch(priority_pattern, v.strip(), re.I)]
                if declared_priorities:
                    fields["priority"] = declared_priorities[0].strip()
            loc = {"table": unit.get("table_index", table_index + 1), "table_row": current[1]}
            if "page" in unit: loc["page"] = unit["page"]
            if "element" in unit: loc["element"] = unit["element"]
            add_requirement(requirements, current[0], statement, source, loc, structured=fields)
            recovered.add(current[0])
        for row_index, row in enumerate(table):
            values = [str(c or "") for c in row]
            if any(re.search(r"^\s*(descrizione|description|statement)\s*$", c, re.I) for c in values):
                finish()
                header, current, pieces = values, None, []
                state["header"] = header
                continue
            ids = REQ.findall(" ".join(values))
            if ids:
                finish()
                current, pieces = (ids[0].upper().replace("-", "_"), row_index + 1), [values]
            elif current and len(values) == len(pieces[0]):
                pieces.append(values)
        finish()
    return recovered


def add_requirement(requirements, declared_id, statement, source, unit, structured=None):
    loc = location(source, unit)
    kind = "nonfunctional" if declared_id.startswith("RNF") else "functional"
    html = bool(structured and structured.get("recognition") in TYPED_RECOGNITIONS)
    if html:
        declared_kind = (structured.get("kind") or "").strip().casefold()
        kind = {"functional": "functional", "rf": "functional", "nonfunctional": "nonfunctional", "non-functional": "nonfunctional", "rnf": "nonfunctional"}.get(declared_kind,
            "nonfunctional" if declared_id.startswith("RNF_") else "functional" if declared_id.startswith("RF_") else "unspecified")
    row = requirements.setdefault(declared_id, {"id": declared_id, "declared_id": declared_id,
        "kind": kind, "authority": "document-declaration",
        "locations": [], "declarations": [], "confidence": "explicit ID; fields partial", "satisfaction": "not-verified"})
    if html:
        row['classification'] = {'kind': kind, 'origin': 'source-declared' if kind != 'unspecified' else 'unspecified',
                                 'source_kind': structured.get('source_kind'), 'categories': [], 'evidence': []}
        row['recognition'] = structured['recognition']
        for key in ('identifier_origin', 'source_kind', 'project_id', 'document_id'):
            if key in structured:
                row[key] = structured[key]
        if structured.get('identifier_origin') == 'generated-row-key':
            row['declared_id'] = None
        elif structured.get('recognition') == 'explicit-arff/1':
            row['declared_id'] = structured.get('declared_id')
        if structured.get('recognition') == 'explicit-reqview/1':
            row['native_declared_id'] = structured.get('declared_id')
    fields = {"actor": None, "priority": None, "oracle": None,
              "thresholds": re.findall(r"\b\d+(?:[.,]\d+)?\s*(?:second[io]|seconds?|ms|%|ore|hours?|utenti|users?)(?=\s|[.,;:!?)]|$)", statement, re.I)}
    if structured:
        fields.update({k: structured[k] for k in ("actor", "priority", "oracle", "thresholds", "measurement_context") if k in structured})
        if html:
            fields.update({k: structured[k] for k in ("title", "status") if isinstance(structured.get(k), str)})
            fields['source_attributes'] = structured.get('attributes', {})
    else:
        priority = re.search(r"\b(Elevat[ao]|Alta|Bassa|Media|High|Low|Medium|Must|Should|Could)\b", statement, re.I)
        fields["priority"] = priority[0] if priority else None
    row["locations"].append(loc)
    row["declarations"].append({"statement": statement, "locations": [loc], "role": source["role"], "fields": fields, "structured": bool(structured),
                                "scope": structured.get("scope", "unspecified; review source/release") if structured else "unspecified; review source/release"})


def build_engineering(root, inventory, graph, semantic, snapshot_id, progress=None):
    sources, coverage = extract_sources(root, inventory, progress)
    if progress:
        progress("document-analysis")
    interpreted = interpret_sources(sources)
    api, api_coverage = recover_api(root, graph, inventory, progress)
    from .behavior import interpret_behavior, BEHAVIOR_PROFILE
    recovered_requirements, behavior_coverage = interpret_behavior(root, inventory, graph, semantic, api, progress)
    declared = {r["id"] for r in interpreted["requirements"]}
    api_targets = {r["entity_ref"]: r["id"] for r in api if r.get("entity_ref")}
    for recovered in recovered_requirements:
        for entity in recovered["entity_refs"]:
            if entity in api_targets:
                interpreted["links"].append({"id": "behavior-link:" + digest([recovered["id"], entity])[:24],
                                             "source": recovered["id"], "target": api_targets[entity], "target_collection": "api", "resolved": True,
                                             "relation": "supported-by-interface-body", "status": "bounded static reconstruction; not proof of runtime execution",
                                             "authority": "static-inference",
                                             "locations": [loc for loc in recovered["locations"] if loc.get("entity_ref") == entity]})
    for item in api:
        item["record_digest"] = digest(item)
        for rid in set(REQ.findall(item.get("responsibility") or "")):
            interpreted["links"].append({"id": "link:" + digest([item["id"], rid])[:24], "source": item["id"], "target": rid,
                                         "relation": "comment-reference", "status": "declared link; not verification", "resolved": rid in declared,
                                         "locations": item["locations"], "authority": "document-declaration"})
    model = {"schema": SCHEMA, "snapshot_id": snapshot_id, "sources": sources, **interpreted, "api": api,
             "recovered_requirements": recovered_requirements, "behavior_coverage": behavior_coverage,
             "behavior_profile": BEHAVIOR_PROFILE,
             "narrative_profile": "controlled-narrative/6",
             "entry_selection_profile": "entry-selection/2",
             "operations_profile": "explicit-entry-operations/4",
             "design_review_coverage":semantic.get('design_review_coverage'),
             "api_coverage": api_coverage, "coverage": coverage,
             "structure": {k: semantic.get(k, []) for k in ("actors", "components", "interfaces", "data_stores", "trust_boundaries", "behaviors", "tests", "controls", "trace_links", "architecture_patterns", "pattern_findings", "pattern_hints", "frontend", "frontend_findings", "conformance_findings", "cross_boundary_findings", "conflicts", "unknowns")},
             "relations": graph.get("edges", []),
             "diagrams": build_diagrams(api, graph.get("edges", [])),
             "unknowns": ["Original intent and satisfaction need stakeholder/test evidence.",
                          "Free prose, diagrams and historical release scope are interpreted partially; consult cited originals.",
                          "No target code, documentation script, build or test was executed."]}
    from ..scanners.java_syntax import parser_profile as java_parser_profile
    from ..scanners.python_http import PROFILE as http_profile
    model["behavior_parser_profiles"] = {"java": java_parser_profile(), "python_http": http_profile}
    model["document_profile"] = "inert-documents/9"
    model['requirement_classification_profile'] = CLASSIFICATION_PROFILE
    model["analysis_scope"] = {"source_paths": sorted(s["path"] for s in inventory.get("source_manifest", [])),
                               "exclusions": inventory.get("exclusions", []),
                               "policy": inventory.get("source_scope", {}).get("policy")}
    model['entry_selection'] = {
        'profile':'entry-selection/2',
        'mode':'recognized-http-handlers' if semantic.get('behaviors') else 'public-library-callables',
        'max_entries':1000,
        'internal_summaries':'own-body only, using remaining budget after primary entries',
        'meaning':'Recognized HTTP entries define the behavior view when present. Otherwise public callable APIs are selected; application paths precede auxiliary benchmark/example/work trees and the budget is spread across files. Private, nested, package and conditional callable bodies may receive separately scoped internal summaries using the remaining budget; other declarations remain in the API inventory. Conditional availability and runtime execution are not established. This is not complete feature coverage.'}
    from .operations import build_operations
    model["operations"], operation_links = build_operations(model)
    model["links"].extend(operation_links)
    model["user_requirements"] = []
    from .quality import check_documents
    checks, model["quality_controls"] = check_documents(model)
    model["issues"].extend(checks)
    model["model_digest"] = digest(model)
    return model


def build_diagrams(api, edges):
    groups = defaultdict(list)
    for row in api:
        groups[row["path"]].append(row)
    diagrams = []
    for path, rows in sorted(groups.items()):
        types = [r for r in rows if r["kind"] in {"class", "interface", "record", "enum"}]
        if types:
            nodes = [{"id": r["entity_ref"] or r["id"], "name": r["name"], "kind": r["kind"],
                      "members": [m["signature"] for m in rows if m.get("owner") in {r["name"], r.get("qualified_name")} and m is not r],
                      "authority": "source-syntax"} for r in types[:30]]
        else:
            nodes = [{"id": "module-view:" + digest(path)[:20], "name": path, "kind": "module",
                      "members": [r["signature"] for r in rows[:30]], "authority": "source-syntax"}]
        ids = {n["id"] for n in nodes}
        relations = [e for e in edges if e["source"] in ids and e["target"] in ids and e["relation"] in {"extends", "implements", "depends_on"}]
        diagrams.append({"id": "diagram:" + digest(path)[:20], "name": path, "kind": "static-class-module-diagram", "authority": "static-inference",
                         "locations": rows[0]["locations"], "nodes": nodes, "edges": relations, "omitted_types": max(0, len(types) - 30),
                         "limits": "At most 30 types per file. Declaration membership and supported static relationships only; no cardinalities or execution order."})
    return diagrams


def engineering_diff(before, after):
    """Record changes and outward links; disappearance is never called resolution."""
    def index(model):
        return {r["id"]: r for key in ("requirements", "recovered_requirements", "api", "scenarios", "test_cases", "operations", "user_requirements") for r in model.get(key, [])}
    old, new = index(before), index(after)
    changed = {key for key in old.keys() & new.keys() if old[key].get("record_digest") != new[key].get("record_digest") or old[key].get("user_context") != new[key].get("user_context")}
    touched = changed | (old.keys() - new.keys()) | (new.keys() - old.keys())
    impacted = [link for link in after.get("links", []) + before.get("links", []) if link.get("source") in touched or link.get("target") in touched]
    def fields(row):
        return {key: row.get(key) for key in ("statement", "statement_it", "statement_en", "conditions", "external_outcomes", "effects", "errors", "fields", "signature", "params", "return_type", "contracts", "attributes", "bases", "errors_declared", "declared_throws", "guards_observed", "scope", "user_context", "author", "acceptance", "support_state", "entry_scope", "entry_visibility", "conditional_declaration", "declaration_context", "kind", "classification", "modality", "subject_missing") if key in row}
    field_changes = [key for key in changed if fields(old[key]) != fields(new[key])]
    sections = set()
    analysis_ids = {r["id"] for model in (before,after) for collection in ("requirements", "recovered_requirements", "operations", "user_requirements") for r in model.get(collection, [])}
    for key in set(field_changes) | (new.keys()-old.keys()) | (old.keys()-new.keys()):
        sections.update(("RAD", "SDD", "ODD") if key in analysis_ids else ("ODD",))
    if impacted:
        sections.update(("TRACEABILITY", "TESTING"))
    if any(before.get(key) != after.get(key) for key in ("behavior_profile", "behavior_parser_profiles", "narrative_profile", "operations_profile", "document_profile", "entry_selection_profile", "requirement_classification_profile")):
        sections.update(("RAD", "SDD", "ODD"))
    from .changes import review_changes
    review = review_changes(before, after, fields)
    if review["configured_scope_changed"] or review["source_set_changed"]:
        sections.update(("RAD", "SDD", "ODD", "COVERAGE"))
    return {"added": sorted(new.keys() - old.keys()), "missing": sorted(old.keys() - new.keys()), "changed": sorted(changed),
            "behavior_method_changed": before.get("behavior_profile") != after.get("behavior_profile"),
            "behavior_parser_changed": before.get("behavior_parser_profiles") != after.get("behavior_parser_profiles"),
            "document_method_changed": before.get("document_profile") != after.get("document_profile"),
            "narrative_method_changed": before.get("narrative_profile") != after.get("narrative_profile"),
            "operations_method_changed": before.get("operations_profile") != after.get("operations_profile"),
            "entry_selection_method_changed": before.get("entry_selection_profile") != after.get("entry_selection_profile"),
            "changed_supported_fields": sorted(field_changes), "unchanged_supported_fields": sorted(changed - set(field_changes)),
            **review, "sections_to_review": sorted(sections),
            "linked_impact": impacted, "interpretation": "Review source scope and semantic content; formatting can change locations/digests. Unchanged supported fields do not prove semantic equivalence. Missing is not resolved."}
