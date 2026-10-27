"""Bounded Italian wording of syntax, never a guess at business intent or execution."""
from __future__ import annotations

import ast
from functools import lru_cache
import re


def label(value):
    value = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', value)
    return value.replace('_', ' ').strip() or value


def quoted(value):
    return '«' + value + '»'


def join(preposition, noun):
    forms = {'a':{'il ':'al ', 'lo ':'allo ', 'la ':'alla ', 'l’':'all’'},
             'di':{'il ':'del ', 'lo ':'dello ', 'la ':'della ', 'l’':'dell’'},
             'da':{'il ':'dal ', 'lo ':'dallo ', 'la ':'dalla ', 'l’':'dall’'},
             'su':{'il ':'sul ', 'lo ':'sullo ', 'la ':'sulla ', 'l’':'sull’'}}
    for article, contracted in forms.get(preposition, {}).items():
        if noun.startswith(article): return contracted + noun[len(article):]
    return preposition + ' ' + noun


@lru_cache(maxsize=2048)
def syntax(value, source_language):
    if len(value) > 1500:
        return None
    try:
        if source_language == 'python':
            return ast.parse(value, mode='eval').body
        if source_language == 'java':
            from ..scanners.java_syntax import parse
            root = parse('class AsesProse { Object value() { return ' + value + '; } }')
        else:
            from ..scanners.javascript import parse
            root = parse('const asesProseValue = (' + value + ');', '.js')
        if root.has_error:
            return None
        pending = [root]
        while pending:
            node = pending.pop()
            if source_language == 'java' and node.type == 'return_statement':
                return unwrap(node.named_children[0]) if node.named_children else None
            if source_language != 'java' and node.type == 'variable_declarator':
                return unwrap(node.child_by_field_name('value'))
            pending.extend(reversed(node.named_children))
    except (SyntaxError, ValueError, RecursionError):
        return None
    return None


def unwrap(node):
    while node is not None and node.type in {'parenthesized_expression'} and len(node.named_children) == 1:
        node = node.named_children[0]
    return node


def raw(node):
    return node.text.decode('utf-8')


def constant(node):
    """Known literal only. Foreign escaped strings stay technical, not Python-decoded."""
    if isinstance(node, ast.Constant):
        v = node.value
        if v is None: return 'nessun valore (None)'
        if v is True: return 'vero'
        if v is False: return 'falso'
        if type(v) in (int, float): return str(v)
        if isinstance(v, str) and len(v) <= 160 and '\n' not in v and '\r' not in v: return quoted(v)
    if node is not None and not isinstance(node, ast.AST):
        text = raw(node)
        if node.type in {'null', 'null_literal'}: return 'nessun valore (null)'
        if node.type in {'true', 'false', 'boolean_literal'}: return {'true':'vero', 'false':'falso'}.get(text)
        if node.type in {'number', 'decimal_integer_literal', 'decimal_floating_point_literal'}: return text
        if node.type in {'string', 'string_literal', 'character_literal'} and len(text) <= 162 and '\\' not in text:
            return quoted(text[1:-1])
    return None


def call_parts(node):
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name): return node.func.id, None, node.args
        if isinstance(node.func, ast.Attribute): return node.func.attr, node.func.value, node.args
    elif node is not None and not isinstance(node, ast.AST):
        if node.type in {'call_expression', 'object_creation_expression'}:
            fn = node.child_by_field_name('function') or node.child_by_field_name('type')
            args = node.child_by_field_name('arguments')
            if fn is not None and fn.type in {'identifier', 'type_identifier'}: return raw(fn), None, args.named_children if args else []
            if fn is not None and fn.type == 'member_expression':
                prop = fn.child_by_field_name('property')
                if prop is not None: return raw(prop), fn.child_by_field_name('object'), args.named_children if args else []
        if node.type == 'method_invocation':
            name = node.child_by_field_name('name'); args = node.child_by_field_name('arguments')
            if name is not None: return raw(name), node.child_by_field_name('object'), args.named_children if args else []
    return None


