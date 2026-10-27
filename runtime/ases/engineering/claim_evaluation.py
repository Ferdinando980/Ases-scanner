"""Closed, manually labelled local-flow claims, separate from ID recovery."""
from __future__ import annotations

import ast
import json
import re
from functools import lru_cache

CATEGORIES = ("outcomes", "errors", "effects")
EXPRESSION_PROFILE = "syntax-tokens/3"


@lru_cache(maxsize=4096)
def expression(value, source_language="python"):
    value = value.strip().rstrip(";")
    value = re.sub(r"^throw\s+", "", value)
    if source_language == "python":
        try:
            return ast.unparse(ast.parse(value, mode="eval").body)
        except (SyntaxError, RecursionError):
            pass
    if source_language in {"javascript", "typescript", "tsx", "java"}:
        try:
            if source_language == "java":
                from ..scanners.java_syntax import parse
                tree=parse('class AsesValue { Object value() { return '+value+'; } }')
            else:
                from ..scanners.javascript import parse, walk
                suffix = ".tsx" if source_language == "tsx" else ".ts" if source_language == "typescript" else ".js"
                tree=parse('const asesValue = '+value+';', suffix)
            if not tree.has_error:
                if source_language != "java":
                    declaration = next((n for n in walk(tree) if n.type == "variable_declarator"), None)
                    tree = declaration.child_by_field_name("value") if declaration is not None else tree
                    # Drop only redundant grouping around the complete expression.
                    while tree is not None and tree.type == "parenthesized_expression" and len(tree.named_children) == 1:
                        tree = tree.named_children[0]
                tokens=[];pending=[tree]
                while pending:
                    node=pending.pop()
                    if node.type in {"comment","line_comment","block_comment"}:continue
                    raw=node.text.decode('utf-8')
                    if node.type == "template_string":
                        # ECMAScript template TV/TRV normalize physical CR/CRLF
                        # to LF. Escaped backslash sequences remain distinct.
                        raw = raw.replace("\r\n", "\n").replace("\r", "\n")
                    if node.type in {"string","template_string","regex","string_literal","character_literal"}:
                        tokens.append([node.type,raw[1:-1] if node.type in {"string","string_literal","character_literal"} else raw])
                    elif not node.children:tokens.append([node.type,raw])
                    else:pending.extend(reversed(node.children))
                return json.dumps(tokens,ensure_ascii=False)
        except (ValueError, RecursionError):
            pass
    # Unparsed syntax stays exact; never erase literal whitespace or guess precedence.
    return value


def predicate(value, source_language="python"):
    """Predicate-context parentheses/double negation, not program equivalence."""
    from .narrative import predicate as whole_predicate
    # Oracle strings use `not (...)` as explicit logical notation. Structured
    # predicates below disambiguate actual JS functions named `not`.
    grammar = "python" if re.match(r"^not(?:\s|\()", value.strip()) else ("javascript" if source_language in {"typescript", "tsx"} else source_language)
    normalized, negative = whole_predicate(value, grammar)
    return [negative, expression(normalized, source_language)]


def canonical(row, category, source_language="python"):
    if row.get("condition_predicates") is not None:
        from .narrative import predicate as whole_predicate
        values=[]
        for item in row["condition_predicates"]:
            value, negative=whole_predicate(item["expression"],source_language)
            values.append([negative != item["negated"],expression(value,source_language)])
    else:
        values=[predicate(c,source_language) for c in row["conditions"]]
    result = {"conditions": sorted({json.dumps(value, ensure_ascii=False) for value in values})}
    if category == "effects":
        result["callee"] = expression(row["callee"],source_language)
    else:
        result["expression"] = expression(row["expression"],source_language)
        if category == "outcomes":
            result["output_fields"] = sorted(set(row.get("output_fields", [])))
    return json.dumps(result, sort_keys=True, ensure_ascii=False)


