from pathlib import Path
from ases.pipeline import scan_project

def test_benchmark_regressions(tmp_path):
    fixture=Path(__file__).parent/"fixture_benchmark"
    result=scan_project(fixture,tmp_path/"out")
    model=result["semantic_model"]

    # Route normalization: never //login
    names={b["name"] for b in model["behaviors"]}
    assert "POST /login" in names
    assert "GET /logout" in names
    assert all("//" not in n for n in names)

    # Binary project docs are discovered.
    roles={d["role"] for d in model["documentation_artifacts"]}
    assert {"RAD","SDD","ODD","TRACEABILITY"} <= roles

    # Test classes are not production components.
    assert all(c["name"]!="AuthServiceTest" for c in model["components"])

    # DTO/factory/state classifications.
    kinds={c["name"]:c["kind"] for c in model["components"]}
    assert kinds["UserDTO"]=="dto"
    assert kinds["MazzoFactory"]=="factory"
    assert kinds["StartGameState"]=="state_implementation"

    # Client validation layer.
    assert any(c["control_type"]=="validation" and c["enforcement_layer"]=="CLIENT" for c in model["controls"])

    # State candidate and factory idiom candidate remain candidates, not assertions.
    candidates=model["pattern_candidates"]
    assert any("State" in p["candidate_patterns"] for p in candidates)
    assert any("Simple Factory / Factory idiom" in p["candidate_patterns"] for p in candidates)

    # Semantic traceability is smaller than raw fact graph.
    assert len(model["trace_links"]) < len(result["graph"]["edges"])

    # Test must not verify its own test method/class.
    for link in model["trace_links"]:
        if link["relation"]=="verifies":
            assert "AuthServiceTest" not in link["to"]

    # Quality metrics exist.
    q=model["semantic_quality"]
    assert q["schema_status"]=="PASS"
    assert q["raw_fact_edges"] >= q["semantic_trace_links"]
