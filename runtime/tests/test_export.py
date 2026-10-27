import json
from pathlib import Path
import jsonschema
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ases.pipeline import scan_project
from ases.export import export_json, generic_context
from ases.claims import build_claims

def test_export(tmp_path):
    fixture = Path(__file__).parent / "fixture_python"
    out = tmp_path/"scan"
    scan_project(fixture, out)
    target = tmp_path/"consumer.json"
    data = export_json(out, target)
    assert data["schema"] == "ases-consumer-context/1.5"
    assert target.exists()
    assert "behaviors" in data and "controls" in data
    assert "data_stores" in data
    assert "external_systems" in data
    assert data["ases_version"]
    assert data["generated_at"]

def test_export_forwards_manifest_fingerprint(tmp_path):
    fixture = Path(__file__).parent / "fixture_python"
    out = tmp_path/"scan2"
    scan_project(fixture, out)
    manifest = json.loads((out/"manifest.json").read_text())
    target = tmp_path/"consumer2.json"
    data = export_json(out, target, manifest)
    assert data["project_fingerprint"] == manifest["project_fingerprint"]

def test_export_without_manifest_omits_fingerprint(tmp_path):
    fixture = Path(__file__).parent / "fixture_python"
    out = tmp_path/"scan3"
    scan_project(fixture, out)
    target = tmp_path/"consumer3.json"
    data = export_json(out, target)
    assert data["project_fingerprint"] is None

def test_design_review_flows_on_existing_claim_without_changing_identity():
    review={"method":"syntax-responsibilities/2","verdict":"INVESTIGATE","problem":{"it":"p","en":"p"},"expected_benefit":{"it":"b","en":"b"},"existing_solution":{"it":"e","en":"e"},"simpler_alternative":{"it":"s","en":"s"},"when_not_to_apply":{"it":"n","en":"n"},"questions":{"it":"q","en":"q"}}
    finding={"id":"finding-1","fingerprint":"fingerprint-1","rule_id":"review.service_responsibilities","pattern":"Service Layer","reason":"Review this boundary.","status":"HINT","confidence":"medium","evidence":["routes.py:12"],"counter_evidence":[],"assumptions":[],"design_review":review}
    claim=build_claims({"pattern_findings":[finding]})[0]
    assert claim["id"] == finding["id"]
    assert claim["fingerprint"] == finding["fingerprint"]
    assert claim["status"] == finding["status"]
    assert claim["design_review"] == review

def test_design_review_claim_and_coverage_remain_optional():
    finding={"id":"finding-2","rule_id":"review.service_responsibilities","reason":"Review this boundary."}
    claim=build_claims({"pattern_findings":[finding]})[0]
    assert "design_review" not in claim
    plain=generic_context({"project":{},"claims":[]})
    assert "design_review_coverage" not in plain
    covered=generic_context({"project":{},"claims":[],"design_review_coverage":[]})
    assert covered["design_review_coverage"] == []

def test_consumer_context_schema_reuses_scanner_review_contract_and_keeps_legacy_valid():
    root=Path(__file__).parents[2]/"schemas"
    consumer=json.loads((root/"consumer-context.schema.json").read_text(encoding="utf-8"))
    scanner=json.loads((root/"scanner-findings.schema.json").read_text(encoding="utf-8"))
    registry=Registry().with_resource(scanner["$id"],Resource.from_contents(scanner,default_specification=DRAFT202012))
    jsonschema.Draft202012Validator.check_schema(consumer)
    base={"schema":"ases-consumer-context/1.5","project":{},"behaviors":[],"components":[],"trace_links":[],"pattern_findings":[],"claims":[]}
    validator=jsonschema.Draft202012Validator(consumer,registry=registry)
    validator.validate(base)
    review={"method":"syntax-responsibilities/2","verdict":"INVESTIGATE","problem":{"it":"p","en":"p"},"expected_benefit":{"it":"b","en":"b"},"existing_solution":{"it":"e","en":"e"},"simpler_alternative":{"it":"s","en":"s"},"when_not_to_apply":{"it":"n","en":"n"},"questions":{"it":"q","en":"q"}}
    row={"path":"a.py","status":"ANALYZED","reason":"bounded_rules_applied","method":"syntax-responsibilities/2","scope":"admitted"}
    valid={**base,"claims":[{"id":"f1","design_review":review}],"design_review_coverage":[row]}
    validator.validate(valid)
    for malformed in ({**valid,"claims":[{"id":"f1","design_review":{**review,"method":"future/9"}}]},
                      {**valid,"claims":[{"id":"f1","design_review":{**review,"extra":"unrecognized"}}]},
                      {**valid,"design_review_coverage":[{**row,"status":"DONE"}]},
                      {**valid,"design_review_coverage":[{**row,"extra":"unrecognized"}]},
                      {**valid,"design_review_coverage":[row,row]}):
        assert list(validator.iter_errors(malformed))
