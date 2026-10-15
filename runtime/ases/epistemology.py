from __future__ import annotations

from hashlib import sha256
import re

CLAIM_STATES = {
    "OBSERVED", "INFERRED", "OPPORTUNITY", "HINT", "UNKNOWN",
    "CONTRADICTED", "SUPPRESSED",
}

_LINE_SUFFIX = re.compile(r":\d+$")


def evidence_anchor(evidence: list[str]) -> str:
    """Stable semantic anchor: file/entity evidence without volatile line numbers."""
    if not evidence:
        return "project"
    normalized = sorted({_LINE_SUFFIX.sub("", str(x)).replace("\\", "/") for x in evidence})
    return normalized[0]


def stable_fingerprint(rule_id: str, subject: str, evidence: list[str]) -> str:
    payload = f"{rule_id}|{subject}|{evidence_anchor(evidence)}"
    return sha256(payload.encode("utf-8")).hexdigest()[:20]


def evidence_strength(evidence: list[str]) -> str:
    """Small, deterministic quality hint; confidence still belongs to each rule."""
    if not evidence:
        return "none"
    # Multiple independent evidence anchors are stronger than one token/location.
    anchors = {_LINE_SUFFIX.sub("", str(x)) for x in evidence}
    return "strong" if len(anchors) >= 2 else "direct"
