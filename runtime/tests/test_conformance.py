from ases.model import FactGraph, Node, Edge, Evidence
from ases.recovery.conformance import recover_architecture_conformance


def test_layered_conformance_only_after_architecture_observed():
    g=FactGraph()
    for i,k in [('c','controller'),('s','service'),('r','repository')]:
        g.add_node(Node(i,k,i,provenance=Evidence(evidence=[f'{i}.java:1'])))
    g.add_edge(Edge('c','r','depends_on',['Controller.java:5']))
    assert recover_architecture_conformance(g,[])==[]
    findings=recover_architecture_conformance(g,[{'pattern':'Layered Architecture','status':'OBSERVED'}])
    assert findings[0]['status']=='CONTRADICTED'
    assert findings[0]['rule_id']=='conformance.layered_dependency'
