from __future__ import annotations


def build_claims(model: dict) -> list[dict]:
    claims=[]
    for item in [*model.get("pattern_findings",[]), *model.get("conformance_findings",[]), *model.get("frontend_findings",[]), *model.get("cross_boundary_findings",[])]:
        claims.append({
            "id":item.get("id"),
            "fingerprint":item.get("fingerprint", item.get("id")),
            "rule_id":item.get("rule_id"),
            "subject":item.get("pattern") or item.get("subject"),
            "statement":item.get("reason", ""),
            "status":item.get("status"),
            "confidence":item.get("confidence"),
            "evidence":item.get("evidence",[]),
            "counter_evidence":item.get("counter_evidence",[]),
            "assumptions":item.get("assumptions",[]),
        })
    for section, status in (("unknowns","UNKNOWN"),("assumptions","INFERRED")):
        for item in model.get(section,[]):
            p=item.get("provenance",{})
            claims.append({
                "id":item.get("id"),
                "fingerprint":item.get("id"),
                "rule_id":item.get("id"),
                "subject":section[:-1],
                "statement":item.get("statement", ""),
                "status":status,
                "confidence":p.get("confidence"),
                "evidence":p.get("evidence",[]),
                "counter_evidence":[],
                "assumptions":p.get("assumptions",[]),
            })
    return claims