def value(node, depth=0):
    if node is None or depth > 7: return None
    literal = constant(node)
    if literal is not None: return literal
    if isinstance(node, ast.Name): return quoted(label(node.id))
    if isinstance(node, ast.Attribute):
        owner = value(node.value, depth+1)
        return 'il campo ' + quoted(label(node.attr)) + ' ' + join('di', owner) if owner else None
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
        owner = value(node.value, depth+1); key = node.slice.value
        if owner and isinstance(key, str): return 'il campo ' + quoted(label(key)) + ' ' + join('di', owner)
        if owner and type(key) is int: return 'l’elemento in posizione ' + str(key) + ' (contando da zero) ' + join('di', owner)
    if isinstance(node, ast.BinOp) and all(isinstance(v, ast.Constant) and type(v.value) in (int, float) for v in (node.left, node.right)):
        op = {ast.Add:'la somma', ast.Sub:'la differenza', ast.Mult:'il prodotto', ast.Div:'il rapporto'}.get(type(node.op))
        if op: return op + ' tra ' + value(node.left) + ' e ' + value(node.right)
    if not isinstance(node, ast.AST):
        node = unwrap(node)
        if node.type in {'identifier', 'type_identifier', 'this', 'super'}: return quoted(label(raw(node)))
        if node.type in {'member_expression', 'field_access'}:
            obj = node.child_by_field_name('object'); prop = node.child_by_field_name('property') or node.child_by_field_name('field')
            owner = value(obj, depth+1)
            if owner and prop is not None: return 'il campo ' + quoted(label(raw(prop))) + ' ' + join('di', owner)
        if node.type in {'subscript_expression', 'array_access'}:
            obj = node.child_by_field_name('object') or node.child_by_field_name('array'); index = node.child_by_field_name('index')
            owner = value(obj, depth+1); key = constant(index)
            if owner and key is not None: return 'il campo o elemento ' + key + ' ' + join('di', owner)
    call = call_parts(node)
    if call:
        name, owner, args = call
        text = 'il risultato dell’operazione ' + quoted(label(name))
        if owner is not None:
            component = value(owner, depth+1)
            if component is None: return None
            text += ' ' + join('di', component)
        # Do not omit keyword/unpacked/multiple arguments and imply a complete invocation.
        if len(args) == 1 and not (isinstance(node, ast.Call) and node.keywords):
            argument = value(args[0], depth+1)
            text += ', applicata ' + join('a', argument) if argument else ', con un argomento da leggere nella prova'
        elif args or isinstance(node, ast.Call) and node.keywords:
            text += ', con gli argomenti indicati nella prova'
        return text
    return None


def condition(expression, negative=False, source_language='python'):
    node = syntax(expression, source_language)
    left = right = op = None
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        left, right = node.left, node.comparators[0]
        op = {ast.Lt:'è inferiore a', ast.LtE:'è inferiore o uguale a', ast.Gt:'è superiore a', ast.GtE:'è superiore o uguale a', ast.Eq:'è uguale a', ast.NotEq:'è diverso da', ast.Is:'è lo stesso oggetto di', ast.IsNot:'non è lo stesso oggetto di', ast.In:'appartiene a', ast.NotIn:'non appartiene a'}.get(type(node.ops[0]))
    elif node is not None and not isinstance(node, ast.AST) and node.type == 'binary_expression':
        operator = node.child_by_field_name('operator')
        if operator is not None:
            symbol = raw(operator)
            op = {'<':'è inferiore a','<=':'è inferiore o uguale a','>':'è superiore a','>=':'è superiore o uguale a','==':'è uguale a','!=':'è diverso da','===':'è uguale, senza conversione di tipo, a','!==':'è diverso, senza conversione di tipo, da'}.get(symbol)
            left, right = node.child_by_field_name('left'), node.child_by_field_name('right')
            if source_language == 'java' and symbol in {'==','!='}:
                # Operand types are not established here: identity vs value equality stays explicit.
                op = 'supera il confronto di uguaglianza con' if symbol == '==' else 'supera il confronto di disuguaglianza con'
    if op:
        a, b = value(left), value(right)
        if a is not None and b is not None:
            head, _, preposition = op.rpartition(' ')
            tail = head + ' ' + join(preposition, b) if preposition in {'a','di','da','con'} else op + ' ' + b
            text = a + ' ' + tail
            if negative and op.startswith('è '): return a + ' non risulta ' + tail[2:]
            return 'non è vero che ' + text if negative else text
    call = call_parts(node)
    if call:
        name, owner, args = call
        text = 'la verifica ' + quoted(label(name))
        if owner is not None:
            component = value(owner)
            if component is None: return 'un controllo non tradotto in linguaggio naturale dà esito ' + ('negativo' if negative else 'positivo') + ' (vedi la prova)'
            text += ' ' + join('di', component)
        if len(args) == 1 and not (isinstance(node, ast.Call) and node.keywords):
            argument = value(args[0])
            text += ' ' + join('su', argument) if argument else ' con un argomento da leggere nella prova'
        elif args or isinstance(node, ast.Call) and node.keywords:
            text += ' con gli argomenti indicati nella prova'
        return text + ' dà esito ' + ('negativo' if negative else 'positivo')
    description = value(node)
    if description:
        return 'il controllo su ' + description + ' dà esito ' + ('negativo' if negative else 'positivo')
    return 'un controllo non tradotto in linguaggio naturale dà esito ' + ('negativo' if negative else 'positivo') + ' (vedi la prova)'


