from __future__ import annotations

def doc_signature(manifest: dict) -> str:
    """Machine-readable header for a regenerable doc: which scan produced it and from which
    project state. A consumer compares `fingerprint` against a fresh manifest to
    decide whether the doc is stale, instead of guessing from a file mtime. Never touched by hand:
    a document a person has edited should have this line removed, which is itself a valid signal
    ("no longer purely regenerable") for any consumer that checks for it.
    """
    return (
        f"<!-- ases:doc fingerprint={manifest.get('project_fingerprint','')} "
        f"ases_version={manifest.get('ases_version','')} -->\n"
    )


def decision_summary(model: dict) -> str:
    """A short reading guide; observations remain separate from review decisions."""
    project = model.get("project", {})
    quality = model.get("semantic_quality", {})
    claims = model.get("claims", [])
    review = [c for c in claims if c.get("status") in {"CONTRADICTED", "OPPORTUNITY"}]
    coverage = quality.get("analysis_coverage", {})
    lines = [
        f"# Evidence summary — {project.get('name', 'project')}", "",
        "> Generated from available evidence. This is a review aid, not an approved design or security verdict.", "",
        "## What was analyzed",
        f"- Entry mode: {project.get('entry_mode', 'UNKNOWN')}",
    ]
    for name, item in coverage.items():
        lines.append(f"- {name}: {item.get('status', 'UNKNOWN')} — {item.get('basis', '')}")
    lines += ["", "## Observed structure"]
    for finding in [*model.get("architecture_patterns", []), *model.get("frontend_findings", [])]:
        if finding.get("status") == "OBSERVED":
            lines.append(f"- {finding.get('pattern')}: {finding.get('reason')} [confidence: {finding.get('confidence')}]" )
    if lines[-1] == "## Observed structure":
        lines.append("- No supported architecture observation in this scan.")
    lines += ["", "## Observed entry-to-boundary paths"]
    paths = model.get("sensitive_paths", [])
    for path in paths[:10]:
        destination = path.get("destination", {})
        lines.append(f"- {path.get('entry_point')} → {destination.get('id')} ({destination.get('kind')}); "
                     f"entry controls observed: {len(path.get('controls_observed_at_entry', []))}")
        lines.append(f"  - Evidence: {', '.join(path.get('evidence', [])[:3])}")
    if len(paths) > 10:
        lines.append(f"- {len(paths) - 10} further paths are available in the semantic model.")
    if not paths:
        lines.append("- No complete path recovered; this does not establish that no data flow exists.")
    lines += ["", "## Requires human review"]
    for claim in review:
        evidence = ", ".join(claim.get("evidence", [])[:3])
        lines.append(f"- {claim.get('subject', claim.get('rule_id', 'Claim'))}: {claim.get('statement', '')} [{claim.get('status')}]" )
        if evidence:
            lines.append(f"  - Evidence: {evidence}")
    if not review:
        lines.append("- No contradicted claim or opportunity surfaced; this does not establish absence of issues.")
    lines += ["", "## Reading limits", "- A valid output checks model consistency, not runtime behavior or security.",
              "- Unknown and not-observed dimensions must not be treated as negative findings."]
    return "\n".join(lines) + "\n"

def _ev(obj):
    p = obj.get("provenance", {})
    ev = ", ".join(p.get("evidence", [])) or "none"
    return f"{p.get('state','UNKNOWN')} / {p.get('confidence','?')} / {ev}"

