import hashlib

from ases.engineering.api import recover_api
from ases.engineering.behavior import interpret_behavior, recover_behavior_facts
from ases.scanners.python import scan_python


def analyze(root):
    source = root / "sample.py"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    inventory = {"source_manifest": [{"path": "sample.py", "language": "python", "sha256": digest}]}
    graph = scan_python(root).to_dict()
    api, _ = recover_api(root, graph, inventory)
    facts, _ = recover_behavior_facts(root, inventory, graph)
    records, coverage = interpret_behavior(root, inventory, graph, {"behaviors": []}, api)
    return graph, api, facts, records, coverage


def test_same_named_siblings_keep_exact_lexical_api_identity_and_local_summaries(tmp_path):
    (tmp_path / "sample.py").write_text(
        "def alpha():\n"
        "    def same():\n"
        "        return 'alpha-local'\n"
        "    return 1\n"
        "\n"
        "def beta():\n"
        "    def same():\n"
        "        return 'beta-local'\n"
        "    return 2\n",
        encoding="utf-8",
    )
    graph, api, _, records, _ = analyze(tmp_path)

    nested = [row for row in api if row.get("is_nested")]
    assert len(nested) == 2
    assert {row["qualified_name"] for row in nested} == {"alpha.same", "beta.same"}
    assert all(row["visibility"] == "local-callable" for row in nested)
    assert len({row["entity_ref"] for row in nested}) == 2
    assert all(any(node["id"] == row["entity_ref"] and node["metadata"].get("is_nested")
                   for node in graph["nodes"]) for row in nested)

    locals_by_name = {row["entry_ref"]: row for row in records if row.get("entry_scope") == "lexical-local"}
    assert set(locals_by_name) == {row["entity_ref"] for row in nested}
    assert {row["entry_visibility"] for row in locals_by_name.values()} == {"local-callable"}
    assert {fact["expression"] for row in locals_by_name.values() for fact in row["returns"]} == {"'alpha-local'", "'beta-local'"}
    assert not any(row["name"] == "same" and not row.get("entry_scope") for row in records)


def test_local_summary_does_not_inherit_parent_or_called_outer_body(tmp_path):
    (tmp_path / "sample.py").write_text(
        "def outer_helper(store):\n"
        "    store.save('outer')\n"
        "    return 'outer-result'\n"
        "\n"
        "def parent():\n"
        "    def inner():\n"
        "        outer_helper(None)\n"
        "        return 'inner-result'\n"
        "    return 'parent-result'\n",
        encoding="utf-8",
    )
    graph, api, _, records, _ = analyze(tmp_path)
    inner = next(row for row in api if row.get("qualified_name") == "parent.inner")
    local = next(row for row in records if row.get("entry_scope") == "lexical-local")
    parent = next(row for row in records if row.get("name") == "parent" and not row.get("entry_scope"))

    assert local["entry_ref"] == inner["entity_ref"]
    assert local["entity_refs"] == [inner["entity_ref"]]
    assert not local["effects"]
    assert {fact["expression"] for fact in local["returns"]} == {"'inner-result'"}
    assert {fact["expression"] for fact in parent["returns"]} == {"'parent-result'"}
    assert not parent["effects"]
    outer = next(node for node in graph["nodes"] if node["name"] == "outer_helper")
    assert outer["id"] not in local["entity_refs"]


def test_private_nested_callable_has_internal_own_body_scope(tmp_path):
    (tmp_path / "sample.py").write_text(
        "def public_parent():\n"
        "    def _private_inner():\n"
        "        return 'private'\n"
        "    def __dunder_inner__():\n"
        "        return 'dunder'\n"
        "    return 1\n",
        encoding="utf-8",
    )
    _, api, _, records, coverage = analyze(tmp_path)

    private_api = next(row for row in api if row.get("qualified_name") == "public_parent._private_inner")
    assert private_api["visibility"] == "local-callable"
    assert private_api["is_nested"] is True
    private_record = next(row for row in records if row.get("entry_ref") == private_api["entity_ref"])
    assert private_record["entry_scope"] == "implementation-local"
    assert private_record["entry_visibility"] == "private-convention"
    dunder_api = next(row for row in api if row.get("qualified_name") == "public_parent.__dunder_inner__")
    assert any(row.get("entry_ref") == dunder_api["entity_ref"] for row in records)
    assert private_record["coverage"]["max_call_depth"] == 0


