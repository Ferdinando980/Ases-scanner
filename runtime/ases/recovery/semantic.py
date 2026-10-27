from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import re
from .. import __version__ as ASES_VERSION
from ..model import FactGraph
from .traceability import semantic_trace_links, technical_relation_counts
from ..scanners.filesystem import iter_owned_files
from .patterns import recover_pattern_findings, pattern_views
from .conformance import recover_architecture_conformance
from .frontend import recover_frontend_findings, recover_cross_boundary_findings
from ..suppression import load_suppressions, apply_suppressions
from ..claims import build_claims
from .paths import recover_sensitive_paths

ARCH_KINDS = {
    "application","controller","service","repository","component","configuration",
    "module","class","domain_object","dto","factory","state_implementation"
}
DATA_KINDS = {"entity"}
INTERFACE_KINDS = {"interface"}

def build_semantic_model(project_name: str, inventory: dict, graph: FactGraph, root: Path | None = None) -> dict:
    nodes_by_kind=defaultdict(list)
    by_id={}
    for n in graph.nodes:
        nodes_by_kind[n.kind].append(n)
        by_id[n.id]=n

    # Test code is not production architecture.
    components=[
        _entity(n) for k in ARCH_KINDS for n in nodes_by_kind[k]
        if not n.metadata.get("is_test_code")
    ]
    interfaces=[_entity(n) for k in INTERFACE_KINDS for n in nodes_by_kind[k] if not n.metadata.get("is_test_code")]
    data_stores=[_entity(n) for k in DATA_KINDS for n in nodes_by_kind[k] if not n.metadata.get("is_test_code")]
    tests=[_entity(n) for n in nodes_by_kind["test"]]
    frontend={
        "components":[_entity(n) for n in nodes_by_kind["frontend_component"]],
        "templates":[_entity(n) for n in nodes_by_kind["frontend_template"]],
        "services":[_entity(n) for n in nodes_by_kind["frontend_service"]],
        "stores":[_entity(n) for n in nodes_by_kind["frontend_store"]],
        "api_calls":[{**_entity(n),"http_method":n.metadata.get("http_method"),"path":n.metadata.get("path"),"external":n.metadata.get("external",False)} for n in nodes_by_kind["frontend_api_call"]],
        "routes":[{**_entity(n),"declared_path":n.metadata.get("declared_path"),"framework":n.metadata.get("framework")} for n in nodes_by_kind["frontend_route"]],
    }

    controls=[
        _entity(n) | {
            "control_type":n.metadata.get("control_type"),
            "enforcement_layer":n.metadata.get("enforcement_layer","UNKNOWN"),
            "scope_basis": n.metadata.get("scope_basis", "unknown"),
            "target_refs": sorted(e.target for e in graph.edges if e.source == n.id and e.relation in {"protects", "protects_or_validates"})
        }
        for n in nodes_by_kind["control"] if not n.metadata.get("is_test_code")
    ]
    sessions=[
        _entity(n) | {
            "operation":n.metadata.get("operation"),
            "enforcement_layer":n.metadata.get("enforcement_layer","UNKNOWN")
        }
        for n in nodes_by_kind["session_operation"] if not n.metadata.get("is_test_code")
    ]

    behaviors=[]
    for route in nodes_by_kind["route"]:
        if route.metadata.get("is_test_code"):
            continue
        actor, actor_state, actor_conf, actor_assumptions=infer_actor(route,graph)
        flow_coverage = {}
        main_flow = _flow_for_route(route, graph, flow_coverage)
        behaviors.append({
            "id":f"behavior:{route.id}",
            "name":route.name,
            "kind":"http_behavior",
            "actor":actor,
            "trigger":route.name,
            "entry_points":[route.metadata.get("handler")] if route.metadata.get("handler") else [route.id],
            "preconditions":[],
            "main_flow":main_flow,
            "flow_coverage": flow_coverage,
            "alternatives":[],
            "side_effects":infer_side_effects(route,graph),
            "provenance":{
                "state":route.provenance.state,"confidence":route.provenance.confidence,
                "evidence":route.provenance.evidence,
                "assumptions":actor_assumptions,
            },
            "actor_provenance":{
                "state":actor_state,"confidence":actor_conf,
                "evidence":route.provenance.evidence,
                "assumptions":actor_assumptions,
            }
        })

    assets=recover_assets(graph)
    trace=semantic_trace_links(graph,behaviors,assets,controls)
    pattern_findings=recover_pattern_findings(root, graph, inventory) if root else []
    if root:
        from ..scanners.filesystem import unavailable_sources, source_unavailable
        for missing in unavailable_sources(root):
            source_unavailable(root,root/missing['path'],graph)
    conformance_findings=recover_architecture_conformance(graph, pattern_findings)
    frontend_findings=recover_frontend_findings(graph)
    cross_boundary_findings=recover_cross_boundary_findings(graph)
    suppressions=load_suppressions(root) if root else {}
    for rows in (pattern_findings, conformance_findings, frontend_findings, cross_boundary_findings):
        apply_suppressions(rows, suppressions)
    patterns, pattern_opportunities, pattern_hints=pattern_views(pattern_findings)
    architecture_patterns=[p for p in pattern_findings if p["category"]=="ARCHITECTURAL" and p["status"]=="OBSERVED"]
    trust=recover_trust_boundaries(graph)
    assumptions=recover_assumptions(graph)
    unknowns=recover_unknowns(behaviors)
    quality=semantic_quality(inventory,graph,behaviors,tests,trace,controls)

    path_coverage = []
    sensitive_paths = recover_sensitive_paths(graph, coverage=path_coverage)
    if any(row.get("status") in {"UNKNOWN", "PARTIAL"} for row in graph.coverage.values()):
        for dimension in ("source_structure", "static_behavior", "architecture", "design_patterns", "frontend_backend_contracts"):
            quality["analysis_coverage"][dimension] = {"status": "PARTIAL", "basis": "An extractor reported incomplete syntax; see the public v2 per-file coverage."}
    model = {
        "ases_version":ASES_VERSION,
        "project":{
            "name":project_name,
            "entry_mode":"BROWNFIELD-UNDOCUMENTED",
            "languages":[x["name"] for x in inventory.get("languages",[])],
            "frameworks":infer_frameworks(inventory,graph),
        },
        "evidence_states":["CONFIRMED","OBSERVED","INFERRED","UNKNOWN","CONFLICTING"],
        "claim_states":["OBSERVED","INFERRED","OPPORTUNITY","HINT","UNKNOWN","CONTRADICTED","SUPPRESSED"],
        "documentation_artifacts":inventory.get("documentation_artifacts",[]),
        "source_classification":{
            "roles":inventory.get("source_roles",{}),
            "scopes":inventory.get("source_scopes",{}),
        },
        "actors":_actors_from_behaviors(behaviors),
        "behaviors":behaviors,
        "components":components,
        "interfaces":interfaces,
        "data_stores":data_stores,
        "frontend":frontend,
        "external_systems":recover_external_systems(graph),
        "assets":assets,
        "trust_boundaries":trust,
        "sensitive_paths":sensitive_paths,
        "path_coverage":path_coverage,
        "file_coverage": graph.coverage,
        "analysis_profile": {"ases_version": ASES_VERSION, "parser": inventory.get("parser_profile", {}), "exclusions": inventory.get("exclusions", [])},
        "controls":controls,
        "sessions":sessions,
        "assumptions":assumptions,
        "pattern_findings":pattern_findings,
        "conformance_findings":conformance_findings,
        "frontend_findings":frontend_findings,
        "cross_boundary_findings":cross_boundary_findings,
        "architecture_patterns":architecture_patterns,
        "pattern_candidates":patterns,
        "pattern_opportunities":pattern_opportunities,
        "pattern_hints":pattern_hints,
        "tests":tests,
        "trace_links":trace,
        "technical_relation_counts":technical_relation_counts(graph),
        "semantic_quality":quality,
        "conflicts":[*conformance_findings, *[x for x in frontend_findings+cross_boundary_findings if x.get("status")=="CONTRADICTED"]],
        "unknowns":unknowns,
    }
    model["claims"] = build_claims(model)
    model['design_review_coverage']=inventory.get('design_review_coverage',[])
    return model

