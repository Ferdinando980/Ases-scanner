"""Authored HTML fields retain authority, unknown classification and exact references."""
import json

from ases.pipeline import scan_project


def test_html_uid_records_keep_unknown_kind_partial_text_and_scoped_links(tmp_path):
    root = tmp_path / "project"
    docs = root / "docs"
    docs.mkdir(parents=True)
    page = docs / "specification-TABLE.html"
    page.write_text("""<table>
<tr data-row-type="REQUIREMENT"><td data-field-name="UID">Feature-X</td>
<td data-field-name="STATEMENT">The tool shall preserve the original record.</td>
<td data-field-name="TITLE">Preserve a record</td><td data-field-name="STATUS">Active</td>
<td data-field-name="RELATIONS">
<a class="requirement__link-child" href="#Partial-2">Partial-2</a>
<a class="requirement__link-parent" href="#Missing-3">Missing-3</a>
<a class="requirement__link-child" href="https://example.invalid/#Partial-2">External copy</a>
</td></tr>
<tr data-row-type="REQUIREMENT"><td data-field-name="UID">Partial-2</td>
<td data-field-name="STATEMENT"></td><td data-field-name="STATUS">Active</td></tr>
</table>""", encoding="utf-8")
    model = scan_project(root, tmp_path / "scan")["engineering_model"]
    rows = {r["id"]: r for r in model["requirements"]}
    assert set(rows) == {"Feature-X", "Partial-2"}
    assert rows["Feature-X"]["statement"] == "The tool shall preserve the original record."
    assert rows["Feature-X"]["fields"]["title"] == "Preserve a record"
    assert rows["Feature-X"]["fields"]["status"] == "Active"
    assert all(r["kind"] == "unspecified" and r["authority"] == "document-declaration" and r["satisfaction"] == "not-verified" for r in rows.values())
    assert rows["Partial-2"]["statement"] == "" and rows["Partial-2"]["statement_missing"]
    assert any(i["kind"] == "declared-requirement-without-statement" for i in model["issues"])
    assert rows["Feature-X"]["locations"][0]["path"] == "docs/specification-TABLE.html"
    assert rows["Feature-X"]["locations"][0]["line"] > 1
    links = [r for r in model["links"] if r["relation"] == "declared-document-reference"]
    assert len(links) == len({r["id"] for r in links}) == 3
    by_href = {r["href"]: r for r in links}
    assert by_href["#Partial-2"]["resolved"] is True
    assert by_href["#Missing-3"]["resolved"] is False
    assert by_href["https://example.invalid/#Partial-2"]["resolved"] is False
    assert by_href["#Missing-3"]["target"] == "Missing-3"
    assert by_href["#Missing-3"]["native_role"] == "parent"
    assert all(r["target_collection"] == "requirements" for r in links)


def test_html_declared_kind_is_explicit_and_legacy_json_default_is_compatible(tmp_path):
    root = tmp_path / "project"
    docs = root / "docs"
    docs.mkdir(parents=True)
    (docs / "data.html").write_text("""<table><tr data-row-type="REQUIREMENT">
<td data-field-name="UID">Original-ID</td><td data-field-name="STATEMENT">The tool shall read the declared item.</td>
<td data-field-name="KIND">Functional</td></tr></table>""", encoding="utf-8")
    (docs / "requirements.json").write_text(json.dumps({"requirements": [{"id": "Legacy-ID", "statement": "The system shall retain the existing declaration."}]}), encoding="utf-8")
    model = scan_project(root, tmp_path / "scan")["engineering_model"]
    rows = {r["id"]: r for r in model["requirements"]}
    assert rows["Original-ID"]["kind"] == "functional"
    assert rows["Legacy-ID"]["kind"] == "functional"
    assert rows["Original-ID"]["declared_id"] == "Original-ID"
