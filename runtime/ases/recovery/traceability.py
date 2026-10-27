from __future__ import annotations
import re
from collections import defaultdict
from ..model import FactGraph, Edge

TEST_PATH_MARKERS = ("/test/","/tests/","src/test/","__tests__",".test.",".spec.")

def _is_test_node(n) -> bool:
    low=(n.path or "").lower()
    return n.kind in {"test","test_class"} or n.metadata.get("is_test_code") or any(x in low for x in TEST_PATH_MARKERS)

def enrich_traceability(graph: FactGraph) -> FactGraph:
    """
    Build conservative test→production evidence without linking a test back to
    its own test method/class.
    """
    by_id={n.id:n for n in graph.nodes}
    tests=[n for n in graph.nodes if n.kind=="test"]
    methods, outgoing, production_names = defaultdict(list), defaultdict(list), defaultdict(list)
    nominal_candidates = []
    candidate_kinds = {"method","function","controller","service","repository","entity","class","domain_object","factory","state_implementation"}
    for node in graph.nodes:
        if node.kind == "method":
            methods[(node.path, node.name)].append(node)
        if not _is_test_node(node):
            production_names[node.name].append(node)
            normalized = _norm(node.name)
            if node.kind in candidate_kinds and len(normalized) >= 4:
                nominal_candidates.append((normalized, node))
    for edge in graph.edges:
        outgoing[edge.source].append(edge)

    # Map test-node to matching method in same test file/name, then follow only
    # explicit call/dependency edges into production nodes.
    for t in tests:
        test_methods = methods[(t.path, t.metadata.get("test_method_name", t.name))]
        targets=set()
        nominal = False
        callback = t.metadata.get("test_callable")
        if callback:
            for edge in outgoing[callback]:
                if edge.source == callback and edge.relation == "calls" and edge.target in by_id and not _is_test_node(by_id[edge.target]):
                    targets.add(edge.target)
        for tm in test_methods:
            for e in outgoing[tm.id]:
                if e.source != tm.id:
                    continue
                if e.relation not in {"calls_dependency","calls","calls_method_name","depends_on"}:
                    continue
                target=by_id.get(e.target)
                # unresolved method-name target may still be useful if it clearly
                # refers to a production type.
                if target is not None:
                    if not _is_test_node(target):
                        targets.add(target.id)
                elif e.target.startswith("method-name:"):
                    typename=e.target.split(":",1)[1].split("#",1)[0]
                    prod_types = production_names[typename]
                    if len(prod_types)==1:
                        targets.add(prod_types[0].id)

        # Fallback: unique production symbol named inside test name, but never same file.
        if not targets:
            norm=_norm(t.name)
            matches=[]
            for pn, p in nominal_candidates:
                if p.path != t.path and pn in norm:
                    matches.append(p)
            unique={m.id:m for m in matches}
            if len(unique)==1:
                targets.add(next(iter(unique)))
                nominal = True

        for target in sorted(targets):
            graph.add_edge(Edge(t.id,target,"tests",[t.path] if t.path else [],
                                {"basis": "name-hint" if nominal else "static-call", "test_executed": False}))
    return graph

def semantic_trace_links(graph: FactGraph, behaviors: list[dict], assets: list[dict], controls: list[dict]) -> list[dict]:
    """
    Semantic traceability is deliberately smaller than the raw fact graph.
    It links behaviors/tests/controls/assets to implementation evidence.
    """
    links=[]
    seen=set()
    by_id={n.id:n for n in graph.nodes}

    def add(src,dst,rel,evidence,metadata=None):
        key=(src,dst,rel)
        if key in seen:
            return
        seen.add(key)
        links.append({"from":src,"to":dst,"relation":rel,"evidence":sorted(set(evidence or [])), **(metadata or {})})

    # behavior -> route/handler/meaningful flow nodes
    for b in behaviors:
        bid=b["id"]
        for node_id in b.get("main_flow",[]):
            if node_id.startswith("method-name:"):
                continue
            add(bid,node_id,"implemented_by",b["provenance"].get("evidence",[]))

    # test -> production targets from enriched graph
    for e in graph.edges:
        if e.relation=="tests":
            add(e.source,e.target,"verifies",e.evidence,e.metadata)

    # control -> target
    for e in graph.edges:
        if e.relation in {"protects_or_validates", "protects"}:
            add(e.source,e.target,"enforces_on",e.evidence)

    # session evidence -> target
    for e in graph.edges:
        if e.relation=="session_affects":
            add(e.source,e.target,"session_affects",e.evidence)

    # assets -> entity implementation
    for a in assets:
        target=a["id"].removeprefix("asset:")
        if target in by_id:
            add(a["id"],target,"represented_by",a["provenance"].get("evidence",[]))

    return links

def technical_relation_counts(graph: FactGraph) -> dict[str,int]:
    out=defaultdict(int)
    for e in graph.edges:
        out[e.relation]+=1
    return dict(sorted(out.items()))

def _norm(s):
    return re.sub(r'[^a-z0-9]','',s.lower())
