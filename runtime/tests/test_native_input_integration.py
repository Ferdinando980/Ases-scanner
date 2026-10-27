import json

from ases.engineering.inputs import extract_sources
from ases.scanners.filesystem import scan_filesystem


def test_reqview_and_arff_are_discovered_and_keep_native_record_metadata(tmp_path):
    reqview = {
        "id": "P",
        "documents": [{
            "id": "SRS",
            "attributes": {"type": {"values": [
                {"key": "FR", "label": "Functional Requirement"},
                {"key": "NFR", "label": "Non-functional Requirement"},
                {"key": "REQ", "label": "Requirement"},
                {"key": "CUSTOM_REQ", "label": "Requirement"},
                {"key": "ASVS", "label": "ASVS Requirement"},
            ]}},
            "data": [
                {"id": str(index), "type": kind, "text": f"<p>Requirement {kind}.</p>"}
                for index, kind in enumerate(("FR", "NFR", "REQ", "CUSTOM_REQ", "ASVS"), 1)
            ],
        }],
    }
    (tmp_path / "requirements.reqw").write_text(json.dumps(reqview), encoding="utf-8")
    (tmp_path / "requirements.arff").write_text(
        "@relation q\n@attribute ID string\n@attribute RequirementText string\n@attribute kind {F,NF}\n"
        "@data\n'R-1','The system shall keep this statement.',F\n",
        encoding="utf-8",
    )

    inventory = scan_filesystem(tmp_path)
    sources, _ = extract_sources(tmp_path, inventory)
    by_path = {source["path"]: source for source in sources}

    req_source = by_path["requirements.reqw"]
    assert req_source["extraction"] == "complete"
    records = req_source["metadata"]["structured_requirements"]
    assert [record["source_kind"] for record in records] == ["FR", "NFR", "REQ", "CUSTOM_REQ", "ASVS"]
    assert [record["kind"] for record in records] == ["functional", "nonfunctional", "unspecified", "unspecified", "unspecified"]
    assert records[3]["id"] == "P-SRS-4" and records[3]["location"]["path"] == ["4"]
    assert req_source["units"][3]["location"] == records[3]["location"]

    arff_source = by_path["requirements.arff"]
    assert arff_source["extraction"] == "complete"
    arff_record = arff_source["metadata"]["structured_requirements"][0]
    assert arff_record["id"] == "R-1"
    assert arff_record["location"] == arff_source["units"][0]["location"]
    assert arff_record["attributes"] == {"ID": "R-1", "RequirementText": "The system shall keep this statement.", "kind": "F"}

    formats = {item["path"]: item["format"] for item in inventory["documentation_artifacts"]}
    assert formats["requirements.reqw"] == "reqview"
    assert formats["requirements.arff"] == "arff"
