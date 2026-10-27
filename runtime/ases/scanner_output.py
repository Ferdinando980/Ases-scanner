from __future__ import annotations
from pathlib import Path
from .source_roles import classify_source


def scanner_findings(model: dict) -> dict:
    findings=[]
    hints=[]
    suppressed=[]
    rows=[*model.get("pattern_findings", []), *model.get("conformance_findings", []), *model.get("frontend_findings", []), *model.get("cross_boundary_findings", [])]
    for item in rows:
        row=_row(item)
        status=item.get("status")
        if status=="HINT": hints.append(row)
        elif status=="SUPPRESSED": suppressed.append(row)
        else: findings.append(row)
    return {
        "schema":"ases-scanner-findings/1.3",
        "scanner":{"name":"ASES","version":model.get("ases_version")},
        "project":model.get("project",{}),
        "summary":{
            "findings":len(findings),
            "observed_patterns":sum(x.get("status")=="OBSERVED" and x.get("type")=="design_pattern_observation" for x in findings),
            "pattern_opportunities":sum(x.get("status")=="OPPORTUNITY" for x in findings),
            "architecture_contradictions":sum(x.get("status")=="CONTRADICTED" for x in findings),
            "pattern_hints":len(hints),
            "frontend_findings":sum(x.get("category","").startswith("FRONTEND") for x in findings),
            "cross_boundary_findings":sum(x.get("category")=="CROSS_BOUNDARY" for x in findings),
            "suppressed":len(suppressed),
        },
        "coverage":model.get("semantic_quality",{}).get("analysis_coverage",{}),
        "file_coverage": model.get("file_coverage", {}),
        "analysis_profile": model.get("analysis_profile"),
        "source_classification":model.get("source_classification",{}),
        **({"design_review_coverage":model["design_review_coverage"]} if "design_review_coverage" in model else {}),
        "findings":findings,
        "hints":hints,
        "suppressed":suppressed,
    }


def _row(item: dict) -> dict:
    return {
        "id":item["id"],
        "fingerprint":item.get("fingerprint", item["id"]),
        "type":item.get("type") or _finding_type(item.get("status")),
        "severity":"warning" if item.get("status")=="CONTRADICTED" else "info",
        "status":item.get("status"),
        "category":item.get("category"),
        "level":item.get("level"),
        "pattern":item.get("pattern"),
        "subject":item.get("subject"),
        "confidence":item.get("confidence","low"),
        "scope":item.get("scope","project"),
        "surface":item.get("surface") or _surface(item),
        "actionability":item.get("actionability") or _actionability(item),
        "entity":item.get("entity") or _entity(item),
        "source_role":_source_role(item),
        "rule_id":item.get("rule_id"),
        "smell":item.get("smell"),
        "location":_location(item.get("evidence",[])),
        "evidence":item.get("evidence",[]),
        "evidence_strength":item.get("evidence_strength"),
        "counter_evidence":item.get("counter_evidence",[]),
        "assumptions":item.get("assumptions",[]),
        "signals":item.get("signals",{}),
        "message":item.get("reason",""),
        "guidance":item.get("guidance",""),
        **({"design_review":item["design_review"]} if "design_review" in item else {})
    }


def _finding_type(status: str | None) -> str:
    return {
        "OBSERVED":"design_pattern_observation",
        "INFERRED":"design_pattern_inference",
        "OPPORTUNITY":"design_pattern_opportunity",
        "HINT":"design_pattern_hint",
        "CONTRADICTED":"architecture_conformance",
        "SUPPRESSED":"suppressed_finding",
        "UNKNOWN":"unknown",
    }.get(status,"analysis_finding")


def _location(evidence: list[str]) -> dict | None:
    if not evidence:
        return None
    value=evidence[0]
    path, sep, line=value.rpartition(":")
    if sep and line.isdigit():
        return {"path":path,"line":int(line)}
    return {"path":value}


def _surface(item: dict) -> str:
    cat=item.get("category") or ""
    if cat=="CROSS_BOUNDARY": return "cross_boundary"
    if cat.startswith("FRONTEND"): return "frontend"
    if item.get("scope")=="file": return "backend"
    return "project"

def _actionability(item: dict) -> str:
    status=item.get("status")
    if status=="CONTRADICTED" and item.get("confidence")=="high": return "action_required"
    if status in {"OPPORTUNITY","CONTRADICTED"}: return "review"
    return "informational"


def _entity(item: dict) -> dict:
    loc=_location(item.get("evidence",[]))
    if loc and loc.get("path"):
        path=loc["path"]
        return {"type":"file","id":path,"name":Path(path).name,"path":path}
    return {"type":"project","id":"project","name":"project"}

def _source_role(item: dict) -> str:
    if item.get("source_role"):
        return item["source_role"]
    loc=_location(item.get("evidence",[]))
    if loc and loc.get("path"):
        return classify_source(loc["path"])["role"]
    return "MIXED"
