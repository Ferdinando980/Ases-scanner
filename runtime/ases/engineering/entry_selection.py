"""Deterministic, declared selection under a budget; no domain-name heuristics."""
from collections import defaultdict, deque
from pathlib import PurePosixPath

PROFILE = 'entry-selection/2'
AUXILIARY = frozenset({'bench', 'benchmark', 'benchmarks', 'examples', 'example', 'samples',
                       'scripts', 'tools', 'work', 'experiments', 'research'})


def prioritize(entries, nodes, budget=1000):
    """Application entries before auxiliary trees, then fair file-by-file allocation.

    Every entry is retained in the returned ordering. The caller applies the budget
    and records omissions; filesystem scope and extracted facts are unchanged.
    """
    if len(entries) <= budget:
        return entries
    groups = defaultdict(lambda: defaultdict(deque))
    for entry in entries:
        paths = sorted({nodes[ref].get('path') or '' for ref in entry[2] if ref in nodes})
        path = paths[0] if paths else ''
        auxiliary = any(part.casefold() in AUXILIARY for part in PurePosixPath(path).parts[:-1])
        tier = 0 if entry[3] else 2 if auxiliary else 1
        groups[tier][path].append(entry)
    ordered = []
    for tier in sorted(groups):
        files = groups[tier]
        active = deque(sorted(files))
        while active:
            path = active.popleft()
            ordered.append(files[path].popleft())
            if files[path]: active.append(path)
    return ordered


def prioritize_body_files(nodes_by_file, graph):
    """Protect entry files before spending the independent body-fact budget."""
    nodes = {n['id']:n for n in graph['nodes']}
    handlers = {n.get('metadata',{}).get('handler') for n in graph['nodes'] if n['kind']=='route'} - {None}
    adjacency = defaultdict(list)
    for edge in graph.get('edges', []):
        if edge['relation'] in {'calls','calls_dependency','calls_api'} and edge['target'] in nodes:
            adjacency[edge['source']].append(edge['target'])
    linked, frontier = set(handlers), set(handlers)
    for _ in range(4):
        following = {target for ref in frontier for target in adjacency[ref]} - linked
        linked.update(following); frontier = following
    linked_paths = {nodes[ref].get('path') for ref in linked if ref in nodes}
    def rank(item):
        path, local = item
        tier = (0 if any(n['id'] in handlers for n in local) else 1 if path in linked_paths else
                3 if any(part.casefold() in AUXILIARY for part in PurePosixPath(path).parts[:-1]) else 2)
        return tier, path
    return [(path, sorted(local,key=lambda n:n['id'] not in handlers))
            for path,local in sorted(nodes_by_file.items(),key=rank)]
