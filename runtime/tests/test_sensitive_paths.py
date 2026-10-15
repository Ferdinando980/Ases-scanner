from ases.model import Edge, Evidence, FactGraph, Node
from ases.recovery.paths import recover_sensitive_paths


def _node(id, kind, **metadata):
    return Node(id, kind, id, "app.py", metadata, Evidence(evidence=["app.py:1"]))


def test_observed_route_to_repository_path_with_entry_control():
    graph = FactGraph(
        nodes=[
            _node("route", "route", handler="handler"),
            _node("handler", "method"),
            _node("service", "service"),
            _node("repository", "repository"),
            _node("auth", "control", control_type="authorization"),
        ],
        edges=[
            Edge("route", "handler", "handled_by", ["app.py:2"]),
            Edge("handler", "service", "calls_dependency", ["app.py:3"]),
            Edge("service", "repository", "calls", ["app.py:4"]),
            Edge("auth", "handler", "protects", ["app.py:2"]),
        ],
    )
    paths = recover_sensitive_paths(graph)
    assert len(paths) == 1
    assert paths[0]["nodes"] == ["route", "handler", "service", "repository"]
    assert paths[0]["controls_observed_at_entry"][0]["type"] == "authorization"
    assert "app.py:4" in paths[0]["evidence"]


def test_injection_or_import_alone_is_not_a_call_path():
    graph = FactGraph(
        nodes=[
            _node("route", "route", handler="handler"),
            _node("handler", "method"),
            _node("controller", "controller", imports=["stripe"]),
            _node("repository", "repository"),
        ],
        edges=[
            Edge("route", "handler", "handled_by", ["app.py:2"]),
            Edge("controller", "repository", "depends_on", ["app.py:3"]),
        ],
    )
    assert recover_sensitive_paths(graph) == []


def test_missing_handler_or_unproven_route_link_is_not_reported():
    graph = FactGraph(nodes=[_node("route", "route", handler="handler"), _node("handler", "method")])
    assert recover_sensitive_paths(graph) == []


def test_resolves_only_called_service_method():
    graph = FactGraph(
        nodes=[
            _node("route", "route", handler="handler"),
            _node("handler", "method"),
            _node("service", "service"),
            _node("called", "method", owner="service"),
            _node("other", "method", owner="service"),
            _node("repository", "repository"),
        ],
        edges=[
            Edge("route", "handler", "handled_by", ["app.py:1"]),
            Edge("handler", "service", "calls_dependency", ["app.py:2"]),
            Edge("handler", "method-name:service#called", "calls_method_name", ["app.py:2"]),
            Edge("other", "repository", "calls_dependency", ["app.py:3"]),
        ],
    )
    assert recover_sensitive_paths(graph) == []
    graph.add_edge(Edge("called", "repository", "calls_dependency", ["app.py:4"]))
    paths = recover_sensitive_paths(graph)
    assert paths[0]["nodes"] == ["route", "handler", "service", "called", "repository"]


def test_unique_interface_implementation_path_is_inferred_and_stable():
    graph = FactGraph(
        nodes=[
            _node("route", "route", handler="handler"),
            _node("handler", "method"),
            _node("contract", "service", java_kind="interface"),
            _node("implementation", "service", java_kind="class"),
            _node("work", "method", owner="implementation"),
            _node("repository", "repository"),
        ],
        edges=[
            Edge("route", "handler", "handled_by", ["app.py:1"]),
            Edge("handler", "contract", "calls_dependency", ["app.py:2"]),
            Edge("handler", "method-name:contract#work", "calls_method_name", ["app.py:2"]),
            Edge("implementation", "contract", "implements", ["app.py:3"]),
            Edge("work", "repository", "calls_dependency", ["app.py:4"]),
        ],
    )
    paths = recover_sensitive_paths(graph)
    assert len(paths) == 1
    assert paths[0]["nodes"] == ["route", "handler", "contract", "implementation", "work", "repository"]
    assert paths[0]["status"] == "INFERRED"
    assert paths[0]["assumptions"]
    assert "app.py:3" in paths[0]["evidence"]
    first_id = paths[0]["id"]
    graph.add_node(_node("unrelated", "method"))
    assert recover_sensitive_paths(graph)[0]["id"] == first_id


def test_multiple_implementations_do_not_form_a_path():
    graph = FactGraph(
        nodes=[
            _node("route", "route", handler="handler"),
            _node("handler", "method"),
            _node("contract", "service", java_kind="interface"),
            _node("impl1", "service", java_kind="class"),
            _node("impl2", "service", java_kind="class"),
            _node("work1", "method", owner="impl1"),
            _node("repository", "repository"),
        ],
        edges=[
            Edge("route", "handler", "handled_by", ["app.py:1"]),
            Edge("handler", "contract", "calls_dependency", ["app.py:2"]),
            Edge("handler", "method-name:contract#work1", "calls_method_name", ["app.py:2"]),
            Edge("impl1", "contract", "implements", ["app.py:3"]),
            Edge("impl2", "contract", "implements", ["app.py:4"]),
            Edge("work1", "repository", "calls_dependency", ["app.py:5"]),
        ],
    )
    assert recover_sensitive_paths(graph) == []
