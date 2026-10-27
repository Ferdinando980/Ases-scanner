from ases.engineering.inputs import read_input


def extract(tmp_path, body):
    path = tmp_path / "source.html"
    path.write_text(body, encoding="utf-8")
    return read_input(path, lambda: None)[3]


def test_bracketed_generic_uid_paragraph_preserves_normalized_statement_and_line(tmp_path):
    metadata = extract(tmp_path, """<html><body>
<p>[ACME-SRS_53.2] The application <em>shall</em> preserve
   the exact authored statement, punctuation included.</p>
</body></html>""")
    record, = metadata["structured_requirements"]
    assert record["id"] == "ACME-SRS_53.2"
    assert record["statement"] == "The application shall preserve the exact authored statement, punctuation included."
    assert record["kind"] == "unspecified"
    assert record["recognition"] == "explicit-html-paragraph/1"
    assert record["location"] == {"line": 2, "element": "requirement-paragraph"}


def test_requirement_prefixes_and_declared_sections_supply_only_explicit_kinds(tmp_path):
    metadata = extract(tmp_path, """<h2>General requirements</h2>
<p>[RF-7] The application shall retain this functional requirement.</p>
<p>[RNF-8] The service shall respond within two seconds.</p>
<h2>Non-functional requirements</h2>
<p>[SPEC-9] The service must remain available continuously.</p>
<h2>Functional Requirements</h2>
<p>[SPEC-10] The application shall return the requested record.</p>""")
    assert [(r["id"], r["kind"]) for r in metadata["structured_requirements"]] == [
        ("RF-7", "functional"), ("RNF-8", "nonfunctional"),
        ("SPEC-9", "nonfunctional"), ("SPEC-10", "functional")]


def test_bracketed_ids_in_excluded_contexts_tables_and_duplicate_headings_are_not_recovered(tmp_path):
    metadata = extract(tmp_path, """<nav><p>[NAV-1] The app must ignore this navigation sample.</p></nav>
<div class="toc"><p>[TOC-1] The app must ignore this contents entry.</p></div>
<div class="example"><p>[EXAMPLE-1] The app must ignore this example.</p></div>
<pre><p>[PRE-1] The app must ignore this preformatted sample.</p></pre>
<code><p>[CODE-1] The app must ignore this code sample.</p></code>
<script><p>[SCRIPT-1] The app must ignore this script.</p></script>
<style><p>[STYLE-1] The app must ignore this style.</p></style>
<table><tr><td><p>[TABLE-1] The app must not create a duplicate.</p></td></tr></table>
<table><tr data-row-type="REQUIREMENT"><td data-field-name="UID">REQ-12</td>
<td data-field-name="STATEMENT">The system shall retain exactly one record for this UID.</td></tr></table>
<h2 id="REQ-12">Requirement title</h2>
<p>[REQ-12] The system shall retain exactly one record for this UID.</p>""")
    records = metadata.get("structured_requirements", [])
    assert [record["id"] for record in records] == ["REQ-12"]
    assert records[0]["recognition"] == "explicit-html/1"
    assert records[0]["statement"] == "The system shall retain exactly one record for this UID."
