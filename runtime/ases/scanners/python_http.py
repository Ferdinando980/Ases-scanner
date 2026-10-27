"""Bounded http.server dispatch-table declarations; no imports or target execution."""
from __future__ import annotations

import ast
from collections import Counter, defaultdict

from ..model import Node, Edge, Evidence

PROFILE = 'stdlib-dispatch/2'
METHODS = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'}


def declaration_bindings(body):
    names = []
    for node in body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node,ast.Import):
            names.extend(alias.asname or alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node,ast.ImportFrom):
            names.extend(alias.asname or alias.name for alias in node.names)
    return names


def scoped_nodes(body):
    pending = list(reversed(body))
    while pending:
        node = pending.pop()
        yield node
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            pending.extend(reversed(list(ast.iter_child_nodes(node))))


def handler_classes(tree):
    names = set()
    for statement in tree.body:
        if isinstance(statement, ast.ImportFrom) and statement.module == 'http.server':
            names.update(alias.asname or alias.name for alias in statement.names if alias.name == 'BaseHTTPRequestHandler')
        elif isinstance(statement, ast.Import):
            for alias in statement.names:
                if alias.name in {'http', 'http.server'}:
                    names.add((alias.asname or alias.name) + ('.server.BaseHTTPRequestHandler' if alias.name == 'http' else '.BaseHTTPRequestHandler'))
    def dotted(node):
        if isinstance(node, ast.Name): return node.id
        if isinstance(node, ast.Attribute): return dotted(node.value) + '.' + node.attr
        return ''
    if not names:
        return []
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    stores = Counter(n.id for n in scoped_nodes(tree.body) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store))
    bindings = stores + Counter(declaration_bindings(tree.body))
    result = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef): continue
        for base in node.bases:
            name = dotted(base)
            if name not in names or bindings[name.split('.')[0]] != 1: continue
            shadowed = False
            parent = parents.get(node)
            while parent is not None and not isinstance(parent, ast.Module):
                if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    local = {n.id for n in scoped_nodes(parent.body) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
                    local.update(declaration_bindings(parent.body))
                    if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args = parent.args
                        local.update(a.arg for a in [*args.posonlyargs, *args.args, *args.kwonlyargs, args.vararg, args.kwarg] if a)
                    shadowed |= name.split('.')[0] in local
                parent = parents.get(parent)
            if not shadowed:
                result.append(node)
                break
    return result


def response_wrappers(handler, tree, rel):
    """Prove a local JSON serializer-to-HTTP-write wrapper, rather than naming it."""
    methods = {n.name:n for n in handler.body if isinstance(n, ast.FunctionDef) and not n.decorator_list}
    if 'send_response' in methods or any(isinstance(n,ast.Attribute) and isinstance(n.ctx,ast.Store)
                                        and n.attr in {*methods,'wfile','send_response'} for n in ast.walk(handler)):
        return []
    json_names = {alias.asname or alias.name for statement in tree.body if isinstance(statement, ast.Import)
                  for alias in statement.names if alias.name == 'json'}
    if any(isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and n.id in json_names for n in scoped_nodes(tree.body)):
        return []
    senders = {}
    for name, method in methods.items():
        args = [*method.args.posonlyargs, *method.args.args]
        if len(args) < 3: continue
        self_name, status, data = [a.arg for a in args[:3]]
        body = list(scoped_nodes(method.body))
        if any(isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store) and n.id in {self_name,status,data} for n in body): continue
        status_call = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'send_response'
                          and isinstance(n.func.value, ast.Name) and n.func.value.id == self_name
                          and n.args and isinstance(n.args[0],ast.Name) and n.args[0].id == status for n in body)
        write = any(isinstance(n, ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr == 'write'
                    and isinstance(n.func.value,ast.Attribute) and n.func.value.attr == 'wfile'
                    and isinstance(n.func.value.value,ast.Name) and n.func.value.value.id == self_name
                    and n.args and isinstance(n.args[0],ast.Name) and n.args[0].id == data for n in body)
        if status_call and write: senders[name] = method.lineno
    result = []
    for name, method in methods.items():
        args = [*method.args.posonlyargs, *method.args.args]
        if len(args) != 3: continue
        self_name, status, payload = [a.arg for a in args]
        if json_names & {self_name,status,payload}: continue
        body = list(scoped_nodes(method.body))
        if json_names & set(declaration_bindings(body)): continue
        assignments = defaultdict(list)
        for n in body:
            if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
                assignments[n.targets[0].id].append(n.value)
        if any(isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store) and n.id in {self_name,status,payload,*json_names} for n in body): continue
        for call in (n for n in body if isinstance(n,ast.Call)):
            if (not isinstance(call.func,ast.Attribute) or not isinstance(call.func.value,ast.Name)
                    or call.func.value.id != self_name or call.func.attr not in senders or len(call.args)<2
                    or not isinstance(call.args[0],ast.Name) or call.args[0].id != status): continue
            value = call.args[1]
            if isinstance(value,ast.Name) and len(assignments[value.id])==1: value=assignments[value.id][0]
            if isinstance(value,ast.Call) and isinstance(value.func,ast.Attribute) and value.func.attr=='encode':
                value=value.func.value
            if (isinstance(value,ast.Call) and isinstance(value.func,ast.Attribute) and value.func.attr=='dumps'
                    and isinstance(value.func.value,ast.Name) and value.func.value.id in json_names
                    and len(value.args)==1 and isinstance(value.args[0],ast.Name) and value.args[0].id==payload):
                result.append({'method':name,'payload_argument':1,'status_argument':0,
                               'evidence':[f'{rel}:{method.lineno}',f'{rel}:{senders[call.func.attr]}']})
    return result


