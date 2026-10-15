"""Evaluate declared scanner claims against a small, explicit local oracle.

This is a rule-quality benchmark, not a claim that all architecture is detectable.
Rules absent from an oracle case are unassessed, rather than negative examples.
"""

from __future__ import annotations


FINDING_GROUPS = ("pattern_findings", "frontend_findings", "cross_boundary_findings")


def evaluate_predictions(observed, oracle: dict, *, complete: bool = False) -> dict:
    """Score labelled claims; close the world only inside an explicit bounded scope."""
    expected, negative, observed = set(oracle["present"]), set(oracle["absent"]), set(observed)
    if expected & negative:
        raise ValueError("The same claim cannot be both present and absent")
    extras = observed - expected - negative
    return {
        "true_positive": sorted(expected & observed),
        "false_negative": sorted(expected - observed),
        "false_positive": sorted((negative & observed) | (extras if complete else set())),
        "true_negative": sorted(negative - observed),
        "unassessed_findings": sorted(set() if complete else extras),
        "unsupported_claims": list(oracle.get("unsupported", [])),
    }


def evaluate_case(model: dict, oracle: dict) -> dict:
    observed = {
        f"{finding['rule_id']}:{finding['status']}"
        for group in FINDING_GROUPS
        for finding in model.get(group, [])
    }
    return evaluate_predictions(observed, oracle)


def summarize(cases: dict[str, dict]) -> dict:
    totals = {
        key: sum(len(case[key]) for case in cases.values())
        for key in ("true_positive", "false_negative", "false_positive", "true_negative")
    }
    tp, fp, fn = totals["true_positive"], totals["false_positive"], totals["false_negative"]
    totals["precision"] = tp / (tp + fp) if tp + fp else None
    totals["recall"] = tp / (tp + fn) if tp + fn else None
    totals["f1"] = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    totals["unassessed"] = sum(len(case.get("unassessed_findings", [])) for case in cases.values())
    totals["assessed_claims"] = tp + fp + fn + totals["true_negative"]
    totals["cases"] = cases
    return totals