def _entity(n):
    return {
        "id":n.id,"name":n.name,"kind":n.kind,"description":"",
        "provenance":{
            "state":n.provenance.state,
            "confidence":n.provenance.confidence,
            "evidence":n.provenance.evidence,
            "assumptions":[]
        }
    }

def infer_frameworks(inventory,graph):
    out=[]
    nodes=[n for n in graph.nodes if not n.metadata.get("is_test_code")]
    build_names={x["tool"] for x in inventory.get("build_tools",[])}
    if ("Maven" in build_names or "Gradle" in build_names) and any(n.kind in {"controller","service","repository","entity","configuration"} for n in nodes):
        out.append("Spring/Spring-like annotations (observed)")
    if any(n.metadata.get("framework")=="NestJS" for n in nodes):
        out.append("NestJS (observed)")
    if any(n.metadata.get("framework")=="Express/Fastify-like" for n in nodes):
        out.append("Express/Fastify-like routing (observed)")
    if any(n.metadata.get("framework")=="Angular" for n in nodes):
        out.append("Angular (observed from frontend source)")
    if any(n.metadata.get("orm")=="Prisma" for n in nodes):
        out.append("Prisma (observed)")
    if any(n.metadata.get("orm")=="Mongoose" for n in nodes):
        out.append("Mongoose (observed)")
    return sorted(set(out))