def expression(expression, source_language='python'):
    node = syntax(expression, source_language)
    description = value(node)
    if description: return description
    if isinstance(node, ast.List):
        if any(isinstance(n, ast.Starred) for n in node.elts): return 'una lista con elementi espansi; lunghezza non ricostruita'
        return 'una lista di ' + str(len(node.elts)) + ' elementi'
    if isinstance(node, ast.Compare): return 'l’esito del confronto: ' + condition(expression, source_language=source_language)
    return 'un valore calcolato da un’espressione non tradotta in linguaggio naturale (vedi la prova)'


def result_fields(expression, fields, source_language='python'):
    """Include literal field values only when their original returned object is explicit."""
    node = syntax(expression, source_language); pairs = []
    if isinstance(node, ast.Dict):
        if any(not isinstance(k, ast.Constant) or not isinstance(k.value, str) for k in node.keys):
            return ''  # Expansions/computed keys may overwrite an otherwise visible literal.
        pairs = [(k.value, v) for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant) and isinstance(k.value, str)]
    elif node is not None and not isinstance(node, ast.AST) and node.type == 'object':
        for child in node.named_children:
            if child.type in {'comment', 'line_comment', 'block_comment'}: continue
            if child.type != 'pair': return ''
            k, v = child.child_by_field_name('key'), child.child_by_field_name('value')
            if k is None or k.type not in {'property_identifier', 'string'} or '\\' in raw(k): return ''
            pairs.append((raw(k)[1:-1] if k.type == 'string' else raw(k), v))
    if len({k for k, _ in pairs}) != len(pairs): return ''
    meanings = []
    for k, v in pairs[:6]:
        description = value(v)
        if k in fields and description is not None: meanings.append(quoted(k) + ' vale ' + description)
    return '; '.join(meanings)


def error(expression, source_language='python'):
    node = syntax(expression, source_language); call = call_parts(node)
    if call:
        name, _, args = call
        text = 'segnala un errore tramite ' + quoted(name)
        if args:
            supplied_text = constant(args[0])
            if supplied_text and supplied_text.startswith('«'):
                text += ', a cui viene passato il testo ' + supplied_text
        return text
    return 'segnala un errore; tipo e messaggio richiedono la lettura della prova'


def possible_call(callee, source_language='python'):
    call = call_parts(syntax(callee + '()', source_language))
    if call:
        name, owner, _ = call
        text = 'può chiamare l’operazione ' + quoted(label(name))
        component = value(owner) if owner is not None else None
        if component: text += ' del componente ' + component
        return text
    return 'può effettuare una chiamata che richiede la lettura della prova'
