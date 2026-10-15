"""Conservative, evidence-linked paths from HTTP entries to architectural boundaries."""

from collections import defaultdict, deque
from hashlib import sha256


_LINKS = {"calls", "calls_dependency", "calls_api"}
_TERMINALS = {"repository", "entity", "frontend_api_call", "external_api_call"}


def _is_terminal(node):
    return node.kind in _TERMINALS or (
        node.kind == "interface" and node.metadata.get("java_kind") == "interface"
        and (node.name.lower().endswith("repository") or node.name.lower().endswith("dao"))
    )


def recover_sensitive_paths(graph, coverage=None, max_paths=20, max_depth=9):
    """Return bounded observed call paths; never interpret missing controls as a vulnerability.

    Class-level injection/dependency edges are deliberately not traversed: possession of a
    collaborator is not proof that a particular route calls it. For the same reason an SDK
    import is not an external-data-flow claim.
    """
    nodes = {node.id: node for node in graph.nodes if not node.metadata.get("is_test_code")}
    outgoing = defaultdict(list)
    controls = defaultdict(list)
    methods_by_owner_name = defaultdict(list)
    implementations = defaultdict(list)
    for node in nodes.values():
        if node.kind == "method" and node.metadata.get("owner"):
            methods_by_owner_name[(node.metadata["owner"], node.name)].append(node)
    call_names = defaultdict(set)
    for edge in graph.edges:
        if edge.relation == "calls_method_name" and edge.source in nodes:
            call_names[edge.source].add(edge.target)
        if edge.source not in nodes or edge.target not in nodes:
            continue
        if edge.relation == "implements":
            implementations[edge.target].append(edge)
        if edge.relation in _LINKS:
            outgoing[edge.source].append(edge)
        elif edge.relation in {"protects", "protects_or_validates"} and nodes[edge.source].kind == "control":
            controls[edge.target].append(edge)
    # Scanner call evidence names the receiver type and method separately. Join only
    # unambiguous receiver/method pairs; never turn every injected method into a call.
    resolved_calls = {}
    for source, edges in outgoing.items():
        for edge in edges:
            if edge.relation != "calls_dependency":
                continue
            receiver = nodes[edge.target]
            prefix = f"method-name:{receiver.name}#"
            markers = sorted(marker for marker in call_names[source] if marker.startswith(prefix))
            if len(markers) != 1:
                continue
            method_name = markers[0][len(prefix):]
            direct = methods_by_owner_name[(receiver.id, method_name)]
            if len(direct) == 1:
                resolved_calls[(source, receiver.id)] = ([direct[0].id], [], False)
                continue
            # Interface dispatch is a static hypothesis, never a runtime fact. Resolve only
            # one observed implementation with one matching concrete method.
            if receiver.metadata.get("java_kind") != "interface":
                continue
            impl_edges = implementations[receiver.id]
            if len(impl_edges) != 1:
                continue
            impl = nodes[impl_edges[0].source]
            methods = methods_by_owner_name[(impl.id, method_name)]
            if len(methods) == 1:
                resolved_calls[(source, receiver.id)] = (
                    [impl.id, methods[0].id], impl_edges[0].evidence + methods[0].provenance.evidence, True
                )

    results = []
    for route in sorted((n for n in nodes.values() if n.kind == "route"), key=lambda n: n.id):
        handler_id = route.metadata.get("handler")
        handler = nodes.get(handler_id)
        if handler is None:
            if coverage is not None:
                coverage.append({"entry_point": route.id, "status": "UNKNOWN", "basis": "handler unresolved", "omitted_count": None})
            continue
        observed = sorted(
            (edge for edge in graph.edges if edge.source == route.id
             and edge.target == handler.id and edge.relation == "handled_by"),
            key=lambda edge: edge.target,
        )
        if not observed:
            continue

        queue = deque([(handler.id, [route.id, handler.id], observed[0].evidence, False)])
        terminal_paths = []
        residual = []
        visited = set()
        while queue and len(terminal_paths) < max_paths:
            current, path, evidence, inferred = queue.popleft()
            visited.add(current)
            if len(path) >= max_depth and outgoing[current]:
                residual.append({"node": current, "reason": "depth_limit"})
                continue
            for edge in sorted(outgoing[current], key=lambda e: (e.target, e.relation)):
                if len(terminal_paths) >= max_paths:
                    residual.append({"node": current, "reason": "result_limit"})
                    break
                target = nodes[edge.target]
                if target.id in path or target.kind in {"test", "test_class"}:
                    if target.id in path:
                        residual.append({"node": target.id, "reason": "cycle_not_expanded"})
                    continue
                resolved = resolved_calls.get((current, target.id)) if edge.relation == "calls_dependency" else None
                extra_nodes, extra_evidence, dispatch_inferred = resolved or ([], [], False)
                if edge.relation == "calls_dependency" and not resolved and call_names[current]:
                    residual.append({"node": target.id, "reason": "method_dispatch_unresolved"})
                    continue
                next_path = path + [target.id] + extra_nodes
                next_evidence = evidence + edge.evidence + extra_evidence
                next_inferred = inferred or dispatch_inferred
                if _is_terminal(target):
                    terminal_paths.append((next_path, next_evidence, next_inferred))
                else:
                    queue.append((extra_nodes[-1] if extra_nodes else target.id, next_path, next_evidence, next_inferred))
        if queue:
            residual.append({"node": route.id, "reason": "result_limit"})
        for current in sorted(visited):
            source_path = nodes[current].path
            file_scope = graph.coverage.get(source_path, {})
            if source_path and (file_scope.get("status") != "ANALYZED" or file_scope.get("relationships") != "ANALYZED"):
                residual.append({"node": current, "reason": "extractor_relationship_scope_partial"})
        if coverage is not None:
            coverage.append({"entry_point": route.id, "status": "PARTIAL" if residual else "ANALYZED",
                             "basis": "bounded static calls; runtime and framework-global controls unverified",
                             "limits": {"max_paths": max_paths, "max_depth": max_depth},
                             "residual_unknowns": residual, "omitted_count": None if residual else 0})

        direct_controls = []
        for target_id in (route.id, handler.id):
            for edge in controls[target_id]:
                control = nodes[edge.source]
                direct_controls.append({
                    "id": control.id,
                    "type": control.metadata.get("control_type", "UNKNOWN"),
                    "evidence": sorted(set(control.provenance.evidence + edge.evidence)),
                })
        direct_controls.sort(key=lambda item: item["id"])

        for path, edge_evidence, inferred in terminal_paths:
            terminal = nodes[path[-1]]
            evidence = sorted(set(edge_evidence + route.provenance.evidence + terminal.provenance.evidence))
            fingerprint = sha256("\0".join(path).encode("utf-8")).hexdigest()[:16]
            results.append({
                "id": f"sensitive-path:{fingerprint}",
                "entry_point": route.id,
                "nodes": path,
                "destination": {"id": terminal.id, "kind": "repository" if terminal.kind == "interface" else terminal.kind},
                "controls_observed_at_entry": direct_controls,
                "status": "INFERRED" if inferred else "OBSERVED",
                "confidence": "medium",
                "evidence": evidence,
                "assumptions": ["A unique static interface implementation is treated as the likely dispatch target; runtime wiring is unverified."] if inferred else [],
                "limitations": [
                    "Static call/dependency edges do not prove runtime execution or data sensitivity.",
                    "Controls outside the entry/handler and framework-wide controls are not assessed.",
                    "No observed control is not evidence that protection is absent.",
                ],
            })
    return results