def infer_actor(route,graph):
    path=(route.metadata.get("path") or "").lower()
    handler=route.metadata.get("handler")
    handler_targets={handler} if handler else set()
    session_ops=[]
    auth_controls=[]
    for e in graph.edges:
        if handler and e.target==handler:
            src=next((n for n in graph.nodes if n.id==e.source),None)
            if src and src.kind=="session_operation":
                session_ops.append(src.metadata.get("operation"))
            if src and src.kind=="control" and src.metadata.get("control_type") in {"authentication","authorization"}:
                auth_controls.append(src.metadata.get("control_type"))

    if "login" in path or "signin" in path:
        return ("Unauthenticated caller","INFERRED","medium",["Route naming suggests an authentication entry point; identity semantics are not confirmed."])
    if "logout" in path or "signout" in path:
        return ("Session-bearing caller","INFERRED","medium",["Logout naming suggests an existing session; authorization semantics are not confirmed."])
    if auth_controls or "session_read" in session_ops:
        return ("Authenticated/session-bearing caller","INFERRED","medium",["Authentication/session evidence is associated with the handler."])
    return ("External caller","INFERRED","medium",["HTTP reachability does not establish authentication or role semantics."])

def _flow_for_route(route,graph,coverage=None):
    flow=[route.id]
    handler=route.metadata.get("handler")
    if not handler:
        if coverage is not None:
            coverage.update({"status": "UNKNOWN", "basis": "handler unresolved", "omitted_count": None})
        return flow
    flow.append(handler)
    frontier=[handler]
    seen=set(flow)
    for _ in range(4):
        nxt=[]
        for current in frontier:
            for e in graph.edges:
                if e.source!=current or e.relation not in {"calls_dependency","calls","calls_api"}:
                    continue
                if e.target.startswith("method-name:"):
                    continue
                if e.target not in seen:
                    seen.add(e.target); flow.append(e.target); nxt.append(e.target)
        frontier=nxt
        if not frontier: break
    if coverage is not None:
        incomplete = any(graph.coverage.get(n.path, {}).get("relationships") != "ANALYZED" for n in graph.nodes if n.id in seen and n.path)
        truncated = any(e.source in frontier and e.relation in {"calls_dependency", "calls", "calls_api"} and e.target not in seen for e in graph.edges)
        coverage.update({"status": "PARTIAL" if incomplete or truncated else "ANALYZED", "basis": "bounded static calls, not architectural dependencies",
                         "max_steps": 4, "truncated": truncated, "omitted_count": None if incomplete or truncated else 0})
    return flow

def infer_side_effects(route,graph):
    effects=[]
    flow=set(_flow_for_route(route,graph))
    for n in graph.nodes:
        if n.kind=="entity":
            if any(e.source in flow and e.target==n.id for e in graph.edges):
                effects.append(f"May access/persist {n.name}")
    return effects

def recover_assets(graph):
    assets=[]
    for n in graph.nodes:
        if n.kind=="entity" and not n.metadata.get("is_test_code"):
            assets.append({
                "id":f"asset:{n.id}","name":n.name,"kind":"data",
                "description":"Persistent/domain data inferred from entity/ORM evidence.",
                "provenance":{
                    "state":"INFERRED","confidence":"medium","evidence":n.provenance.evidence,
                    "assumptions":["Entity/ORM presence suggests data significance, not sensitivity."]
                }
            })
    return assets

