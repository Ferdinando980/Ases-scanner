from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Any

@dataclass
class Evidence:
    state: str = "OBSERVED"
    confidence: str = "high"
    evidence: list[str] = field(default_factory=list)

@dataclass
class Node:
    id: str
    kind: str
    name: str
    path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    provenance: Evidence = field(default_factory=Evidence)

@dataclass
class Edge:
    source: str
    target: str
    relation: str
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class FactGraph:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    coverage: dict[str, dict] = field(default_factory=dict)
    unknowns: list[dict] = field(default_factory=list)
    _node_index: dict = field(default_factory=dict, init=False, repr=False, compare=False)
    _edge_index: dict = field(default_factory=dict, init=False, repr=False, compare=False)

    def __post_init__(self):
        self._node_index = {node.id: node for node in self.nodes}
        self._edge_index = {(edge.source, edge.target, edge.relation): edge for edge in self.edges}

    def add_node(self, node: Node) -> None:
        if node.id not in self._node_index:
            self.nodes.append(node)
            self._node_index[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        key = edge.source, edge.target, edge.relation
        if key not in self._edge_index:
            self.edges.append(edge)
            self._edge_index[key] = edge
        else:
            existing = self._edge_index[key]
            existing.evidence = sorted(set(existing.evidence + edge.evidence))

    def merge(self, other: "FactGraph") -> "FactGraph":
        for n in other.nodes:
            self.add_node(n)
        for e in other.edges:
            self.add_edge(e)
        self.coverage.update(other.coverage)
        self.unknowns.extend(other.unknowns)
        return self

    def to_dict(self) -> dict:
        return {
            "nodes": [asdict(n) for n in self.nodes],
            "edges": [asdict(e) for e in self.edges],
            "coverage": self.coverage,
            "unknowns": self.unknowns,
        }