def recover_dispatch_tables(tree, graph, rel, module_name, function_nodes):
    classes = handler_classes(tree)
    if not classes:
        return
    functions = defaultdict(list)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions[node.name].append(node)
    functions = {name: nodes[0] for name, nodes in functions.items() if len(nodes) == 1 and not nodes[0].decorator_list}
    tables, prefix_tables = {}, set()
    stores = Counter(n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store))
    bindings = Counter(declaration_bindings(tree.body))
    functions = {name: fn for name, fn in functions.items() if not stores[name] and bindings[name]==1}
    url_parsers = {alias.asname or alias.name for statement in tree.body
                   if isinstance(statement, ast.ImportFrom) and statement.module == 'urllib.parse'
                   for alias in statement.names if alias.name == 'urlparse' and not stores[alias.asname or alias.name]}
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
            name, value = statement.targets[0].id, statement.value
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            name, value = statement.target.id, statement.value
        else:
            continue
        if stores[name] != 1:
            continue
        if isinstance(value, (ast.List, ast.Tuple)) and value.elts and all(
                isinstance(pair, (ast.List, ast.Tuple)) and len(pair.elts) == 2
                and isinstance(pair.elts[0], ast.Constant) and isinstance(pair.elts[0].value, str)
                and pair.elts[0].value.startswith('/') and '*' not in pair.elts[0].value
                and isinstance(pair.elts[1], ast.Name) and pair.elts[1].id in functions for pair in value.elts):
            tables[name] = [(pair.elts[0], pair.elts[1]) for pair in value.elts]
            prefix_tables.add(name)
        if not isinstance(value, ast.Dict) or not value.keys:
            continue
        if all(isinstance(k, ast.Constant) and isinstance(k.value, str) and k.value.startswith('/')
               and isinstance(v, ast.Name) and v.id in functions for k, v in zip(value.keys, value.values)):
            if len({k.value for k in value.keys}) == len(value.keys):
                tables[name] = list(zip(value.keys, value.values))
    # Mutation, aliases and unknown consumers make a registry's bindings uncertain.
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store) and isinstance(node.value, ast.Name):
            tables.pop(node.value.id, None)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.attr != 'get':
            tables.pop(node.func.value.id, None)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.Return)):
            value = node.value
            if isinstance(value, ast.Name): tables.pop(value.id, None)
    def lookup_parameter(helper):
        body = list(scoped_nodes(helper.body))
        returned = {n.value.id for n in body if isinstance(n, ast.Return) and isinstance(n.value, ast.Name)}
        args = [*helper.args.posonlyargs, *helper.args.args]
        result = set()
        for statement in body:
            if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name): continue
            call = statement.value
            if (statement.targets[0].id in returned and isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                    and call.func.attr == 'get' and isinstance(call.func.value, ast.Name)):
                if call.args and isinstance(call.args[0], ast.Name):
                    table_name, key_name = call.func.value.id, call.args[0].id
                    changed = any(isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store) and n.id in {table_name,key_name} for n in body)
                    changed |= any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name)
                                   and n.func.value.id==table_name and n.func.attr!='get' for n in body)
                    changed |= any(isinstance(n,ast.Subscript) and isinstance(n.ctx,ast.Store) and isinstance(n.value,ast.Name)
                                   and n.value.id==table_name for n in body)
                    allowed = {id(n.func.value) for n in body if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
                               and n.func.attr=='get' and isinstance(n.func.value,ast.Name)}
                    changed |= any(isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load) and n.id==table_name and id(n) not in allowed for n in body)
                    if not changed:
                        result.update((i,j) for i,arg in enumerate(args) if arg.arg==table_name
                                      for j,key in enumerate(args) if key.arg==key_name)
        return result
    lookup_helpers = {name: lookup_parameter(fn) for name, fn in functions.items()}
    def prefix_parameter(helper):
        args = [*helper.args.posonlyargs, *helper.args.args]
        body = list(scoped_nodes(helper.body))
        result = set()
        for loop in body:
            if not (isinstance(loop, ast.For) and isinstance(loop.iter, ast.Name)
                    and isinstance(loop.target, (ast.Tuple, ast.List)) and len(loop.target.elts) == 2
                    and all(isinstance(n, ast.Name) for n in loop.target.elts)):
                continue
            prefix, candidate = [n.id for n in loop.target.elts]
            if len(loop.body) != 1 or not isinstance(loop.body[0], ast.If): continue
            branch = loop.body[0]
            test = branch.test
            if not (isinstance(test, ast.Call) and isinstance(test.func, ast.Attribute)
                    and test.func.attr == 'startswith' and isinstance(test.func.value, ast.Name)
                    and len(test.args) == 1 and isinstance(test.args[0], ast.Name) and test.args[0].id == prefix
                    and not test.keywords and len(branch.body) == 1 and not branch.orelse
                    and isinstance(branch.body[0], ast.Return) and isinstance(branch.body[0].value, ast.Name)
                    and branch.body[0].value.id == candidate):
                continue
            table_name, key_name = loop.iter.id, test.func.value.id
            if len({prefix, candidate, table_name, key_name}) != 4: continue
            # No mutation, alias, escape or shadow of the two parameters is supported.
            allowed = {id(loop.iter), id(test.func.value)}
            for n in body:
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'get'
                        and isinstance(n.func.value, ast.Name) and len(n.args) == 1
                        and isinstance(n.args[0], ast.Name) and n.args[0].id == key_name
                        and any(args[i].arg == n.func.value.id and args[j].arg == key_name
                                for i,j in lookup_helpers.get(helper.name, set()))):
                    allowed.add(id(n.args[0]))
            if any(isinstance(n, ast.Name) and n.id in {table_name, key_name}
                   and (isinstance(n.ctx, ast.Store) or isinstance(n.ctx, ast.Load) and id(n) not in allowed) for n in body):
                continue
            if {table_name,key_name} & set(declaration_bindings(body)): continue
            result.update((i,j) for i,arg in enumerate(args) if arg.arg==table_name
                          for j,key in enumerate(args) if key.arg==key_name)
        return result
    prefix_helpers = {name: prefix_parameter(fn) for name, fn in functions.items()}
    allowed_loads = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call): continue
        if isinstance(node.func,ast.Attribute) and node.func.attr=='get' and isinstance(node.func.value,ast.Name):
            allowed_loads.add(id(node.func.value))
        for index, arg in enumerate(node.args):
            if isinstance(arg, ast.Name) and arg.id in tables:
                helpers = prefix_helpers if arg.id in prefix_tables else lookup_helpers
                if not isinstance(node.func, ast.Name) or index not in {i for i, _ in helpers.get(node.func.id, set())}:
                    tables.pop(arg.id, None)
                else:
                    allowed_loads.add(id(arg))
    for node in ast.walk(tree):
        if isinstance(node,ast.Name) and isinstance(node.ctx,ast.Load) and node.id in tables and id(node) not in allowed_loads:
            tables.pop(node.id,None)
    count = 0
    for handler in classes:
        responses = response_wrappers(handler, tree, rel)
        for method in handler.body:
            if not isinstance(method, ast.FunctionDef) or not method.name.startswith('do_') or method.name[3:] not in METHODS:
                continue
            pending, seen = [(method, 0)], set()
            while pending:
                function, depth = pending.pop(0)
                if function in seen: continue
                seen.add(function)
                body = list(scoped_nodes(function.body))
                # A static declaration is supported only where the selected callable is invoked.
                invoked = {n.func.id for n in body if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
                args = function.args
                positional = [*args.posonlyargs, *args.args]
                request = positional[0].arg if positional else None
                local_stores = Counter(n.id for n in body if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store))
                if local_stores[request]: continue
                shadows = {a.arg for a in [*args.posonlyargs, *args.args, *args.kwonlyargs, args.vararg, args.kwarg] if a}
                shadows |= {n.id for n in body if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
                shadows.update(declaration_bindings(body))
                assignments = defaultdict(list)
                for statement in body:
                    if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
                        assignments[statement.targets[0].id].append(statement.value)
                def request_path(value, seen=frozenset()):
                    if isinstance(value, ast.Name) and value.id not in seen and len(assignments[value.id]) == 1 and local_stores[value.id]==1:
                        return request_path(assignments[value.id][0], seen | {value.id})
                    if not isinstance(value, ast.Attribute) or value.attr != 'path': return False
                    if isinstance(value.value, ast.Name) and value.value.id == request: return True
                    parsed = value.value
                    if isinstance(parsed, ast.Name) and len(assignments[parsed.id]) == 1 and local_stores[parsed.id]==1:
                        parsed = assignments[parsed.id][0]
                    return (isinstance(parsed, ast.Call) and isinstance(parsed.func, ast.Name) and parsed.func.id in url_parsers
                            and parsed.func.id not in shadows and len(parsed.args) == 1
                            and isinstance(parsed.args[0], ast.Attribute) and parsed.args[0].attr == 'path'
                            and isinstance(parsed.args[0].value, ast.Name) and parsed.args[0].value.id == request)
                def lookup_use(call):
                    if not isinstance(call, ast.Call): return []
                    if (isinstance(call.func, ast.Attribute) and call.func.attr == 'get' and isinstance(call.func.value, ast.Name)
                            and call.args and request_path(call.args[0])):
                        return [(call.func.value.id, call)] if call.func.value.id not in prefix_tables else []
                    if isinstance(call.func, ast.Name) and call.func.id not in shadows:
                        pairs = lookup_helpers.get(call.func.id, set()) | prefix_helpers.get(call.func.id, set())
                        return [(call.args[index].id, call) for index, key in pairs
                                if max(index,key) < len(call.args) and isinstance(call.args[index], ast.Name)
                                and request_path(call.args[key])
                                and (index,key) in (prefix_helpers if call.args[index].id in prefix_tables else lookup_helpers).get(call.func.id,set())]
                    return []
                for call in (n for n in body if isinstance(n, ast.Call)):
                    if (isinstance(call.func, ast.Name) and call.func.id in functions and call.func.id not in shadows and depth < 3
                            and call.args and isinstance(call.args[0], ast.Name) and call.args[0].id == request):
                        pending.append((functions[call.func.id], depth + 1))
                uses = []
                for statement in body:
                    if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name): continue
                    call = statement.value
                    if statement.targets[0].id not in invoked or not isinstance(call, ast.Call): continue
                    if local_stores[statement.targets[0].id] != len(assignments[statement.targets[0].id]): continue
                    if any(not lookup_use(value) for value in assignments[statement.targets[0].id]): continue
                    uses.extend(lookup_use(call))
                for name, call in uses:
                    if name in shadows: continue
                    selected_name = next(statement.targets[0].id for statement in body
                                         if isinstance(statement,ast.Assign) and statement.value is call)
                    invocations = [n for n in body if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id==selected_name]
                    forwards_request = all(n.args and isinstance(n.args[0],ast.Name) and n.args[0].id==request for n in invocations)
                    for path_node, target in tables.get(name, []):
                        function_node = functions[target.id]
                        target_id = function_nodes.get((rel, id(function_node)))
                        if target_id is None: continue
                        is_prefix = name in prefix_tables
                        verb, path = method.name[3:], path_node.value + ('*' if is_prefix else '')
                        route_id = f'route:{verb}:{path}:{rel}:{path_node.lineno}'
                        evidence = sorted({f'{rel}:{line}' for line in (path_node.lineno, call.lineno, method.lineno, function_node.lineno)})
                        graph.add_node(Node(route_id, 'route', verb + ' ' + path, rel,
                                            {'http_method':verb,'path':path,'handler':target_id,'framework':'Python http.server',
                                             'route_scope':'declared-static-prefix-table' if is_prefix else 'declared-static-table','dispatch_table':name,
                                             'match_kind':'prefix' if is_prefix else 'exact',
                                             'path_prefix':path_node.value if is_prefix else None,
                                             'dispatch_precedence':'source order; overlapping declarations and guards may shadow this candidate',
                                             'registration_basis':'literal registry, reachable dispatch and selected callable invocation; runtime and guards unverified',
                                             'response_wrappers':responses if forwards_request else [],
                                             'dispatch_profile':PROFILE}, Evidence(state='INFERRED',confidence='medium',evidence=evidence)))
                        graph.add_edge(Edge(route_id,target_id,'handled_by',evidence))
                        count += 1
    graph.unknowns.append({'path':rel,'line':classes[0].lineno,'reason':'python_custom_http_routing_partial' if count else 'python_custom_http_routing_not_reconstructed',
                           'state':'UNKNOWN','basis':'Only unmutated literal exact-match and ordered startswith-prefix tables with local functions and supported lookup/invocation syntax are reconstructed. Dynamic, inherited dispatch, guards, shadowing and runtime registration remain unassessed.'})
