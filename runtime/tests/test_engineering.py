"""Own synthetic oracles; no course slides, external project files or private runs."""
import json
from pathlib import Path
import sys
import zipfile
from xml.sax.saxutils import escape

import pytest

from ases.pipeline import scan_project
from ases.engineering.api import recover_api
from ases.engineering.inputs import extract_sources, read_input
from ases.engineering.model import digest, interpret_sources, engineering_diff
from ases.engineering.service import apply_review, regenerate, load_model


def source(text, role="RAD", **unit):
    return {"id": "doc:rad", "path": "docs/RAD.md", "sha256": "a" * 64, "role": role,
            "units": [{"text": text, **unit}], "limitations": [], "metadata": {}}


def workbook(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml", '<workbook xmlns:r="urn:relationships"><sheets><sheet name="Requirements" r:id="r1"/><sheet name="Implementation" r:id="r2"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/><Relationship Id="r2" Target="worksheets/sheet2.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", '<worksheet><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>RF_ORD_1</t></is></c><c r="B1" t="inlineStr"><is><t>The clerk shall record the order.</t></is></c></row></sheetData></worksheet>')
        z.writestr("xl/worksheets/sheet2.xml", '<worksheet><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>RF_ORD_1</t></is></c><c r="B1"><f>IF(A1="High","X","")</f><v>1</v></c></row></sheetData></worksheet>')


def write_xlsx(path, sheets):
    """Write a small inert workbook from rows of {cell: value-or-formula-record}."""
    sheet_names = list(sheets)
    workbook_xml = '<workbook xmlns:r="urn:relationships"><sheets>' + ''.join(
        f'<sheet name="{escape(name)}" r:id="r{i}"/>' for i, name in enumerate(sheet_names, 1)) + '</sheets></workbook>'
    relationships = '<Relationships>' + ''.join(
        f'<Relationship Id="r{i}" Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, len(sheet_names) + 1)) + '</Relationships>'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml", workbook_xml)
        z.writestr("xl/_rels/workbook.xml.rels", relationships)
        for sheet_index, (name, rows) in enumerate(sheets.items(), 1):
            row_xml = []
            for row_index, row in enumerate(rows, 1):
                cells = []
                for address, raw in row.items():
                    if isinstance(raw, dict):
                        value, formula = raw.get("value", ""), raw.get("formula")
                    else:
                        value, formula = raw, None
                    if formula is None:
                        cells.append(f'<c r="{address}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
                    else:
                        cells.append(f'<c r="{address}" t="str"><f>{escape(formula)}</f><v>{escape(str(value))}</v></c>')
                row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
            z.writestr(f"xl/worksheets/sheet{sheet_index}.xml", '<worksheet><sheetData>' + ''.join(row_xml) + '</sheetData></worksheet>')


def pdf(path, pages):
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b""]
    ids = []
    for text in pages:
        page_id, stream_id = len(objects) + 1, len(objects) + 2
        ids.append(page_id)
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents {stream_id} 0 R >>".encode())
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content = ("BT /F1 12 Tf 40 720 Td (" + escaped + ") Tj ET").encode()
        objects.append(f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream")
    objects[1] = f"<< /Type /Pages /Count {len(ids)} /Kids [ {' '.join(str(i) + ' 0 R' for i in ids)} ] >>".encode()
    data, offsets = b"%PDF-1.4\n", [0]
    for i, obj in enumerate(objects):
        offsets.append(len(data))
        data += f"{i + 1} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(data)
    data += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    data += b"".join(f"{n:010d} 00000 n \n".encode() for n in offsets[1:])
    data += f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    path.write_bytes(data)


def project(tmp_path):
    root = tmp_path / "shop"
    root.mkdir()
    (root / "requirements.yaml").write_text('requirements:\n  - id: RF_ORD_1\n    statement: The clerk shall record the order.\n    actor: Clerk\n    priority: High\n    oracle: Persisted order has its assigned identifier.\n  - id: RNF_P_1\n    statement: Response within 2 seconds under 20 users.\n    measurement_context: p95 on the declared test machine\n', encoding="utf-8")
    (root / "api.py").write_text('class Orders:\n    """Order storage.\n    @invariant IDs are unique.\n    """\n    def add(self, title: str, *, urgent: bool = False) -> int:\n        """RF_ORD_1\n        @pre title must not be empty\n        @post returns the saved identifier\n        """\n        if not title:\n            raise ValueError("title")\n        return 1\n', encoding="utf-8")
    return root


def test_requirements_fields_contracts_and_documents(tmp_path):
    root = project(tmp_path)
    result = scan_project(root, tmp_path / "scan")
    model = result["engineering_model"]
    assert len(model["requirements"]) == 2
    req = next(r for r in model["requirements"] if r["id"] == "RF_ORD_1")
    assert req["fields"]["actor"] == "Clerk"
    assert req["fields"]["oracle"].startswith("Persisted")
    assert req["satisfaction"] == "not-verified"
    method = next(r for r in model["api"] if r["name"] == "add")
    assert method["signature"] == "def add(self, title: str, *, urgent: bool=False) -> int"
    assert [c["kind"] for c in method["contracts"]] == ["precondition", "postcondition"]
    assert method["guards_observed"] == ["not title"]
    assert all(c["kind"] != "invariant" for c in method["contracts"])
    assert method["entity_ref"]
    assert any(l.get("source") == method["id"] and l["target"] == "RF_ORD_1" for l in model["links"])
    for name, expected in (("RAD.md", "The clerk shall record"), ("ODD.md", "def add(self"), ("TCS.md", "TCS"), ("DOCUMENT-QUALITY.md", "sources")):
        assert expected in (tmp_path / "scan/docs" / name).read_text(encoding="utf-8")
    import jsonschema
    schema = json.loads((Path(__file__).parents[1] / "ases/engineering/resources/engineering-model.schema.json").read_text())
    jsonschema.validate(model, schema)
    assert load_model(tmp_path / "scan")["model_digest"] == model["model_digest"]


def test_all_workbook_sheets_and_formula_semantics(tmp_path):
    path = tmp_path / "matrix.xlsx"
    workbook(path)
    units, status, _, _ = read_input(path, lambda: None)
    assert status == "complete"
    assert {u["sheet"] for u in units} == {"Requirements", "Implementation"}
    assert units[1]["cells"][1]["formula"] == 'IF(A1="High","X","")'
    assert units[1]["cells"][1]["cached_value"] == "1"
    src = source("", role="TRACEABILITY")
    src["units"] = units
    model = interpret_sources([src])
    assert len(model["requirements"]) == 1
    assert model["requirements"][0]["satisfaction"] == "not-verified"
    assert any(i["kind"] == "formula-not-execution" for i in model["issues"])


@pytest.mark.parametrize("role", ["TRACEABILITY", "OTHER"])
def test_explicit_requirement_matrix_headers_preserve_structured_fields(tmp_path, role):
    path = tmp_path / "traceability.xlsx"
    write_xlsx(path, {
        "Requirements": [
            {"A1": "ID Requisito", "B1": "Descrizione", "C1": "Attori", "D1": "Priorità"},
            {"A2": "RF_MATRIX_1", "B2": "The clerk can register an order.", "C2": "Clerk", "D2": "High"},
            {"A3": "RF_MATRIX_2", "B3": "The clerk can cancel an order.", "C3": "Clerk",
             "D3": {"formula": '"High"', "value": "High"}},
        ],
        "Generic": [
            {"A1": "ID", "B1": "Descrizione", "C1": "Attori", "D1": "Priorità"},
            {"A2": "RF_OTHER_9", "B2": "The user shall select a book.", "C2": "Reader", "D2": "High"},
        ],
    })
    units, status, _, _ = read_input(path, lambda: None)
    assert status == "complete"
    src = source("", role=role)
    src.update(path="docs/traceability.xlsx", units=units)
    model = interpret_sources([src])
    requirements = {row["id"]: row for row in model["requirements"]}
    assert requirements["RF_MATRIX_1"]["fields"]["actor"] == "Clerk"
    assert requirements["RF_MATRIX_1"]["fields"]["priority"] == "High"
    assert requirements["RF_MATRIX_2"]["fields"]["actor"] == "Clerk"
    assert requirements["RF_MATRIX_2"]["fields"]["priority"] is None
    generic = requirements.get("RF_OTHER_9")
    if role == "OTHER" and generic:
        assert generic["fields"]["actor"] is None and generic["fields"]["priority"] is None
        assert not any(declaration["structured"] for declaration in generic["declarations"])
    assert any(issue["kind"] == "formula-not-execution" and issue["cached_value"] == "High"
               for issue in model["issues"])


def test_literal_test_matrix_markers_and_direct_requirement_references_are_linked(tmp_path):
    path = tmp_path / "matrix.xlsx"
    write_xlsx(path, {
        "Matrix": [
            {"A1": "Requirement ID", "B1": "TC_1.1_1", "C1": "TC_1.1_2"},
            {"A2": "RF_MATRIX_1", "B2": "X", "C2": "X"},
            {"A3": {"formula": "Sintesi!A7", "value": ""}, "C3": "X"},
            {"A4": "RF_MATRIX_3", "B4": {"formula": 'IF(TRUE,"X","")', "value": "X"},
             "C4": {"formula": 'IF(TRUE,"X","")', "value": "X"}},
            {"A5": "RF_MATRIX_4"},
            {"A6": "RF_MATRIX_5", "C6": {"formula": "[outside.xlsx]Sintesi!A7", "value": "X"}},
            {"A7": "RF_MATRIX_6", "C7": {"formula": 'Sintesi!A7&"suffix"', "value": "X"}},
            {"A8": "RF_MATRIX_7", "C8": {"formula": "Sintesi!A6", "value": "RF_MATRIX_2"}},
        ],
        "Sintesi": [{}, {}, {}, {}, {}, {"A6": {"formula": "A7", "value": "RF_MATRIX_2"}},
                    {"A7": "RF_MATRIX_2"}],
        "NoHeader": [
            {"A1": "Notes", "B1": "TC_1.1_1"},
            {"A2": "RF_NO_HEADER_1", "B2": "X"},
        ],
    })
    units, status, _, _ = read_input(path, lambda: None)
    assert status == "complete"
    matrix = source("", role="TRACEABILITY")
    matrix.update(path="docs/matrix.xlsx", units=units)
    spec = source("TC_1.1_1 First test case.\nTC_1.1_2 Second test case.", role="TCS", page=1)
    spec.update(id="doc:tcs", path="docs/TCS.md", sha256="b" * 64)
    model = interpret_sources([matrix, spec])
    cases = {case["declared_id"]: case for case in model["test_cases"]}
    links = [link for link in model["links"] if link["relation"] == "documented-test-reference"]
    literal_links = [link for link in links if link["source"] == "RF_MATRIX_1"]
    assert {link["target"] for link in literal_links} == {cases["TC_1.1_1"]["id"], cases["TC_1.1_2"]["id"]}
    assert all(link["resolved"] is True for link in literal_links)
    assert len({link["id"] for link in literal_links}) == 2
    direct_link = next(link for link in links if link["source"] == "RF_MATRIX_2")
    assert direct_link["target"] == cases["TC_1.1_2"]["id"]
    assert direct_link["resolved"] is True
    direct_locations = direct_link["locations"]
    assert any(loc.get("sheet") == "Matrix" and loc.get("row") == 1 and loc.get("cell") == "C1" for loc in direct_locations)
    assert any(loc.get("sheet") == "Matrix" and loc.get("row") == 3 and "C3" in loc.get("cell", "").split(",")
               for loc in direct_locations)
    assert any(loc.get("sheet") == "Sintesi" and loc.get("cell") == "A7" for loc in direct_locations)
    assert {link["source"] for link in links} == {"RF_MATRIX_1", "RF_MATRIX_2"}


def test_test_matrix_parent_id_stays_unresolved_when_only_child_cases_exist():
    matrix = source("RF_ORD_1 | TC_1.1", role="TRACEABILITY",
                    cells=[{"cell": "A1", "value": "RF_ORD_1"}, {"cell": "B1", "value": "TC_1.1"}])
    child = source("TC_1.1_1 A child test case.", role="TCS", page=1)
    child.update(id="doc:child", path="docs/TCS.md", sha256="b" * 64)
    unresolved_model = interpret_sources([matrix, child])
    parent_link = next(link for link in unresolved_model["links"]
                       if link["relation"] == "documented-test-reference")
    assert parent_link["source"] == "RF_ORD_1"
    assert parent_link["target"] == "TC_1.1"
    assert parent_link["target_collection"] == "test_cases"
    assert parent_link["resolved"] is False

    exact = source("TC_1.1 The exact parent test case.\nTC_1.1_1 A child test case.", role="TCS", page=2)
    exact.update(id="doc:exact", path="docs/TCS-exact.md", sha256="c" * 64)
    resolved_model = interpret_sources([matrix, child, exact])
    exact_cases = [case for case in resolved_model["test_cases"] if case["declared_id"] == "TC_1.1"]
    exact_link = next(link for link in resolved_model["links"]
                      if link["relation"] == "documented-test-reference")
    assert exact_link["target"] == exact_cases[0]["id"]
    assert exact_link["resolved"] is True


def test_pdf_table_split_rows_and_precise_location():
    src = source("RF_ORD_1 Clerk shall record order", page=4)
    src["units"][0]["tables"] = [[['ID', 'Description', 'Actor', 'Priority'], ['RF_ORD_1', 'Clerk shall record', 'Clerk', 'High'], ['', 'the order.', '', '']]]
    req = interpret_sources([src])["requirements"][0]
    assert req["statement"] == "Clerk shall record\nthe order."
    assert req["fields"]["actor"] == "Clerk"
    assert req["locations"][0]["page"] == 4
    assert req["locations"][0]["table_row"] == 2


def test_id_collisions_and_unresolved_references_remain_visible():
    a = source("RF_ORD_1 The clerk shall delete an order.", page=1)
    b = source("RF_ORD_1 The clerk shall create an order. UC_ORD_1 Entry: create.", page=2)
    b.update(id="doc:other", path="other/RAD.md", sha256="b"*64)
    ref = source("RF_MISS_9", role="TCS", page=3)
    model = interpret_sources([a, b, ref])
    assert len(model["requirements"]) == 1
    assert len(model["requirements"][0]["declarations"]) == 2
    assert any(i["kind"] == "declaration-variants" for i in model["issues"])
    assert any(not l["resolved"] for l in model["links"])


def test_malformed_and_unsupported_sources_do_not_break_scan(tmp_path):
    root = project(tmp_path)
    (root / "bad.pdf").write_bytes(b"not a pdf")
    (root / "schedule.mpp").write_bytes(b"not supported")
    (root / "bad.xlsx").write_bytes(b"not a zip")
    model = scan_project(root, tmp_path / "scan")["engineering_model"]
    assert len(model["requirements"]) == 2
    states = {s["path"]: s["extraction"] for s in model["sources"]}
    assert states["bad.pdf"] in {"failed", "unsupported"}
    assert states["schedule.mpp"] == "unsupported"
    assert states["bad.xlsx"] == "failed"


def test_missing_optional_pdf_reader_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "pdfplumber", None)
    path = tmp_path / "test.pdf"
    path.write_bytes(b"unused")
    _, status, notes, _ = read_input(path, lambda: None)
    assert status == "unsupported" and "ases[documents]" in notes[0]


def test_generated_documents_preserve_manual_edits(tmp_path):
    from ases.engineering.service import write_documents
    model = scan_project(project(tmp_path), tmp_path / "scan")["engineering_model"]
    folder = tmp_path / "scan/docs"
    original = folder / "ODD.md"
    original.write_text(original.read_text(encoding="utf-8") + "\nMy manual design decision.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="edited"):
        write_documents(model, folder)
    assert "My manual design decision" in original.read_text(encoding="utf-8")


def test_document_quality_keeps_checks_and_manual_judgment_separate(tmp_path):
    root = project(tmp_path)
    (root / "api.py").write_text('class Orders:\n    def add(self, title: str) -> int:\n        """@param missing obsolete argument\n        context Unrelated::add\n        @pre title is present\n        """\n        return 1\n', encoding="utf-8")
    model = scan_project(root, tmp_path / "scan")["engineering_model"]
    checks = {i["kind"]: i for i in model["issues"]}
    assert checks["comment-parameter-not-in-signature"]["parameters"] == ["missing"]
    assert checks["declared-contract-context-review"]["context"] == "Unrelated"
    assert any(c["method"] == "manual" and c["status"] == "review-required" for c in model["quality_controls"])
    # A valid declared precondition is still a declaration, not an invariant/proof.
    method = next(r for r in model["api"] if r["name"] == "add")
    assert method["contracts"][0]["status"] == "declared; not proved"
    assert all(i.get("parameters") != ["title"] for i in model["issues"])


def test_documented_overloads_are_not_matched_arbitrarily(tmp_path):
    root = tmp_path / "library"
    (root / "docs").mkdir(parents=True)
    (root / "Store.java").write_text('public class Store { public int read(String key) { return 1; } public int read(int index) { return 2; } }')
    (root / "docs/Store.html").write_text('<pre>public int read(String other)</pre>')
    model = scan_project(root, tmp_path / "scan")["engineering_model"]
    overloads = [r for r in model["api"] if r["name"] == "read"]
    assert len(overloads) == 2
    assert len({r["id"] for r in overloads}) == 2
    assert all(r["entity_ref"] is None for r in overloads)
    assert not any(i["kind"] == "documented-interface-parameters-review" for i in model["issues"])


def test_invalid_structured_record_does_not_erase_valid_documents(tmp_path):
    root = project(tmp_path)
    (root / "docs").mkdir()
    (root / "docs/requirements.json").write_text(json.dumps({"requirements": [{"id": "RF_BAD_1", "statement": 123}, {"statement": "A sentence without an ID."}, {"id": "RF_BAD_2", "statement": "A valid sentence.", "thresholds": 3}]}))
    model = scan_project(root, tmp_path / "scan")["engineering_model"]
    assert {r["id"] for r in model["requirements"]} == {"RF_ORD_1", "RNF_P_1"}
    assert sum(i["kind"] == "invalid-structured-requirement" for i in model["issues"]) == 3


def test_nested_callable_exception_is_not_parent_api_contract(tmp_path):
    root = tmp_path / "lib"
    root.mkdir()
    (root / "api.py").write_text('def outer():\n    def inner():\n        raise ValueError("inner only")\n    return inner\n')
    model = scan_project(root, tmp_path / "scan")["engineering_model"]
    assert next(r for r in model["api"] if r["name"] == "outer")["errors_observed"] == []


def test_pdf_pages_empty_text_and_cancellation(tmp_path):
    pytest.importorskip("pdfplumber")
    path = tmp_path / "RAD.pdf"
    pdf(path, ["RF_A_1 The reader shall open a book.", ""])
    units, status, notes, meta = read_input(path, lambda: None)
    assert len(units) == meta["pages_total"] == 2
    assert "RF_A_1" in units[0]["text"]
    assert status == "partial" and "no textual layer" in notes[0]
    def cancel():
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        read_input(path, cancel)


def test_encrypted_pdf_is_a_visible_gap_without_losing_other_documents(tmp_path):
    pytest.importorskip("pdfplumber")
    root = project(tmp_path)
    (root / "locked.pdf").write_bytes((Path(__file__).parent / "fixture_documents/encrypted.pdf").read_bytes())
    model = scan_project(root, tmp_path / "scan")["engineering_model"]
    locked = next(s for s in model["sources"] if s["path"] == "locked.pdf")
    assert locked["extraction"] == "failed" and locked["interpretation"] == "not-run"
    assert any("password" in n.lower() for n in locked["limitations"])
    assert len(model["requirements"]) == 2


@pytest.mark.parametrize("dialect,payload", [
    ("html", '<h1>API</h1><script>secret()</script><p>Public call</p>'),
    ("xml", '<testsuite timestamp="2021-01-01" name="old"><testcase name="works"/><testcase name="fails"><failure/></testcase></testsuite>'),
    ("side", '{"tests":[{"name":"open page","commands":[]}]}'),
])
def test_static_formats_are_not_execution(tmp_path, dialect, payload):
    path = tmp_path / ("report." + dialect)
    path.write_text(payload, encoding="utf-8")
    units, status, _, _ = read_input(path, lambda: None)
    assert status == "complete"
    if dialect == "html":
        assert "secret" not in str(units)
    elif dialect == "xml":
        assert [u["test_result"]["status"] for u in units] == ["passed", "failure"]
        assert units[0]["test_result"]["revision"] is None
    else:
        assert "definition" in units[0] and "test_result" not in units[0]


def test_report_copies_are_not_independent_results():
    a, b = source("report", role="TSR"), source("report", role="TSR")
    a["path"], b["path"] = "a.xml", "b.xml"
    for s in (a, b):
        s["units"][0]["test_result"] = {"status": "passed"}
    results = interpret_sources([a, b])["test_results"]
    assert sum(r["independent_evidence"] for r in results) == 1
    assert not any(r["revision_bound"] for r in results)


def test_entities_have_undeclared_types_not_guessed_types(tmp_path):
    root = project(tmp_path)
    (root / "api.ts").write_text('/** @pre key must exist */\nexport class Store {\n public async read(key: string): Promise<number> { return 1; }\n}\nexport function plain(key) { return key; }', encoding="utf-8")
    (root / "Store.java").write_text('package demo;\npublic class Store {\n private int size;\n /** @pre key must exist\n  * @post returns the item\n  */\n public int read(String key) throws Exception { return 1; }\n public int read(int key) { return 1; }\n}\n', encoding="utf-8")
    model = scan_project(root, tmp_path / "scan")["engineering_model"]
    assert next(r for r in model["api"] if r["name"] == "plain")["return_type"] is None
    java = [r for r in model["api"] if r["name"] == "read" and r["language"] == "Java"]
    assert len(java) == 2
    assert java[0]["declared_throws"] == ["Exception"]
    assert java[0]["contracts"][0]["kind"] == "precondition"


def test_reviews_preserve_original_and_conflict_on_change(tmp_path):
    model = scan_project(project(tmp_path), tmp_path / "scan")["engineering_model"]
    req = model["requirements"][0]
    review = {"schema": "ases-engineering-review/1.0", "base_model_digest": model["model_digest"], "operations": [
        {"record_id": req["id"], "expected_digest": req["record_digest"], "action": "confirm", "note": "Checked with the clerk"}]}
    revised = apply_review(model, review)
    assert revised["review_state"]["applied"] == [req["id"]]
    assert "review" not in req
    req["record_digest"] = "changed"
    assert apply_review(model, review)["review_state"]["conflicts"]
    # Restore digest to the saved model via independent load.
    model = load_model(tmp_path / "scan")
    package = regenerate(tmp_path / "scan", tmp_path / "documents", review=review, language="en")
    assert package["review_digest"] == digest(review)
    assert "Checked with the clerk" in (tmp_path / "documents/RAD.md").read_text(encoding="utf-8")
    odd = (tmp_path / "documents/ODD.md").read_text(encoding="utf-8")
    assert "# ODD — Interfaces and object design" in odd
    for heading in ("## Introduction and conventions", "## Packages and modules",
                    "## Interfaces and contracts", "## Class and module diagrams"):
        assert heading in odd
    for heading in ("## Introduzione e convenzioni", "## Package e moduli",
                    "## Interfacce e contratti", "## Diagrammi delle classi e dei moduli"):
        assert heading not in odd
    assert "### Orders.add" in odd
    assert "def add(self, title: str, *, urgent: bool=False) -> int" in odd
    assert "- Source: api.py · line=5 · SHA256 " in odd
    (tmp_path / "documents/RAD.md").write_text("My manually edited RAD", encoding="utf-8")
    with pytest.raises(ValueError, match="edited"):
        regenerate(tmp_path / "scan", tmp_path / "documents")
    assert (tmp_path / "documents/RAD.md").read_text() == "My manually edited RAD"


def test_regeneration_does_not_need_source(tmp_path):
    root = project(tmp_path)
    scan_project(root, tmp_path / "scan")
    root.rename(tmp_path / "source-not-attached")
    package = regenerate(tmp_path / "scan", tmp_path / "package", language="it")
    assert package["parent_snapshot"]
    assert "def add" in (tmp_path / "package/ODD.md").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="separate"):
        regenerate(tmp_path / "scan", tmp_path / "scan")


def test_source_limits_and_xml_entities(tmp_path, monkeypatch):
    from ases.engineering import inputs
    root = project(tmp_path)
    monkeypatch.setattr(inputs, "MAX_FILE", 1)
    sources, coverage = extract_sources(root, {"documentation_artifacts": [{"path": "requirements.yaml"}]})
    assert sources[0]["extraction"] == "partial" and not sources[0]["units"]
    assert coverage["bytes_read"] == 0
    path = tmp_path / "hostile.xml"
    path.write_text('<!DOCTYPE report [<!ENTITY x SYSTEM "file:///secret">]><report>&x;</report>')
    with pytest.raises(ValueError, match="DOCTYPE"):
        read_input(path, lambda: None)


def test_formatting_deltas_are_not_resolution():
    before = {"requirements": [{"id": "RF_A_1", "record_digest": "a"}]}
    after = {"requirements": [{"id": "RF_A_1", "record_digest": "b"}]}
    assert engineering_diff(before, after)["changed"] == ["RF_A_1"]
    result = engineering_diff(before, {})
    assert result["missing"] == ["RF_A_1"] and "not resolved" in result["interpretation"]


def test_jacoco_dtd_is_inert_and_copies_deduplicate(tmp_path):
    path = tmp_path / "jacoco.xml"
    path.write_text('<!DOCTYPE report PUBLIC "-//JACOCO//DTD Report 1.1//EN" "report.dtd"><report name="old"><sessioninfo start="1" dump="2"/><counter type="LINE" missed="3" covered="7"/></report>')
    units, status, _, _ = read_input(path, lambda: None)
    assert status == "complete"
    assert units[0]["counters"] == [{"type": "LINE", "missed": "3", "covered": "7"}]
    assert units[0]["sessions"][0]["start"] == "1"


def test_static_javadoc_read_even_when_classified_generated(tmp_path):
    root = tmp_path / "project"
    (root / "docs/javadoc").mkdir(parents=True)
    (root / "docs/javadoc/Store.html").write_text('<html><h1>Store</h1><pre>public int read(String key)</pre><script>danger()</script></html>')
    model = scan_project(root, tmp_path / "scan")["engineering_model"]
    assert model["sources"] and model["document_api"]
    assert model["document_api"][0]["authority"] == "document-declaration"
    assert model["document_api"][0]["signature"] == "public int read(String key)"
    assert "danger" not in str(model["sources"][0]["units"])


def test_work_log_reference_is_not_requirement():
    src = source("RF_WRONG_6 | 2 | 0 | 2 | 2", role="OTHER", cells=[{"cell":"A1","value":"RF_WRONG_6"}])
    assert not interpret_sources([src])["requirements"]
    src["path"]="worklog.xlsx"
    src["units"][0]["text"]="Development and testing | RF_WRONG_6 | 2 | 0 | 2"
    src["units"][0]["cells"]=[{"cell":"A1","value":"Development and testing"},{"cell":"B1","value":"RF_WRONG_6"}]
    assert not interpret_sources([src])["requirements"]


def test_repeated_use_case_id_is_not_merged():
    src = source("UC_USR_1 Create a user. UC_USR_1 Delete a user.", role="RAD", page=1)
    rows = interpret_sources([src])["scenarios"]
    assert len(rows) == 2
    assert rows[0]["id"] != rows[1]["id"]
    assert rows[0]["declared_id"] == rows[1]["declared_id"]


def test_pdf_table_header_carries_across_pages():
    src = source("RF_USR_1 The user shall register.", page=1)
    src["units"][0]["tables"] = [[['ID','Description','Actor','Priority'], ['RF_USR_1','The user shall register.','User','High']]]
    src["units"].append({"page": 2,"text":"RF_USR_2 The user shall log out.","tables":[[['RF_USR_2','The user shall log out.','User','Low']]]})
    rows = interpret_sources([src])["requirements"]
    assert rows[1]["fields"]["actor"] == "User" and rows[1]["fields"]["priority"] == "Low"


def test_explicit_test_matrix_links_are_navigable():
    src = source("RF_USR_1 | The user shall register. | TC_1.1_1", role="TRACEABILITY", cells=[{"cell":"A1","value":"RF_USR_1"}])
    spec = source("TC_1.1_1 Given a new user, expect a stored account.", role="TCS", page=1)
    spec.update(id="doc:spec",path="docs/TCS.pdf")
    model = interpret_sources([src,spec])
    link = next(l for l in model["links"] if l["relation"] == "documented-test-reference")
    assert link["source"] == "RF_USR_1"
    assert link["target"] == model["test_cases"][0]["id"]
    assert link["target_collection"] == "test_cases"


def test_document_evaluator_reports_field_errors_and_zero_denominators(tmp_path):
    from ases.engineering.evaluate import evaluate_documents
    corpus = {"schema":"ases-document-corpus/1","label_review":"same-session, independent review pending", "cases":[
        {"id":"plain","files":{"api.py":"def greet(name):\n    return name\n"},"requirements":[],
         "fields":[{"select":{"name":"greet"},"field":"return_type","expected":"str"}]}]}
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(corpus))
    report = evaluate_documents(path, tmp_path / "evaluation")
    assert report["requirements"]["recall"] is None
    assert report["fields"] == {"correct":0,"labelled":1}
    assert not report["cases"][0]["passed"]
    assert (tmp_path / "evaluation/document-accuracy.html").is_file()
    corpus["cases"][0]["files"] = {"../outside":"x"}
    path.write_text(json.dumps(corpus))
    with pytest.raises(ValueError, match="Unsafe"):
        evaluate_documents(path, tmp_path / "evaluation")


def test_checklist_is_self_report_and_future_release_is_not_current():
    src = source("RF_SCH: School\nNot included in the first release.\nRF_SCH_1 The school shall plan an event.", page=1)
    check = source("All requirements checked | YES", role="OTHER", sheet="Checklist", row=1, cells=[{"cell":"D1","value":"YES"}])
    check["path"] = "C07_CL_ODD.xlsx"
    model = interpret_sources([src,check])
    assert any(i["kind"]=="checklist-self-report" for i in model["issues"])
    assert model["requirements"][0]["satisfaction"] == "not-verified"
    assert model["requirements"][0]["scope_declarations"][0]["status"].startswith("declared release exclusion")


def test_spreadsheet_results_keep_status_date_and_definition_distinct(tmp_path):
    path = tmp_path / "TIRT.xlsx"
    workbook(path)
    with zipfile.ZipFile(path) as original:
        members = {name: original.read(name) for name in original.namelist() if name != "xl/worksheets/sheet1.xml"}
    with zipfile.ZipFile(path, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
        z.writestr("xl/styles.xml", '<styleSheet><cellXfs><xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>')
        z.writestr("xl/worksheets/sheet1.xml", '<worksheet><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Test Case ID</t></is></c><c r="B1" t="inlineStr"><is><t>Esito</t></is></c><c r="C1" t="inlineStr"><is><t>Data</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>TC_1.1_1</t></is></c><c r="B2" t="inlineStr"><is><t>Not Passed</t></is></c><c r="C2" s="1"><v>43847</v></c></row></sheetData></worksheet>')
    units, _, _, _ = read_input(path, lambda: None)
    result = next(u["test_result"] for u in units if "test_result" in u)
    assert result["name"] == "TC_1.1_1" and result["status"] == "failure"
    assert result["timestamp"].startswith("2020-")
    assert result["revision"] is None
    src = source("", role="TIR");src["units"]=units
    recovered = interpret_sources([src])
    assert recovered["test_results"] and not recovered["test_cases"]


def test_docx_paragraphs_and_tables_are_read_inertly(tmp_path):
    path = tmp_path / "RAD.docx"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", '<w:document xmlns:w="urn:w"><w:body><w:p><w:r><w:t>RF_DOC_1 The user shall read a document.</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Declared table text.</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
    units, status, notes, _ = read_input(path, lambda: None)
    assert status == "complete"
    assert [u["paragraph"] for u in units] == [1,2]
    assert "RF_DOC_1" in units[0]["text"] and "table" in units[1]["text"]
    assert notes


def test_packaged_templates_match_source_and_include_diagram_glossary():
    from importlib.resources import files
    root = Path(__file__).parents[2]
    package = files("ases.engineering").joinpath("resources/templates")
    for path in package.iterdir():
        assert path.read_text(encoding="utf-8") == (root / "templates" / path.name).read_text(encoding="utf-8")
    assert "Class and module diagrams" in package.joinpath("ODD.md").read_text(encoding="utf-8")
