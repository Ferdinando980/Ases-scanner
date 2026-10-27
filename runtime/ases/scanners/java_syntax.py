"""Bounded inert Java syntax. Target code and build tools are never executed."""
from __future__ import annotations

from importlib.metadata import version
from tree_sitter import Language, Parser
import tree_sitter_java

MAX_BYTES = 5 * 1024 * 1024
MAX_NODES = 200000
LANGUAGE = Language(tree_sitter_java.language())


def parse(source):
    data = source.encode('utf-8')
    if len(data) > MAX_BYTES:
        raise ValueError('java-source-byte-limit')
    root = Parser(LANGUAGE).parse(data).root_node
    # Bound the traversal before any consumer starts interpreting syntax.
    for _ in walk(root):
        pass
    return root


def walk(node):
    stack, count = [node], 0
    while stack:
        current = stack.pop()
        count += 1
        if count > MAX_NODES:
            raise ValueError('java-syntax-node-limit')
        yield current
        stack.extend(reversed(current.named_children))


def field(node, name):
    return node.child_by_field_name(name) if node is not None else None


def text(node):
    return node.text.decode('utf-8') if node is not None else ''


def parser_profile():
    return {'grammar': version('tree-sitter-java'), 'method': 'java-local-flow/1',
            'limits': {'source_bytes': MAX_BYTES, 'named_nodes': MAX_NODES,
                       'depth': 128, 'facts': 500, 'live_paths': 64}}
