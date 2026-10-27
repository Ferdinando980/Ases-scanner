import json

import pytest

from ases.engineering.document_formats import read_arff, read_reqview


def reqview_fixture():
    return {
        "id": "PRJ",
        "documents": [{
            "id": "SRS",
            "attributes": {"type": {"name": "Type", "type": "enum", "values": [
                {"key": "FR", "label": "Functional Requirement"},
                {"key": "NFR", "label": "Non-functional Requirement"},
                {"key": "REQ", "label": "Requirement"},
                {"key": "SEC", "label": "Section"},
            ]}},
            "data": [
                {"id": "1", "heading": "Section title", "text": "<p>Group text.</p>", "type": "SEC",
                 "children": [
                    {"id": "2", "type": "FR", "status": "Approved", "priority": "High", "verMethod": "T",
                     "text": "<p>Keep <em>all, punctuation!</em><script>bad()</script> words.&nbsp;Now.</p>",
                     "links": {"satisfaction": ["NEEDS-7"]}},
                    {"id": "3", "type": "REQ", "text": "<p>Explicit but untyped.</p>"},
                    {"id": "4", "type": "NFR", "text": "<p>Latency remains bounded.</p>"},
                    {"id": "5", "type": "STORY", "text": "<p>User story, not automatically requirement.</p>"},
                 ]},
            ],
        }, {
            "id": "NEEDS", "attributes": {"type": {"values": [{"key": "FR", "label": "Requirement"}]}},
            "data": [{"id": "7", "type": "FR", "text": "<p>Need statement.</p>"}],
        }],
        "attachments": {"ignored": "not interpreted"},
        "dashboard": {"script": "ignored"},
    }


def test_reqview_preserves_explicit_requirement_types_native_ids_and_scope():
    units, status, notes, metadata = read_reqview(json.dumps(reqview_fixture()).encode())
    records = [r for r in metadata["structured_requirements"] if r["document_id"] == "SRS"]
    assert status == "complete" and not notes
    assert [r["id"] for r in records] == ["PRJ-SRS-2", "PRJ-SRS-3", "PRJ-SRS-4"]
    assert [r["kind"] for r in records] == ["functional", "unspecified", "nonfunctional"]
    assert records[0]["status"] == "Approved"
    assert records[0]["attributes"] == {"status": "Approved", "priority": "High", "verMethod": "T", "type": "FR"}
    assert records[0]["statement"] == "Keep all, punctuation! words.\u00a0Now."
    assert records[0]["location"]["path"] == ["1", "2"]
    assert "STORY" not in [r["source_kind"] for r in records]
    assert units
    assert metadata["structured_references"] == [{
        "source": "PRJ-SRS-2", "target": "PRJ-NEEDS-7", "native_role": "satisfaction",
        "direction": "source-to-target", "href": None, "location": records[0]["location"]}]


def test_reqview_limits_are_explicitly_partial_and_bad_json_rejected():
    units, status, notes, metadata = read_reqview(json.dumps(reqview_fixture()).encode(), max_records=1)
    assert status == "partial"
    assert any("record limit" in n for n in notes)
    assert len(metadata["structured_requirements"]) == 1
    with pytest.raises(ValueError, match="Malformed ReqView"):
        read_reqview(b"{bad")


def test_arff_supports_quotes_commas_multiline_and_declared_kinds():
    src = b'''@relation synthetic
@attribute ProjectID {1,2}
@attribute ID string
@attribute RequirementText string
@attribute kind {F,NF}
@data
1,'R-1','The system shall accept, preserve, and return "quoted" data.',F
2,'R-2','The system shall show
the exact saved text.',NF
'''
    units, status, notes, metadata = read_arff(src)
    records = metadata["structured_requirements"]
    assert status == "complete" and not notes
    assert records[0]["id"] == "R-1" and records[0]["kind"] == "functional"
    assert records[0]["statement"] == 'The system shall accept, preserve, and return "quoted" data.'
    assert records[1]["kind"] == "nonfunctional"
    assert records[1]["statement"] == "The system shall show\nthe exact saved text."
    assert records[1]["project_id"] == "2"
    assert units[1]["location"]["table_row"] == 2


def test_arff_quality_class_codes_remain_untyped_and_synthetic_keys_stable():
    src = b"""@relation q
@attribute RequirementText string
@attribute class {F,A,L,LF,MN,O,PE,SC,SE,US,FT,PO}
@data
'May include "quoted" words.',PE
'A second statement.',F
"""
    _, status, _, metadata = read_arff(src)
    records = metadata["structured_requirements"]
    assert status == "complete"
    assert records[0]["kind"] == "unspecified" and records[0]["source_kind"] == "PE"
    assert records[0]["id"] == "arff-row-5"
    assert records[0]["identifier_origin"] == "generated-row-key"
    assert records[0]["declared_id"] is None
    assert records[1]["kind"] == "functional"


@pytest.mark.parametrize("source", [
    b"@relation bad\n@attribute Statement string\n@attribute class {F,NF}\n@data\n'broken, F\n",
    b"@relation bad\n@attribute Statement string\n@data\n'one','two'\n",
])
def test_arff_rejects_malformed_rows_without_fabricating_data(source):
    with pytest.raises(ValueError, match="Malformed|Unterminated|has 2 values"):
        read_arff(source)


def test_arff_cp1252_and_limits_are_reported():
    src = "@relation q\n@attribute Statement string\n@data\n'Caf\u00e9 requirement.'\n".encode("cp1252")
    _, status, notes, metadata = read_arff(src, max_text=4)
    assert status == "partial"
    assert "Windows-1252" in notes[0]
    assert metadata["structured_requirements"][0]["statement"] == "Caf\u00e9"