def recover_trust_boundaries(graph):
    out=[]
    routes=[n for n in graph.nodes if n.kind=="route" and not n.metadata.get("is_test_code")]
    if routes:
        ev=sorted({p for n in routes for p in n.provenance.evidence})
        out.append({
            "id":"trust-boundary:external-http",
            "name":"External caller → application HTTP boundary",
            "kind":"network_boundary",
            "description":"Observed HTTP entry points imply a boundary between an external caller and application code.",
            "provenance":{"state":"INFERRED","confidence":"high","evidence":ev,"assumptions":["Deployment topology is not inferred."]}
        })
    repos=[n for n in graph.nodes if n.kind=="repository" and not n.metadata.get("is_test_code")]
    entities=[n for n in graph.nodes if n.kind=="entity" and not n.metadata.get("is_test_code")]
    if repos or entities:
        ev=sorted({p for n in repos+entities for p in n.provenance.evidence})
        out.append({
            "id":"trust-boundary:persistence",
            "name":"Application → persistence boundary",
            "kind":"data_boundary",
            "description":"Repository/entity evidence implies a logical persistence boundary; physical deployment separation is unknown.",
            "provenance":{"state":"INFERRED","confidence":"medium","evidence":ev,"assumptions":["Logical boundary does not imply a separate host or trust zone."]}
        })
    return out

# Fixed allowlist of well-known third-party API/service clients, matched as a case-insensitive
# substring against each node's raw import strings (see scanners/{java,typescript,python}.py
# node.metadata["imports"]). Deliberately excludes generic DB drivers (pg, mongodb, JDBC, ...):
# those would overlap with `data_stores` (recovered separately, from `entity` nodes) and mean
# something different — "the app's own database" is not a third party in the sense this list is
# for. Conservative on purpose: an import proves the client/SDK is present in the code, nothing
# about whether it's actually called, which endpoint it hits, or what data it sends.
EXTERNAL_SYSTEM_PROVIDERS = [
    ("OpenAI API", ("openai",)),
    ("Anthropic API", ("anthropic",)),
    ("Stripe", ("stripe",)),
    ("AWS SDK", ("aws-sdk", "boto3", "software.amazon.awssdk", "com.amazonaws")),
    ("Supabase", ("supabase",)),
    ("Twilio", ("twilio",)),
    ("SendGrid", ("sendgrid",)),
    ("Firebase", ("firebase",)),
]

def recover_external_systems(graph):
    matches={}
    usages=defaultdict(list)
    for n in graph.nodes:
        if n.metadata.get("is_test_code"):
            continue
        for imp in n.metadata.get("imports") or []:
            low=str(imp).lower()
            for provider,tokens in EXTERNAL_SYSTEM_PROVIDERS:
                if any(t in low for t in tokens):
                    ev=matches.setdefault(provider,set())
                    ev.update(n.provenance.evidence or ([n.path] if n.path else []))
                    if n.metadata.get("client_call_observed"):
                        usages[provider].append(n.id)
    out=[]
    for provider,ev in sorted(matches.items()):
        out.append({
            "id":f"external-system:{provider.lower().replace(' ','-')}",
            "name":provider,
            "kind":"third_party_api",
            "description":f"A known {provider} client/SDK import was observed in the code.",
            "usage_basis": "static-client-call" if usages[provider] else "import-candidate",
            "call_refs": sorted(usages[provider]),
            "provenance":{
                "state":"INFERRED","confidence":"medium","evidence":sorted(ev),
                "assumptions":["Static client calls are recovered; execution, endpoint, contract terms and data sent remain unverified." if usages[provider] else "Endpoint, contract terms, and data sent are not inferred — only that the client/SDK is imported."]
            }
        })
    return out

def recover_assumptions(graph):
    out=[]
    route_files=sorted({n.path for n in graph.nodes if n.kind=="route" and n.path and not n.metadata.get("is_test_code")})
    if route_files:
        out.append({
            "id":"assumption:http-actor-identity",
            "statement":"Static route recovery alone cannot determine caller identity or role.",
            "provenance":{"state":"UNKNOWN","confidence":"high","evidence":route_files,"assumptions":[]}
        })

    client_validation=[n for n in graph.nodes if n.kind=="control" and not n.metadata.get("is_test_code") and n.metadata.get("control_type")=="validation" and n.metadata.get("enforcement_layer")=="CLIENT"]
    server_validation=[n for n in graph.nodes if n.kind=="control" and not n.metadata.get("is_test_code") and n.metadata.get("control_type")=="validation" and n.metadata.get("enforcement_layer")=="SERVER"]
    if client_validation and not server_validation:
        out.append({
            "id":"assumption:client-only-validation",
            "statement":"Validation evidence was recovered on the client side, while no server-side validation evidence was recovered by this scanner.",
            "provenance":{
                "state":"INFERRED","confidence":"medium",
                "evidence":sorted({p for n in client_validation for p in n.provenance.evidence}),
                "assumptions":["Absence of recovered server validation is not proof that no server validation exists."]
            }
        })
    return out

