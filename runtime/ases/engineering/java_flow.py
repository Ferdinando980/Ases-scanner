"""Java local branches over inert syntax; unresolved joins remain explicit."""
from __future__ import annotations

from ..scanners.java_syntax import field, parse, text
from .flow import condition_predicates, merge_paths, negate

CALLABLES = {'method_declaration', 'constructor_declaration', 'lambda_expression'}
TYPES = {'class_declaration', 'interface_declaration', 'enum_declaration',
         'record_declaration', 'annotation_type_declaration', 'class_body'}
COMPOUND = {'while_statement', 'for_statement', 'enhanced_for_statement', 'do_statement',
            'switch_expression', 'switch_statement', 'try_statement',
            'try_with_resources_statement', 'synchronized_statement', 'labeled_statement', 'assert_statement'}


def java_facts(body, line_offset=0):
    """Accept a located body node; a fragment is supported for legacy callers."""
    if isinstance(body, str):
        root = parse('class AsesFragment { Object asesFragment() ' + body + '}')
        class_body = field(root.named_children[0], 'body')
        declaration = next((n for n in class_body.named_children if n.type == 'method_declaration'), None)
        body = field(declaration, 'body')
    facts = []

    def emit(kind, syntax, conditions, **data):
        if len(facts) < 499:
            facts.append({'kind': kind, 'line': syntax.start_point.row + 1 + line_offset,
                          'conditions': [str(c) for c in conditions],
                          'condition_predicates': condition_predicates(conditions), **data})
        elif len(facts) == 499:
            facts.append({'kind': 'unsupported-flow', 'line': syntax.start_point.row + 1 + line_offset,
                          'conditions': [], 'expression': '500 local-fact limit; remaining syntax not interpreted'})

    def partial(syntax, conditions, reason):
        emit('unsupported-flow', syntax, conditions, expression=reason)

    def unwrap(node):
        while node is not None and node.type == 'parenthesized_expression' and len(node.named_children) == 1:
            node = node.named_children[0]
        return node

    def expression(node):
        return text(node)[:1200]

    def expressions(node, conditions, depth=0):
        if node is None or len(facts) >= 500 or node.type in CALLABLES | TYPES:
            return
        if depth > 128:
            partial(node, conditions, '128 local-flow depth limit; expression omitted')
            return
        node = unwrap(node)
        if node.type in COMPOUND:
            partial(node, conditions, 'Java compound expression partial: ' + node.type)
            return
        if node.type == 'ternary_expression':
            test = expression(field(node, 'condition'))
            expressions(field(node, 'condition'), conditions, depth + 1)
            expressions(field(node, 'consequence'), (*conditions, test), depth + 1)
            expressions(field(node, 'alternative'), (*conditions, negate(test)), depth + 1)
            return
        operator = next((c.type for c in node.children if c.type in {'&&', '||'}), None)
        if node.type == 'binary_expression' and operator:
            left, right = field(node, 'left'), field(node, 'right')
            expressions(left, conditions, depth + 1)
            expressions(right, (*conditions, expression(left) if operator == '&&' else negate(expression(left))), depth + 1)
            return
        if node.type == 'method_invocation':
            receiver, name, arguments = field(node, 'object'), field(node, 'name'), field(node, 'arguments')
            callee = (expression(receiver) + '.' if receiver else '') + text(name)
            emit('call', node, conditions, callee=callee,
                 arguments=[expression(a) for a in arguments.named_children] if arguments else [])
        # Arguments of an anonymous object may execute; its methods do not belong to this body.
        for child in node.named_children:
            expressions(child, conditions, depth + 1)

    def returned(value, statement, conditions, depth):
        value = unwrap(value)
        if depth > 128:
            partial(statement, conditions, '128 local-flow depth limit; return omitted')
        elif value is not None and value.type == 'ternary_expression':
            test = expression(field(value, 'condition'))
            emit('branch', value, conditions, expression=test)
            expressions(field(value, 'condition'), conditions)
            returned(field(value, 'consequence'), statement, (*conditions, test), depth + 1)
            returned(field(value, 'alternative'), statement, (*conditions, negate(test)), depth + 1)
        else:
            emit('return', statement, conditions, expression=expression(value) or 'void', output_fields=[])
            expressions(value, conditions)

    def sequence(statements, paths, depth=0):
        for statement in statements:
            if statement is None or not paths or len(facts) >= 500:
                break
            if depth > 128:
                partial(statement, (), '128 local-flow depth limit; continuation omitted')
                return []
            following = []
            for conditions in paths:
                kind = statement.type
                if kind in CALLABLES | TYPES or kind in {'line_comment', 'block_comment'}:
                    following.append(conditions)
                elif kind in {'block', 'constructor_body'}:
                    following += sequence(statement.named_children, [conditions], depth + 1)
                elif kind == 'if_statement':
                    test_node = unwrap(field(statement, 'condition'))
                    test = expression(test_node)
                    emit('branch', statement, conditions, expression=test)
                    expressions(test_node, conditions)
                    if test != 'false':
                        following += sequence([field(statement, 'consequence')], [(*conditions, test)], depth + 1)
                    if test != 'true':
                        alternative = field(statement, 'alternative')
                        following += sequence([alternative], [(*conditions, negate(test))], depth + 1) if alternative else [(*conditions, negate(test))]
                elif kind == 'return_statement':
                    returned(statement.named_children[0] if statement.named_children else None, statement, conditions, depth)
                elif kind == 'throw_statement':
                    value = statement.named_children[0] if statement.named_children else None
                    emit('throw', statement, conditions, expression=expression(value))
                    expressions(value, conditions)
                elif kind in {'break_statement', 'continue_statement', 'yield_statement'}:
                    partial(statement, conditions, 'Java abrupt loop/switch exit; target unresolved')
                elif kind in COMPOUND:
                    partial(statement, conditions, 'Java compound flow partial: ' + kind + '; joins and outward exits unresolved')
                    # Do not flatten unresolved catches/finally or nested exits into unconditional facts.
                    expressions(field(statement, 'condition'), (*conditions, 'Java control flow partial; compound condition'))
                    following.append((*conditions, 'Java control flow partial; continuation after ' + kind))
                else:
                    expressions(statement, conditions)
                    following.append(conditions)
            paths, limited = merge_paths(following)
            if limited:
                partial(statement, (), '64 live-path limit; some continuations omitted')
        return paths

    if body is None:
        return []
    if body.has_error:
        partial(body, (), 'Malformed Java body; interpretation withheld')
    else:
        sequence(body.named_children, [()])
    return facts
