from pathlib import Path

from ases.pipeline import scan_project
from ases.engineering.behavior import python_facts


def scan(tmp_path, files):
    root = tmp_path / "orders"
    root.mkdir()
    for path, text in files.items():
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8")
    return scan_project(root, tmp_path / "scan")["engineering_model"]


def test_reconstructs_sentences_without_any_requirement_labels(tmp_path):
    model = scan(tmp_path, {"app.py":
        'from fastapi import FastAPI\napp = FastAPI()\n'
        'class Store:\n    def save(self, title):\n        return 1\n'
        'store = Store()\n@app.post("/orders")\ndef create_order(title: str):\n'
        '    if not title:\n        raise ValueError("title required")\n'
        '    identifier = store.save(title)\n    return {"id": identifier}\n'})
    assert model["requirements"] == []
    rows = model["recovered_requirements"]
    assert len(rows) == 1
    row = rows[0]
    assert row["name"] == "POST /orders"
    assert "campi «id»" in row["statement_it"]
    assert '«save»' in row['statement_it'] and '«store»' in row['statement_it']
    assert any(f['callee']=='store.save' for f in row['effects'])
    assert "ValueError" in row["statement_it"]
    assert row["authority"] == "static-inference"
    assert row["errors"][0]["conditions"] == ["not title"]
    assert row["external_outcomes"][0]["conditions"] == ["not (not title)"]
    assert row["locations"] and row["test_ideas"]
    assert all(i["status"].startswith("proposed, not executed") for i in row["test_ideas"])
    rad = (tmp_path / "scan/docs/RAD.md").read_text(encoding="utf-8")
    assert row["statement_it"] in rad
    assert "requisiti originali approvati" in rad


def test_internal_helper_results_are_not_presented_as_endpoint_output(tmp_path):
    model = scan(tmp_path, {"app.py":
        'from fastapi import FastAPI\napp = FastAPI()\n'
        'def internal():\n    return {"internal_debug": True}\n'
        '@app.get("/orders")\ndef read_order():\n    internal()\n    return {"id": 7}\n'})
    row = model["recovered_requirements"][0]
    assert "campi «id»" in row["statement_it"]
    assert "internal_debug" not in row["statement_it"]
    assert any("internal_debug" in fact.get("expression", "") for fact in row["facts"])


def test_nested_functions_do_not_add_unexecuted_body_to_parent(tmp_path):
    import ast
    tree = ast.parse('def outer():\n    def never_called():\n        raise RuntimeError("not reached")\n    return 1\n')
    facts = python_facts(tree.body[0])
    assert [f["expression"] for f in facts if f["kind"] == "return"] == ["1"]
    assert not any(f["kind"] == "throw" for f in facts)


def test_branch_alternatives_keep_their_conditions(tmp_path):
    model = scan(tmp_path, {"api.py":'def choose(value):\n    if value is None:\n        return {"error": "missing"}\n    return {"id": value}\n'})
    row = model["recovered_requirements"][0]
    assert "oppure" in row["statement_it"]
    assert {tuple(f["conditions"]) for f in row["external_outcomes"]} == {("value is None",), ("not (value is None)",)}


def test_javascript_callback_behavior_is_interpreted(tmp_path):
    model = scan(tmp_path, {"app.js":
        "const express = require('express');\nconst app=express();\n"
        "app.post('/orders', (req,res)=>{ if(!req.body.title) return res.status(400).json({error:'missing'}); return res.json({id:1}); });\n"})
    rows = model["recovered_requirements"]
    assert rows
    row = next(r for r in rows if r["name"] == "POST /orders")
    assert row["conditions"]
    assert "campi «id»" in row["statement_it"] and "campi «error»" in row["statement_it"]
    assert "oppure" in row["statement_it"]
    assert row["authority"] == "static-inference"


def test_java_handler_to_service_is_interpreted_with_declared_limits(tmp_path):
    fixture = Path(__file__).parent / "fixture_spring"
    model = scan(tmp_path, {p.relative_to(fixture).as_posix(): p.read_text(encoding="utf-8") for p in fixture.rglob("*.java")})
    row = next(r for r in model["recovered_requirements"] if r["name"] == "POST /users")
    assert '«save»' in row['statement_it'] and '«repository»' in row['statement_it']
    assert any("UserService" in ref for ref in row["entity_refs"])
    assert row["coverage"]["status"] == "partial"
    assert 'salvataggio permanente' in row['statement_it'] and 'restano da verificare' in row['statement_it']


def test_name_alone_does_not_prove_persistence(tmp_path):
    model = scan(tmp_path, {"api.py":'def save_order(order):\n    return order\n'})
    row = model["recovered_requirements"][0]
    assert not row["effects"]
    assert "persist" not in row["statement_it"]


def test_arrow_expression_and_arithmetic_are_interpreted(tmp_path):
    model = scan(tmp_path, {"api.ts":"export const double = (value: number): number => value * 2;\n"})
    row = model["recovered_requirements"][0]
    assert row["external_outcomes"][0]["expression"] == "value * 2"
    # A declared numeric type is not proof that runtime operands are numeric.
    assert 'non tradotta' in row['statement_it'] and 'value * 2' not in row['statement_it']


def test_java_comments_and_strings_do_not_create_fake_returns():
    from ases.engineering.behavior import java_facts
    facts = java_facts('{ String s = "return 7;"; /* throw new Danger(); */ return 1; }')
    assert [f["expression"] for f in facts if f["kind"] == "return"] == ["1"]
    assert not any(f["kind"] == "throw" for f in facts)
