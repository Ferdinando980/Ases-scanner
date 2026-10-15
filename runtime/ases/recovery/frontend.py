from __future__ import annotations
from collections import defaultdict
import re
from ..model import FactGraph
from ..epistemology import stable_fingerprint, evidence_strength


def recover_frontend_findings(graph: FactGraph) -> list[dict]:
    by_id={n.id:n for n in graph.nodes}
    frontend=[n for n in graph.nodes if not n.metadata.get('is_test_code') and (n.metadata.get('scope')=='frontend' or n.kind.startswith('frontend_'))]
    components=[n for n in frontend if n.kind=='frontend_component']
    templates=[n for n in frontend if n.kind=='frontend_template' and n.metadata.get('framework')!='Angular']
    angular_templates=[n for n in frontend if n.kind=='frontend_template' and n.metadata.get('framework')=='Angular']
    services=[n for n in frontend if n.kind=='frontend_service']
    stores=[n for n in frontend if n.kind=='frontend_store']
    calls=[n for n in frontend if n.kind=='frontend_api_call' and not n.metadata.get('external')]
    out=[]

    if len(components)>=3:
        out.append(_finding('frontend.component_architecture','OBSERVED','high','FRONTEND_ARCHITECTURE','Component-based UI',
            f'{len(components)} owned frontend components were observed.',
            [ev for n in components[:8] for ev in n.provenance.evidence],
            guidance='This records component structure only; component quality and runtime composition are not inferred.'))

    if len(templates)>=3:
        frameworks=sorted({n.metadata.get('framework') for n in templates if n.metadata.get('framework')})
        out.append(_finding('frontend.server_rendered_templates','OBSERVED','high','FRONTEND_ARCHITECTURE','Server-rendered Template UI',
            f'{len(templates)} owned frontend templates were observed' + (f" ({', '.join(frameworks)})." if frameworks else '.'),
            [ev for n in templates[:8] for ev in n.provenance.evidence],
            guidance='Generated documentation HTML and vendored assets are excluded from this count.'))

    if angular_templates:
        out.append(_finding('frontend.angular_component_templates','OBSERVED','high','FRONTEND_ARCHITECTURE','Angular Component Templates',
            f'{len(angular_templates)} Angular component template(s) were observed as frontend source.',
            [ev for n in angular_templates[:8] for ev in n.provenance.evidence],
            guidance='These are client component templates, not server-rendered pages.'))

    if services:
        used={e.target for e in graph.edges if e.relation=='depends_on' and e.target in {n.id for n in services}}
        conf='high' if used else 'medium'
        out.append(_finding('frontend.api_service_layer','OBSERVED',conf,'FRONTEND_APPLICATION_PATTERN','Frontend API Service Layer',
            f'{len(services)} owned frontend API/service module(s) were observed' + (' and referenced by frontend modules.' if used else '.'),
            [ev for n in services for ev in n.provenance.evidence],
            guidance='This does not require every request to pass through a service; conformance is checked separately when enough evidence exists.',
            counter=[] if used else ['No resolved frontend import/dependency to the service modules was observed.']))

    if stores:
        out.append(_finding('frontend.shared_state_store','OBSERVED','medium','FRONTEND_APPLICATION_PATTERN','Shared Frontend State Store',
            f'{len(stores)} owned frontend state/store module(s) were observed.',
            [ev for n in stores for ev in n.provenance.evidence],
            guidance='State ownership and runtime subscription behavior are not dynamically verified.'))

    # If a service layer exists, direct calls from components/pages are architecture erosion, not generic style advice.
    if services:
        direct=[]
        for e in graph.edges:
            if e.relation!='calls_api' or e.source not in by_id or e.target not in by_id: continue
            src,tgt=by_id[e.source],by_id[e.target]
            if src.kind in {'frontend_component','frontend_module'} and tgt.kind=='frontend_api_call' and not tgt.metadata.get('external'):
                direct.append((src,tgt,e))
        if direct:
            evidence=sorted({ev for _,_,e in direct for ev in e.evidence})
            out.append(_finding('frontend.conformance.api_service_bypass','CONTRADICTED','medium','FRONTEND_CONFORMANCE','Frontend API Service Layer',
                f'{len(direct)} direct internal API call(s) originate from frontend component/module code despite an observed frontend API service layer.',
                evidence,
                guidance='Refactor only when the service-layer convention is intentional. Suppress explicit exceptions rather than hiding them.',
                counter=['Some direct calls may be deliberate one-off exceptions.']))

    # If no service layer exists, repeated direct internal calls from multiple modules are only an opportunity.
    if not services and calls:
        owners=defaultdict(set)
        call_nodes={n.id:n for n in calls}
        for e in graph.edges:
            if e.relation=='calls_api' and e.target in call_nodes:
                owners[_normalize_path(call_nodes[e.target].metadata.get('path',''))].add(e.source)
        repeated={p:o for p,o in owners.items() if p and len(o)>=2}
        if repeated:
            evidence=sorted({ev for p in repeated for n in calls if _normalize_path(n.metadata.get('path',''))==p for ev in n.provenance.evidence})
            out.append(_finding('frontend.opportunity.api_service_layer','OPPORTUNITY','medium','FRONTEND_APPLICATION_PATTERN','Frontend API Service Layer',
                f'{len(repeated)} internal endpoint(s) are called directly from multiple frontend modules. A small API/service layer may centralize transport concerns if this duplication keeps growing.',
                evidence,
                guidance='Keep direct calls when they are few and local; add a service layer only when request setup, error handling, auth, or endpoint usage is repeated.'))
    return out


