from __future__ import annotations

from collections import Counter
from ..epistemology import stable_fingerprint, evidence_strength
from ..model import FactGraph


def recover_architecture_conformance(graph: FactGraph, pattern_findings: list[dict]) -> list[dict]:
    """Check only rules implied by architecture that ASES already observed.

    ASES never imposes layering from outside. A violation exists only when the
    project first supplied enough evidence for the corresponding architecture.
    """
    observed = {f.get("pattern") for f in pattern_findings if f.get("status") == "OBSERVED"}
    if "Layered Architecture" not in observed:
        return []

    nodes = {n.id: n for n in graph.nodes if not n.metadata.get("is_test_code")}
    deps = [e for e in graph.edges if e.relation == "depends_on" and e.source in nodes and e.target in nodes]
    violations = []

    forbidden = {
        ("controller", "repository"): "Observed layering routes controllers through services before repositories.",
        ("repository", "controller"): "Persistence components should not depend back on the presentation/controller layer of the observed architecture.",
    }
    grouped: dict[tuple[str, str], list] = {}
    for e in deps:
        pair = (nodes[e.source].kind, nodes[e.target].kind)
        if pair in forbidden:
            grouped.setdefault(pair, []).append(e)

    for (src_kind, dst_kind), edges in grouped.items():
        evidence = sorted({ev for edge in edges for ev in edge.evidence})
        subject = f"{src_kind}->{dst_kind}"
        fingerprint = stable_fingerprint("conformance.layered_dependency", subject, evidence)
        violations.append({
            "id": f"conformance:{fingerprint}",
            "fingerprint": fingerprint,
            "rule_id": "conformance.layered_dependency",
            "type": "architecture_conformance",
            "category": "ARCHITECTURE",
            "subject": subject,
            "status": "CONTRADICTED",
            "confidence": "high",
            "scope": "project",
            "reason": f"{len(edges)} {src_kind}→{dst_kind} dependency edge(s) contradict the observed layered dependency direction.",
            "evidence": evidence,
            "evidence_strength": evidence_strength(evidence),
            "counter_evidence": [forbidden[(src_kind, dst_kind)]],
            "assumptions": ["The Layered Architecture finding remains applicable to these production components."],
            "signals": {
                "positive": [f"Observed Layered Architecture", f"{len(edges)} violating dependency edge(s)"],
                "negative": [],
            },
            "guidance": "Resolve only if the shortcut is accidental. If it is an intentional architectural exception, suppress the rule with an explicit reason rather than hiding the evidence.",
        })
    return violations