def system_overview(model: dict, inventory: dict) -> str:
    p = model["project"]
    lines = [
        f"# Recovered System Overview — {p['name']}",
        "",
        "> Generated from repository evidence. It describes the current implementation and does not claim original stakeholder intent.",
        "",
        "## Provenance",
        f"- ASES: {model['ases_version']}",
        f"- Entry mode: {p['entry_mode']}",
        "",
        "## Technology inventory",
    ]
    for l in inventory.get("languages", []):
        lines.append(f"- {l['name']}: {l['files']} source files")
    for b in inventory.get("build_tools", []):
        lines.append(f"- Build: {b['tool']} (`{b['path']}`)")
    for f in p.get("frameworks", []):
        lines.append(f"- Framework: {f}")

    lines += ["", "## Actors"]
    for a in model.get("actors", []):
        lines.append(f"- **{a['name']}** — {_ev(a)}")
    if not model.get("actors"):
        lines.append("- None recovered.")

    lines += ["", "## Observed components"]
    for c in model.get("components", []):
        lines.append(f"- **{c['name']}** ({c['kind']}) — {_ev(c)}")
    frontend = model.get("frontend", {})
    if any(frontend.values()):
        lines += ["", "## Observed frontend"]
        for label, key in (("Components", "components"), ("Templates", "templates"),
                           ("Services", "services"), ("Stores", "stores"),
                           ("Routes", "routes"), ("API calls", "api_calls")):
            if frontend.get(key):
                lines.append(f"- {label}: {len(frontend[key])} observed")

    lines += ["", "## Observed behaviors"]
    if model.get("behaviors"):
        for b in model["behaviors"]:
            flow = " → ".join(b.get("main_flow", []))
            lines.append(f"- **{b['name']}**")
            lines.append(f"  - actor: {b.get('actor')}")
            lines.append(f"  - flow: `{flow}`")
            lines.append(f"  - evidence: `{', '.join(b['provenance']['evidence'])}`")
    else:
        lines.append("- No externally meaningful backend behavior recovered from static evidence.")

    lines += ["", "## Data / assets"]
    for a in model.get("assets", []):
        lines.append(f"- {a['name']} — {_ev(a)}")
    if not model.get("assets"):
        lines.append("- None recovered.")

    lines += ["", "## Trust boundaries"]
    for t in model.get("trust_boundaries", []):
        lines.append(f"- {t['name']} — {_ev(t)}")
    if not model.get("trust_boundaries"):
        lines.append("- None recovered.")

    lines += ["", "## Tests"]
    for t in model.get("tests", []):
        lines.append(f"- {t['name']} — {_ev(t)}")
    if not model.get("tests"):
        lines.append("- No tests recovered.")

    lines += ["", "## Assumptions / unknowns"]
    for u in model.get("assumptions", []) + model.get("unknowns", []):
        lines.append(f"- {u['statement']} [{u['provenance']['state']}]")
    return "\n".join(lines) + "\n"

def recovered_rad(model: dict) -> str:
    lines = [
        f"# Recovered RAD — {model['project']['name']}",
        "",
        "> Recovered requirements describe current observed/inferred behavior, not original stakeholder intent unless explicitly confirmed.",
        "",
        "## Actors",
    ]
    for a in model.get("actors", []):
        lines.append(f"- {a['name']} — {_ev(a)}")
    lines += ["", "## Recovered functional behavior"]
    for b in model.get("behaviors", []):
        lines.append(f"### {b['name']}")
        lines.append(f"- State: {b['provenance']['state']}")
        lines.append(f"- Actor: {b['actor']}")
        lines.append(f"- Trigger: {b['trigger']}")
        lines.append(f"- Main flow: {' → '.join(b.get('main_flow', []))}")
        lines.append(f"- Evidence: {', '.join(b['provenance']['evidence'])}")
        lines.append("")
    lines += ["## Unknown original requirements"]
    for u in model.get("unknowns", []):
        lines.append(f"- {u['statement']}")
    return "\n".join(lines) + "\n"

def recovered_sdd(model: dict) -> str:
    lines = [
        f"# Recovered SDD — {model['project']['name']}",
        "",
        "> Evidence-based reconstruction of the current implementation.",
        "",
        "## Architecture overview",
    ]
    by_kind = {}
    for c in model.get("components", []):
        by_kind.setdefault(c["kind"], []).append(c)
    for kind, items in sorted(by_kind.items()):
        lines.append(f"### {kind.title()}")
        for c in items:
            lines.append(f"- {c['name']} — {_ev(c)}")
    frontend = model.get("frontend", {})
    if any(frontend.values()):
        lines += ["", "## Observed frontend structure"]
        for label, key in (("Components", "components"), ("Templates", "templates"),
                           ("Services", "services"), ("Stores", "stores"), ("Routes", "routes")):
            items = frontend.get(key, [])
            if items:
                lines.append(f"- {label}: {len(items)} observed")
        lines += ["", "### Frontend architecture and conformance"]
        for finding in model.get("frontend_findings", []):
            lines.append(f"- **{finding['pattern']}** — {finding['status']} / {finding['confidence']}: {finding['reason']}")
            lines.append(f"  - Evidence: {', '.join(finding.get('evidence', [])) or 'not available'}")
        if not model.get("frontend_findings"):
            lines.append("- No frontend architecture finding supported by current static evidence.")
    lines += ["", "## Persistence / data"]
    for d in model.get("data_stores", []):
        lines.append(f"- {d['name']} — {_ev(d)}")
    if not model.get("data_stores"):
        lines.append("- UNKNOWN / not recovered.")

    lines += ["", "## Trust boundaries"]
    for t in model.get("trust_boundaries", []):
        lines.append(f"- {t['name']} — {_ev(t)}")
    if not model.get("trust_boundaries"):
        lines.append("- None recovered.")

    lines += ["", "## Conflicts and unknowns"]
    for x in model.get("conflicts", []) + model.get("unknowns", []):
        lines.append(f"- {x.get('statement') or x.get('reason') or x.get('message','')}")
    return "\n".join(lines) + "\n"