def recover_cross_boundary_findings(graph: FactGraph) -> list[dict]:
    routes=[n for n in graph.nodes if n.kind=='route' and not n.metadata.get('is_test_code')]
    calls=[n for n in graph.nodes if n.kind=='frontend_api_call' and not n.metadata.get('external') and not n.metadata.get('is_test_code')]
    if not routes or not calls: return []
    route_pairs={(n.metadata.get('http_method','ANY').upper(),_normalize_path(n.metadata.get('path',''))):n for n in routes}
    route_paths=defaultdict(set)
    for method,path in route_pairs: route_paths[path].add(method)
    matched=[]; mismatched_method=[]; unknown=[]
    for call in calls:
        method=call.metadata.get('http_method','GET').upper(); path=_normalize_path(call.metadata.get('path',''))
        if not path or '${' in path or '@{' in path: continue
        if (method,path) in route_pairs or ('ANY',path) in route_pairs:
            matched.append(call)
        elif path in route_paths:
            mismatched_method.append((call,sorted(route_paths[path])))
        else:
            unknown.append(call)
    out=[]
    if matched:
        ev=[e for n in matched[:12] for e in n.provenance.evidence]
        out.append(_finding('cross_boundary.route_contract','OBSERVED','high','CROSS_BOUNDARY','Frontend↔Backend Route Contract',
            f'{len(matched)} owned frontend request/form endpoint reference(s) match observed backend routes by method and normalized path.',ev,
            guidance='This is static contract evidence only; payload schemas and runtime responses are not verified.'))
    if mismatched_method:
        ev=[e for n,_ in mismatched_method for e in n.provenance.evidence]
        detail=', '.join(f"{n.metadata.get('http_method')} {n.metadata.get('path')} (backend: {'/'.join(ms)})" for n,ms in mismatched_method[:4])
        out.append(_finding('cross_boundary.http_method_mismatch','CONTRADICTED','high','CROSS_BOUNDARY','Frontend↔Backend HTTP Method',
            f'{len(mismatched_method)} frontend endpoint reference(s) use an HTTP method not exposed for the same backend path: {detail}.',ev,
            guidance='Verify framework routing and template rewriting; if literal method/path evidence is correct, align the frontend request or backend route.'))
    if unknown:
        ev=[e for n in unknown for e in n.provenance.evidence]
        out.append(_finding('cross_boundary.unmatched_route','HINT','low','CROSS_BOUNDARY','Unmatched Frontend Endpoint',
            f'{len(unknown)} internal-looking frontend endpoint reference(s) did not match a statically observed backend route.',ev,
            guidance='Treat this as a hint: routes may be generated, proxied, framework-rewritten, or served externally. Confirm before changing code.',
            counter=['Static route recovery may be incomplete.']))
    return out


def _finding(rule_id,status,confidence,category,subject,reason,evidence,guidance='',counter=None):
    fp=stable_fingerprint(rule_id,subject,evidence)
    return {
        'id':f'finding:{fp}','fingerprint':fp,'rule_id':rule_id,'type':_type(rule_id,status),
        'category':category,'level':category,'pattern':subject,'subject':subject,'status':status,
        'confidence':confidence,'scope':'project','reason':reason,'evidence':evidence,
        'evidence_strength':evidence_strength(evidence),'counter_evidence':counter or [],'assumptions':[],
        'signals':{'positive':[],'negative':counter or []},'guidance':guidance,
        'entity':{'type':'project','id':'project','name':'project'},
    }


def _type(rule_id,status):
    if rule_id.startswith('cross_boundary.'): return 'cross_boundary_contract'
    if status=='CONTRADICTED': return 'architecture_conformance'
    return 'frontend_architecture'


def _normalize_path(path:str)->str:
    if not path: return ''
    path=path.split('?',1)[0].strip()
    if re.match(r'https?://',path,re.I): return ''
    path=re.sub(r'\$\{[^}]+\}|\{[^}]+\}|:[A-Za-z_]\w*','{}',path)
    path=re.sub(r'/+','/',path)
    if not path.startswith('/'): path='/'+path
    return path.rstrip('/') or '/'
