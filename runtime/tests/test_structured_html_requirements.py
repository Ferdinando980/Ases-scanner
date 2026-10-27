from ases.engineering.inputs import read_input


def extract(tmp_path, body):
    path = tmp_path / "source.html"
    path.write_text(body, encoding="utf-8")
    return read_input(path, lambda: None)[3]


def test_explicit_rows_retain_full_statement_and_literal_relations(tmp_path):
    metadata = extract(tmp_path, """<table><tr data-row-type='REQUIREMENT'>
      <td data-field-name='UID'>REQ-004</td><td data-field-name='STATEMENT'>The system shall keep <b>all words</b> after this tail.
      <table><tr><td>nested words</td></tr></table><ul><li>and list text</li></ul></td>
      <td data-field-name='STATUS'>Active</td><td data-field-name='RELATIONS'>
      <a class='requirement__link-parent' href='#REQ-001'>Parent</a>
      <a class='requirement__link-child' href='#REQ-099'>Child</a></td></tr></table>""")
    record, = metadata["structured_requirements"]
    assert record["id"] == "REQ-004" and record["kind"] == "unspecified"
    assert record["statement"].startswith("The system shall keep all words after this tail.")
    assert "nested words" in record["statement"] and "and list text" in record["statement"]
    assert record["status"] == "Active" and record["recognition"] == "explicit-html/1"
    assert record["location"]["line"] > 0
    assert [(r["source"], r["target"], r["native_role"]) for r in metadata["structured_references"]] == [
        ("REQ-004", "REQ-001", "parent"), ("REQ-004", "REQ-099", "child")]


def test_empty_statement_keeps_partial_uid_without_status_promotion(tmp_path):
    metadata = extract(tmp_path, "<table><tr data-row-type='REQUIREMENT'><td data-field-name='UID'>R-7</td><td data-field-name='STATEMENT'> </td><td data-field-name='STATUS'>Active</td></tr></table>")
    record, = metadata["structured_requirements"]
    assert record["id"] == "R-7" and record["statement"] == ""
    assert record["statement_missing"] and record["status"] == "Active" and record["kind"] == "unspecified"


def test_untyped_markup_toc_examples_and_ambiguous_fields_are_not_records(tmp_path):
    metadata = extract(tmp_path, """<style>.x{content:'R-1'}</style><script>R-2 shall be ignored</script>
    <nav><tr data-row-type='TEXT'><td data-field-name='UID'>R-3</td></tr></nav>
    <tr data-row-type='REQUIREMENT'><td data-field-name='UID'>R-4</td><td data-field-name='UID'>R-5</td><td data-field-name='STATEMENT'>shall</td></tr>
    <h2>REQ019 Introduction</h2><p>General overview only.</p><h2>API Reference</h2><p>Any API documentation.</p>""")
    assert "structured_requirements" not in metadata


def test_heading_fallback_requires_authored_obligation_and_stops_at_next_heading(tmp_path):
    metadata = extract(tmp_path, """<h2>REQ019 Introduction</h2><p>General context only.</p>
    <h2>REQ020 Retain records</h2><p>The system shall retain the complete record.</p>
    <p>See children: <a class='requirement__link-child' href='#REQ021'>REQ021</a></p>
    <h2>API Reference</h2><p>Clients must call this API.</p>""")
    record, = metadata["structured_requirements"]
    assert record["id"] == "REQ020" and "complete record" in record["statement"]
    assert "API" not in record["statement"] and all(r["id"] != "REQ019" for r in metadata["structured_requirements"])
    assert [(r["source"], r["target"], r["native_role"]) for r in metadata["structured_references"]] == [("REQ020", "REQ021", "child")]


def test_heading_id_with_indexed_visible_title_and_labeled_literal_child_links(tmp_path):
    metadata = extract(tmp_path, """<nav><a href='#REQ999'>Table of contents</a></nav>
    <h2 id='REQ019'>2.1 Introduction</h2><p>Overview only, no authored obligation.</p>
    <h2 id='REQ021'>2.3 Identifier rules REQ021</h2>
    <p>The system shall preserve the original identifier.</p>
    <p>This includes whitespace and punctuation in every stored record.</p>
    <p><em>Child links:</em> <a href='linked.html#LLT%20001'>LLT001</a></p>
    <h2 id='REQ022'>2.4 Examples</h2><div class='example'><h3 id='REQ999'>Bad API example</h3><p>The client must ignore this sample.</p></div>
    <h2>API reference</h2><p>See <a href='api.html#ROUTE42'>route</a>.</p>""")
    rows = metadata["structured_requirements"]
    assert len(rows) == 1
    row, = rows
    assert row["id"] == "REQ021" and row["title"] == "2.3 Identifier rules"
    assert row["statement"] == "The system shall preserve the original identifier. This includes whitespace and punctuation in every stored record."
    assert metadata["structured_references"] == [{"source": "REQ021", "target": "LLT 001", "native_role": "child",
        "href": "linked.html#LLT%20001", "location": {"line": 6, "element": "heading-requirement"}}]


def test_explicit_statement_retains_code_and_pre_text_without_discovering_fake_rows(tmp_path):
    metadata = extract(tmp_path, """<table><tr data-row-type='REQUIREMENT'>
    <td data-field-name='UID'>REQ-164</td><td data-field-name='STATEMENT'>The system shall preserve <code>literal &lt;tag&gt; example</code>.
    <pre>first line\nsecond line</pre> Tail remains part of this statement.
    <code><tr data-row-type='REQUIREMENT'><td data-field-name='UID'>FAKE-1</td><td data-field-name='STATEMENT'>must not become a requirement</td></tr>
    <h2 id='FAKE-2'>Fake heading</h2></code></td></tr></table>""")
    records = metadata["structured_requirements"]
    assert [r["id"] for r in records] == ["REQ-164"]
    statement = records[0]["statement"]
    assert "literal <tag> example" in statement
    assert "first line second line" in statement and "Tail remains part" in statement