def validate_oracles(labels):
    if not isinstance(labels, list) or len(labels) > 100:
        raise ValueError("Behavior oracles must be a bounded list")
    selectors = set()
    for label in labels:
        if not isinstance(label, dict) or not isinstance(label.get("select"), dict) or not label["select"] or not isinstance(label.get("oracle"), str) or not label["oracle"].strip():
            raise ValueError("Behavior oracle needs an explicit selector and rationale")
        closed = label.get("closed")
        if not isinstance(closed, list) or not closed or any(not isinstance(k, str) or k not in CATEGORIES for k in closed) or len(closed) != len(set(closed)):
            raise ValueError("Declare closed behavior categories without duplicates")
        if not all(isinstance(k, str) and k for k in label["select"]):
            raise ValueError("Behavior selector needs named fields")
        selector = json.dumps(label["select"], sort_keys=True)
        if selector in selectors:
            raise ValueError("Duplicate behavior entry selector")
        selectors.add(selector)
        for category in closed:
            rows = label.get(category)
            if not isinstance(rows, list) or len(rows) > 1000:
                raise ValueError("Behavior category needs explicit expected claims, including an empty list")
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get("conditions"), list) or not all(isinstance(c, str) and len(c) <= 4000 for c in row["conditions"]):
                    raise ValueError("Behavior claim needs explicit conditions")
                key = "callee" if category == "effects" else "expression"
                if not isinstance(row.get(key), str) or not row[key] or len(row[key]) > 4000:
                    raise ValueError("Behavior claim needs a bounded expression or callee")
                if category == "outcomes" and (not isinstance(row.get("output_fields"), list) or not all(isinstance(v, str) for v in row["output_fields"])):
                    raise ValueError("Outcome claim needs explicit output fields")
                predicates=row.get("condition_predicates")
                if predicates is not None and (not isinstance(predicates,list) or len(predicates)!=len(row["conditions"]) or any(not isinstance(p,dict) or not isinstance(p.get("expression"),str) or len(p["expression"])>4000 or type(p.get("negated")) is not bool for p in predicates)):
                    raise ValueError("Structured predicates need matching bounded expressions and boolean negations")
                if predicates is not None and any(condition.strip() != ("not ("+p["expression"]+")" if p["negated"] else p["expression"]).strip() for condition,p in zip(row["conditions"],predicates)):
                    raise ValueError("Structured predicate text must match the displayed condition")
            path=str(label["select"].get("entry_path", ""))
            language="java" if path.endswith(".java") else "tsx" if path.endswith(".tsx") else "typescript" if path.endswith((".ts",".mts",".cts")) else "javascript" if path.endswith((".js",".jsx",".mjs",".cjs")) else "python"
            keys = [canonical(row, category, language) for row in rows]
            if len(keys) != len(set(keys)):
                raise ValueError("Duplicate equivalent behavior oracle claims")


def score_claims(model, labels):
    from .evaluate import counts
    result = []
    for label in labels:
        matches = [row for row in model.get("recovered_requirements", []) if all(row.get(k) == value for k, value in label["select"].items())]
        row = matches[0] if len(matches) == 1 else {}
        entries = row.get("entry_points", [])
        if not entries:
            entries = next((b.get("entry_points", []) for b in model.get("structure", {}).get("behaviors", []) if b["id"] == row.get("entry_ref")), [])
            if not entries and str(row.get("entry_ref", "")).startswith("api-behavior:"):
                entries = [row["entry_ref"].removeprefix("api-behavior:")]
        scored, assessed, transitive = {}, {}, {}
        path=str(row.get("entry_path") or label["select"].get("entry_path", ""))
        source_language="java" if path.endswith(".java") else "tsx" if path.endswith(".tsx") else "typescript" if path.endswith((".ts",".mts",".cts")) else "javascript" if path.endswith((".js",".jsx",".mjs",".cjs")) else "python"
        for category in label["closed"]:
            actual = row.get({"outcomes":"external_outcomes", "errors":"errors", "effects":"effects"}[category], [])
            transitive[category] = [fact for fact in actual if fact.get("entity_ref") not in entries]
            actual = [fact for fact in actual if fact.get("entity_ref") in entries]
            assessed[category] = actual
            scored[category] = counts([canonical(fact, category, source_language) for fact in actual], [canonical(fact, category, source_language) for fact in label[category]])
        result.append({"select": label["select"], "oracle": label["oracle"], "predicate_profile":"whole-expression-negation/2", "expression_profile": EXPRESSION_PROFILE, "scope": "selected entry body only; transitive propagation unassessed",
                       "matches": len(matches), "categories": scored, "statement_it": row.get("statement_it"), "statement_en": row.get("statement_en"),
                       "explanation": row.get("explanation"),
                       "narrative_assessment": "Sentences and fact references are inspectable; general readability and domain meaning require separate review.",
                       "expected_claims": {k:label[k] for k in label["closed"]},
                       "actual_claims": assessed, "transitive_claims_outside_oracle": transitive,
                       "passed": len(matches) == 1 and all(not s["FP"] and not s["FN"] for s in scored.values())})
    return result


def summarize(cases):
    keys = ("TP", "FP", "FN", "expected", "predicted")
    summary = {}
    for category in CATEGORIES:
        rows = [label["categories"][category] for case in cases for label in case.get("behaviors", []) if category in label["categories"]]
        values = {k:sum(row[k] for row in rows) for k in keys}
        values.update(precision=values["TP"] / values["predicted"] if values["predicted"] else None,
                      recall=values["TP"] / values["expected"] if values["expected"] else None)
        summary[category] = values
    return {"categories":summary, "labelled_entries":sum(len(c.get("behaviors", [])) for c in cases),
            "meaning":"Selected local-flow claims supporting the sentences. Not general semantic correctness or runtime execution."}
