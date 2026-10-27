"""Bounded document checks. Review signals never certify product correctness."""
from __future__ import annotations

import ast
from collections import defaultdict
import re


def parameter_names(row):
    """Return None when syntax is outside the supported comparison scope."""
    if row.get("language") == "Python":
        try:
            node = ast.parse(row["signature"] + ":\n    pass").body[0]
            args = node.args
            return {a.arg for a in args.posonlyargs + args.args + args.kwonlyargs} | {a.arg for a in (args.vararg, args.kwarg) if a}
        except (SyntaxError, AttributeError):
            return None
    value = row.get("params")
    if not isinstance(value, str) or any(c in value for c in "{}<>[]"):
        return None
    names = set()
    for part in value.strip("() ").split(","):
        part = part.strip()
        if not part:
            continue
        match = re.match(r"^(?:\.\.\.)?([\w$]+)\??\s*(?::|=|$)", part) if row.get("language") != "Java" else re.search(r"([\w$]+)\s*$", part)
        if not match:
            return None
        names.add(match[1])
    return names


def check_documents(model):
    issues = []
    def add(kind, row, meaning, method="heuristic", **extra):
        issues.append({"id": "quality:" + kind + ":" + row["id"], "kind": kind, "method": method,
                       "record_ref": row["id"], "locations": row.get("locations", []), "meaning": meaning, **extra})

    for row in model["requirements"]:
        statement, fields = row["statement"], row["fields"]
        vague = re.findall(r"\b(?:user.friendly|easy to use|efficient|fast|quickly|intuitiv[oa]|facile|veloce|efficiente)\b", statement, re.I)
        if vague:
            add("acceptance-language-review", row, "Qualitative terms need a stated acceptance context; they are not automatically invalid requirements", terms=sorted(set(vague)))
        if not fields.get("oracle"):
            add("acceptance-oracle-not-recovered", row, "No structured acceptance oracle recovered; it may exist in prose, linked tests or unread sources", "deterministic")
        for field in ("actor", "priority"):
            values = sorted({str(d["fields"][field]).strip() for d in row["declarations"] if d["fields"].get(field)})
            if len(values) > 1:
                add(field + "-variants", row, "Different declared values; check versions and vocabulary before calling this a contradiction", values=values)

    unresolved = [link for link in model["links"] if not link.get("resolved", False)]
    if unresolved:
        issues.append({"id": "quality:unresolved-references", "kind": "unresolved-readable-reference", "method": "deterministic",
                       "meaning": "Targets not recovered in this read scope; excluded or unread material can contain them",
                       "occurrences": len(unresolved), "targets": sorted({l["target"] for l in unresolved}),
                       "locations": [loc for link in unresolved[:20] for loc in link.get("locations", [])]})

    by_name = defaultdict(list)
    for row in model["api"]:
        by_name[row["name"]].append(row)
        names = parameter_names(row)
        comment = row.get("responsibility") or ""
        declared = re.findall(r"(?:@param\s+(?:\{[^}]+\}\s*)?|:param\s+)([\w$]+)\b", comment)
        if names is not None and set(declared) - names:
            add("comment-parameter-not-in-signature", row, "Documented parameter names are absent from the recovered signature", "deterministic", parameters=sorted(set(declared) - names))
        for context in re.findall(r"\bcontext\s+([\w.]+)(?:::[\w]+)?", comment, re.I):
            owner = (row.get("owner") or row.get("qualified_name") or row["name"]).split(".")[-1]
            if context.split(".")[-1] != owner:
                add("declared-contract-context-review", row, "Explicit contract context differs from the recovered declaration owner; inspect intended OCL context", context=context, owner=owner)

    # Compare only uniquely attributable simple Javadoc signatures. Overloads,
    # generics and prose are left to review instead of choosing a convenient match.
    for documented in model.get("document_api", []):
        match = re.search(r"\b([\w$]+)\s*\(([^()]*)\)", documented["signature"])
        if not match:
            continue
        candidates = by_name[match[1]]
        owner = documented["locations"][0]["path"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        candidates = [r for r in candidates if (r.get("owner") or "").split(".")[-1] == owner]
        if len(candidates) != 1 or candidates[0].get("language") != "Java":
            continue
        observed = candidates[0]
        doc_names = parameter_names({"language": "Java", "params": match[2]})
        code_names = parameter_names(observed)
        if doc_names is not None and code_names is not None and doc_names != code_names:
            add("documented-interface-parameters-review", documented, "Javadoc and uniquely matched source declaration use different parameter names; version binding is not established", documented_parameters=sorted(doc_names), source_parameters=sorted(code_names), api_ref=observed["id"])

    controls = [
        ("record-identity", "deterministic", "Recovered IDs, readable references, duplicate report hashes and retained source locations"),
        ("declaration-consistency", "heuristic", "Text, actor/priority variants, vague acceptance language and explicit API comment/context comparisons"),
        ("historical-results", "deterministic", "Imported definitions/results, date differences and unresolved test IDs; no current execution or revision proof"),
        ("domain-and-design", "manual", "Validate intent, actors, decision-to-need links, release precedence and architecture trade-offs against stakeholder sources"),
        ("contracts-and-oracles", "manual", "Validate contract meaning, invariants, parameter types, test partitions and pass/fail semantics beyond supported syntax"),
        ("guides-and-diagrams", "manual", "Check imported commands, platform/artifact versions and raster/UML semantics; commands are never executed"),
    ]
    return issues, [{"id": name, "method": method, "scope": scope, "status": "review-required" if method == "manual" else "ran-in-supported-scope"} for name, method, scope in controls]