def recovered_odd(model: dict, graph: dict) -> str:
    lines = [
        f"# Recovered ODD — {model['project']['name']}",
        "",
        "> Significant implementation objects recovered from code. Pattern names are not asserted without intent evidence.",
        "",
        "## Classes / interfaces / components",
    ]
    relevant = model.get("components", []) + model.get("interfaces", []) + model.get("data_stores", [])
    for c in relevant:
        lines.append(f"### {c['name']}")
        lines.append(f"- Kind: {c['kind']}")
        lines.append(f"- Provenance: {_ev(c)}")
        lines.append("")
    lines += ["", "## Backend and code-level pattern analysis"]
    patterns = model.get("pattern_findings", [])
    visible = [p for p in patterns if p.get("status") != "HINT"]
    if visible:
        for p in visible:
            lines.append(f"- **{p['pattern']}** ({p['category']}) — {p['status']} / {p['confidence']} confidence")
            lines.append(f"  - Rule: `{p.get('rule_id', '')}`")
            lines.append(f"  - Reason: {p['reason']}")
            lines.append(f"  - Evidence: {', '.join(p.get('evidence', []))}")
            if p.get('guidance'):
                lines.append(f"  - Guardrail: {p['guidance']}")
    else:
        lines.append("- No evidence-backed backend or code-level pattern observation or opportunity recovered.")
    if model.get("frontend_findings"):
        lines += ["", "## Frontend architecture and conformance"]
        for finding in model["frontend_findings"]:
            lines.append(f"- **{finding['pattern']}** — {finding['status']} / {finding['confidence']}: {finding['reason']}")
            lines.append(f"  - Evidence: {', '.join(finding.get('evidence', [])) or 'not available'}")
    hints = model.get("pattern_hints", [])
    reviews = [p for p in patterns if p.get('design_review')]
    if reviews:
        lines += ['', '## Design reasoning — hypotheses and existing solutions', '',
                  'Static review only; refactoring benefit, semantic equivalence and change pressure are not established.']
        for p in reviews:
            review = p['design_review']
            lines += ['', f"### {p['pattern']} — {review['verdict']}", f"Evidence: {', '.join(p['evidence'])}"]
            for key, label in [('problem','Problem to verify'),('expected_benefit','Expected benefit'),('existing_solution','Existing solution'),('simpler_alternative','Simplest alternative'),('when_not_to_apply','When to leave it alone'),('questions','Questions before deciding')]:
                lines.append(f"- **{label}:** {review[key]['en']}")
    lines += ["", "## Pattern hints (suppressed from the main scanner feed)"]
    if hints:
        for p in hints:
            lines.append(f"- **{p['pattern']}** ({p['category']}) — low-confidence hint")
            lines.append(f"  - Reason: {p['reason']}")
    else:
        lines.append("- No suppressed pattern hints.")
    lines += [
        "",
        "## Unknown rationale",
        "- Historical design rationale is UNKNOWN unless documented or confirmed.",
    ]
    return "\n".join(lines) + "\n"

def testing_baseline(model: dict) -> str:
    lines = [
        f"# Testing Baseline — {model['project']['name']}",
        "",
        "## Recovered tests",
    ]
    if model.get("tests"):
        for t in model["tests"]:
            lines.append(f"- {t['name']} — {_ev(t)}")
    else:
        lines.append("- None recovered.")
    lines += [
        "",
        "## Coverage interpretation",
        "- Presence of a test is OBSERVED evidence only; semantic coverage is not assumed unless linked explicitly.",
    ]
    return "\n".join(lines) + "\n"


def quality_report(model: dict) -> str:
    q=model.get("semantic_quality",{})
    lines=[
        f"# Semantic Quality — {model['project']['name']}",
        "",
        f"- Schema validation: {q.get('schema_status','UNKNOWN')}",
        f"- Evidence coverage: {q.get('evidence_coverage',{}).get('supported',0)}/{q.get('evidence_coverage',{}).get('total',0)}",
        f"- Route-handler coverage: {q.get('route_handler_coverage',{}).get('covered',0)}/{q.get('route_handler_coverage',{}).get('total',0)}",
        f"- Test-target coverage: {q.get('test_target_coverage',{}).get('linked_tests',0)}/{q.get('test_target_coverage',{}).get('total_tests',0)}",
        f"- Semantic trace links: {q.get('semantic_trace_links',0)}",
        f"- Raw fact edges: {q.get('raw_fact_edges',0)}",
        f"- Trace noise reduction: {q.get('trace_noise_reduction',0)}",
        f"- Unsupported inference count: {q.get('unsupported_inference_count',0)}",
        f"- Documentation artifacts discovered: {q.get('documentation_artifacts_discovered',0)}",
        "",
        "## Control layers",
    ]
    for layer,count in q.get("control_layers",{}).items():
        lines.append(f"- {layer}: {count}")
    return "\n".join(lines)+"\n"