def recover_unknowns(behaviors):
    out=[{
        "id":"unknown:stakeholder-intent",
        "statement":"Original stakeholder intent is not recoverable from code alone.",
        "provenance":{"state":"UNKNOWN","confidence":"high","evidence":[],"assumptions":[]}
    }]
    if any(b["actor"]=="External caller" for b in behaviors):
        out.append({
            "id":"unknown:actors",
            "statement":"One or more route actors cannot be determined reliably from static repository evidence.",
            "provenance":{"state":"UNKNOWN","confidence":"high","evidence":[],"assumptions":[]}
        })
    return out

def semantic_quality(inventory,graph,behaviors,tests,trace,controls):
    evidence_items=[]
    for n in graph.nodes:
        if n.kind in {"route","controller","service","repository","entity","control","session_operation","test"}:
            evidence_items.append(n)
    evidence_supported=sum(1 for n in evidence_items if n.provenance.evidence)
    route_handlers=sum(1 for b in behaviors if len(b.get("main_flow",[]))>=2)
    tested_ids={x["from"] for x in trace if x["relation"]=="verifies"}
    unsupported_inferences=0

    return {
        "schema_status":"PENDING_PIPELINE_VALIDATION",
        "evidence_coverage":{
            "supported":evidence_supported,
            "total":len(evidence_items),
            "ratio":round(evidence_supported/len(evidence_items),4) if evidence_items else 1.0,
        },
        "route_handler_coverage":{
            "covered":route_handlers,
            "total":len(behaviors),
            "ratio":round(route_handlers/len(behaviors),4) if behaviors else 1.0,
        },
        "test_target_coverage":{
            "linked_tests":len(tested_ids),
            "total_tests":len(tests),
            "ratio":round(len(tested_ids)/len(tests),4) if tests else 1.0,
        },
        "semantic_trace_links":len(trace),
        "raw_fact_edges":len(graph.edges),
        "trace_noise_reduction":round(1-(len(trace)/len(graph.edges)),4) if graph.edges else 0.0,
        "unsupported_inference_count":unsupported_inferences,
        "documentation_artifacts_discovered":len(inventory.get("documentation_artifacts",[])),
        "control_layers":{
            "CLIENT":sum(1 for c in controls if c.get("enforcement_layer")=="CLIENT"),
            "SERVER":sum(1 for c in controls if c.get("enforcement_layer")=="SERVER"),
            "UNKNOWN":sum(1 for c in controls if c.get("enforcement_layer")=="UNKNOWN"),
        },
        "analysis_coverage":{
            "source_structure":{"status":"ANALYZED","basis":"owned source files and static dependency graph"},
            "static_behavior":{"status":"ANALYZED","basis":"routes, call/dependency edges, controls and sessions"},
            "architecture":{"status":"ANALYZED","basis":"production component kinds and dependency graph"},
            "design_patterns":{"status":"ANALYZED","basis":"precision-first static rules; absence is not proof of absence"},
            "frontend_structure":{"status":"ANALYZED","basis":"owned frontend components/templates/modules only; generated and vendored assets excluded"},
            "frontend_backend_contracts":{"status":"ANALYZED","basis":"literal owned frontend endpoint references matched against statically observed backend routes"},
            "runtime_behavior":{"status":"NOT_OBSERVED","basis":"no dynamic execution or production telemetry"},
            "deployment_topology":{"status":"UNKNOWN","basis":"repository evidence alone is insufficient"},
            "external_system_behavior":{"status":"UNKNOWN","basis":"external services are not executed"},
        }
    }

def _actors_from_behaviors(behaviors):
    seen={}
    for b in behaviors:
        name=b["actor"]
        if name not in seen:
            seen[name]={
                "id":f"actor:{name.lower().replace(' ','-').replace('/','-')}",
                "name":name,"kind":"actor",
                "description":"Recovered from externally reachable behavior.",
                "provenance":b["actor_provenance"]
            }
    return list(seen.values())
