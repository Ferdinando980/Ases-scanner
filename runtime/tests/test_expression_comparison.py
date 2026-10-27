from ases.engineering.claim_evaluation import expression, validate_oracles


def test_typescript_cast_and_crlf_are_normalized_from_selector_path():
    left = "return (value as number) + 1;\r\n"
    right = "return ( value as number ) + 1;\n"
    label = {
        "select": {"entry_path": "src/value.ts"},
        "oracle": "CRLF and spaces around syntax do not change the expression.",
        "closed": ["outcomes"],
        "outcomes": [{"conditions": [], "expression": left, "output_fields": []},
                     {"conditions": [], "expression": right, "output_fields": []}],
    }
    try:
        validate_oracles([label])
    except ValueError as exc:
        assert "Duplicate equivalent" in str(exc)
    else:
        raise AssertionError("TypeScript selector should select the TypeScript expression grammar")


def test_redundant_root_grouping_is_removed_but_nested_precedence_is_preserved():
    assert expression("((left - right))", "typescript") == expression("left - right", "typescript")
    assert expression("left - (right - third)", "typescript") != expression("(left - right) - third", "typescript")


def test_literal_content_and_template_escape_semantics_are_preserved():
    assert expression('"a b"', "typescript") != expression('"ab"', "typescript")
    assert expression("`first\nsecond`", "typescript") != expression(r"`first\nsecond`", "typescript")
    assert expression("/a b/", "typescript") != expression("/ab/", "typescript")


def test_tsx_uses_tsx_grammar():
    assert expression("<div>one two</div>", "tsx") != expression("<div>onetwo</div>", "tsx")