def test_conditional_nested_definition_keeps_context_and_internal_identity(tmp_path):
    (tmp_path / "sample.py").write_text(
        "def parent(flag):\n"
        "    if flag:\n"
        "        def conditional():\n"
        "            return 'inner'\n"
        "    return None\n", encoding="utf-8")
    _, api, _, records, _ = analyze(tmp_path)
    local = next(row for row in api if row.get("qualified_name") == "parent.conditional")
    assert local['conditional_declaration'] is True
    record = next(row for row in records if row.get('entry_ref') == local['entity_ref'])
    assert record['entry_scope'] == 'conditional-local'
    assert record['declaration_context'] == [{'kind':'if','expression':'flag','branch':'then','line':2}]
    assert {x['expression'] for x in record['returns']} == {"'inner'"}


def test_empty_nested_body_is_covered_without_a_fake_summary(tmp_path):
    (tmp_path / "sample.py").write_text(
        "def parent():\n"
        "    def empty():\n"
        "        pass\n"
        "    return 1\n",
        encoding="utf-8",
    )
    _, api, _, records, coverage = analyze(tmp_path)
    empty = next(row for row in api if row.get("qualified_name") == "parent.empty")
    assert not any(row.get("entry_ref") == empty["entity_ref"] for row in records)
    assert any("without admitted body evidence excluded" in row.get("reason", "") for row in coverage)


def test_local_summaries_use_only_the_remaining_entry_budget(tmp_path):
    lines = ["def parent():"]
    for index in range(1002):
        lines.extend((f"    def local_{index}():", f"        return {index}"))
    lines.append("    return 1")
    (tmp_path / "sample.py").write_text("\n".join(lines) + "\n", encoding="utf-8")

    _, _, _, records, coverage = analyze(tmp_path)
    local_records = [row for row in records if row.get("entry_scope") == "lexical-local"]
    assert len(local_records) == 999
    assert len(records) == 1000
    assert any("3 excluded by the 1000-entry budget" in row.get("reason", "") for row in coverage)


def test_explicit_semantic_entry_does_not_get_duplicate_local_summary(tmp_path):
    (tmp_path/'sample.py').write_text('def parent():\n    def inner():\n        return 1\n    return inner\n',encoding='utf-8')
    graph, api, _, _, _ = analyze(tmp_path)
    inner = next(row for row in api if row.get('qualified_name') == 'parent.inner')
    manifest={'source_manifest':[{'path':'sample.py','language':'python','sha256':hashlib.sha256((tmp_path/'sample.py').read_bytes()).hexdigest()}]}
    semantic={'behaviors':[{'id':'route:explicit','name':'GET /example','entry_points':[inner['entity_ref']]}]}
    records, coverage=interpret_behavior(tmp_path,manifest,graph,semantic,api)
    assert len(records)==1 and records[0]['entry_ref']=='route:explicit'
    assert not records[0].get('entry_scope')
    assert any(row.get('entity_ref')==inner['entity_ref'] and row['reason']=='selected: explicit semantic entry point' for row in coverage)


def test_operation_keeps_local_visibility_in_the_reading_view(tmp_path):
    from ases.engineering.operations import build_operations
    (tmp_path/'sample.py').write_text('def parent():\n    def inner():\n        return 1\n    return 2\n',encoding='utf-8')
    _, _, _, records, _=analyze(tmp_path)
    operations,_=build_operations({'recovered_requirements':records})
    assert next(row for row in operations if row['name']=='inner')['entry_scope']=='lexical-local'
    assert not next(row for row in operations if row['name']=='parent').get('entry_scope')
