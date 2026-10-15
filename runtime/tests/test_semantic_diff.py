from ases.semantic_diff import semantic_diff


def test_semantic_diff_ignores_line_moves_but_reports_changed_control():
    before = {"schema": "ases-consumer-context/1.5", "project_fingerprint": "one",
              "controls": [{"id": "control:auth", "name": "authorize", "enforcement_layer": "SERVER",
                            "provenance": {"evidence": ["src/auth.py:10"]}}]}
    moved = {**before, "project_fingerprint": "two",
             "controls": [{**before["controls"][0], "provenance": {"evidence": ["src/auth.py:42"]}}]}
    assert semantic_diff(before, moved)["summary"] == {"added": 0, "removed": 0, "changed": 0}
    changed = {**moved, "controls": [{**moved["controls"][0], "enforcement_layer": "CLIENT"}]}
    report = semantic_diff(before, changed)
    assert report["summary"]["changed"] == 1
    assert report["dimensions"]["controls"]["changed"][0]["after"]["enforcement_layer"] == "CLIENT"


def test_semantic_diff_captures_added_frontend_finding():
    before = {"schema": "ases-consumer-context/1.5"}
    after = {**before, "frontend_findings": [{"id": "f:1", "status": "CONTRADICTED", "pattern": "Frontend API Service Layer"}]}
    report = semantic_diff(before, after)
    assert report["summary"]["added"] == 1
    assert len(report["dimensions"]["frontend_findings"]["added"]) == 1


def test_legacy_route_migration_uses_unique_scope_without_recreating_the_app():
    legacy = {"schema": "ases-consumer-context/1.5", "behaviors": [
        {"id": "behavior:route:GET:/users:server.ts:1", "name": "GET /users", "kind": "route", "provenance": {"evidence": ["server.ts:1"]}}]}
    modern = {"schema": "ases-consumer-context/2.0", "behaviors": [
        {**legacy["behaviors"][0], "id": "behavior:canonical", "provenance": {"evidence": ["server.ts:7"]}}]}
    report = semantic_diff(legacy, modern)
    assert report["summary"] == {"added": 0, "removed": 0, "changed": 0}
    assert report["identity_remappings"][0]["basis"] == "unique-legacy-family-name-source"
    modern["behaviors"].append({**modern["behaviors"][0], "id": "behavior:duplicate"})
    report = semantic_diff(legacy, modern)
    assert report["identity_candidates"] and report["uncertain"]
