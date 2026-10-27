"""Controlled, bilingual explanations over saved facts; no inferred business intent."""
from __future__ import annotations

import ast
from functools import lru_cache

from . import prose


def _unparen(value):
    while value.startswith('(') and value.endswith(')'):
        depth, quote, escaped, whole = 0, None, False, True
        for index, char in enumerate(value):
            if quote:
                if escaped: escaped = False
                elif char == '\\': escaped = True
                elif char == quote: quote = None
            elif char in "\"'`": quote = char
            elif char == '(': depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0 and index != len(value)-1:
                    whole = False
                    break
        if not whole or depth or quote: break
        value = value[1:-1].strip()
    return value


@lru_cache(maxsize=4096)
def predicate(value, source_language='python'):
    """Peel whole-expression negations, never the left side of `!a && b`."""
    value, negative = value.strip(), False
    for _ in range(40):
        value = _unparen(value)
        node = None
        if source_language == 'python':
            try:
                node = ast.parse(value, mode='eval').body
            except (SyntaxError, ValueError, RecursionError):
                pass
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            negative, value = not negative, ast.unparse(node.operand)
            continue
        if node is not None:
            return ast.unparse(node), negative
        # Flow facts use Python-style `not (...)` around JS conditions.
        if source_language == 'python' and value.startswith('not'):
            rest = value[3:].strip()
            if rest.startswith('(') and _unparen(rest) != rest:
                negative, value = not negative, _unparen(rest)
                continue
        if '!' in value:
            from ..scanners.javascript import parse, walk
            tree = parse('const asesPredicate = (' + value + ');', '.js')
            if tree.has_error:
                break
            declarations = [n for n in walk(tree) if n.type == 'variable_declarator']
            syntax = declarations[0].child_by_field_name('value') if declarations else None
            while syntax is not None and syntax.type == 'parenthesized_expression' and len(syntax.named_children) == 1:
                syntax = syntax.named_children[0]
            if syntax is not None and syntax.type == 'unary_expression':
                operator = syntax.child_by_field_name('operator')
                argument = syntax.child_by_field_name('argument')
                if operator is not None and operator.text == b'!' and argument is not None:
                    negative, value = not negative, argument.text.decode('utf-8')
                    continue
        break
    return value, negative


def condition_text(conditions, language='it', source_language='python', predicates=None):
    it = language == 'it'
    markers = ('Java control flow ', 'comprehension iteration/', 'loop:', 'loop completed ',
               'try path;', 'except ', 'catch path;', 'match case partial:', 'loop/switch path ',
               'loop continuation partial;', 'finally continuation partial;')
    original = [p['expression'] for p in predicates] if predicates is not None else conditions
    if any(c.startswith(markers) for c in original):
        return 'con condizioni del percorso solo parzialmente ricostruite' if it else 'with only partially recovered path conditions'
    parts = []
    for index, condition in enumerate(original):
        value, negative = predicate(condition, source_language)
        if predicates is not None:
            negative = negative != predicates[index]['negated']
        parts.append(prose.condition(value, negative, source_language) if it
                     else ('“' + value + '” evaluates as ' + ('false' if negative else 'true')))
    return ('se ' if it else 'if ') + (' e ' if it else ' and ').join(parts) if parts else ''


def explain_behavior(record, describe_expression):
    clauses = []
    shape_support = {}
    for fact in record.get('facts', []):
        if fact['kind'] == 'object-shape':
            shape_support.setdefault((fact['entity_ref'], fact.get('binding_name')), []).append(fact['fact_id'])
    entries = record['entry_points']
    groups = [('outcome', record['external_outcomes']), ('error', record['errors']), ('effect', record['effects'])]
    omitted = {}
    for kind, facts in groups:
        omitted[kind] = max(0, len(facts)-20)
        for fact in facts[:20]:
            texts = {}
            local = fact['entity_ref'] in entries
            for language in ('it', 'en'):
                it = language == 'it'
                path = next((loc['path'] for loc in record['locations'] if loc.get('entity_ref') == fact['entity_ref']), record.get('entry_path') or '')
                source_language = 'python' if path.endswith('.py') else 'javascript' if path.endswith(('.js','.ts','.jsx','.tsx','.mjs','.cjs','.mts','.cts')) else 'java'
                path = condition_text(fact['conditions'], language, source_language, fact.get('condition_predicates'))
                prefix = (path + ', ') if path else ''
                if kind == 'outcome':
                    shape = list(dict.fromkeys(fact.get('output_fields', [])))
                    action = ('prepara un risultato con i campi «' + '», «'.join(shape) + '»') if it and shape else (
                        'prepares a result with fields “' + '”, “'.join(shape) + '”') if shape else (
                        ('restituisce ' if it else 'returns ') + describe_expression(fact['expression'], language, source_language))
                    if shape and fact.get('output_fields_complete') is False:
                        action += ' (elenco parziale)' if it else ' (partial field list)'
                    if it and shape:
                        meanings = prose.result_fields(fact['expression'], shape, source_language)
                        if meanings:
                            action += ': ' + meanings
                    if fact.get('http_status') is not None:
                        action = ('prepara una risposta JSON HTTP ' if it else 'prepares an HTTP JSON response ') + str(fact['http_status']) + ': ' + action
                elif kind == 'error':
                    action = prose.error(fact['expression'], source_language) if it else ('declares error “' + fact['expression'] + '”')
                    if not local:
                        action += '; la propagazione all’ingresso non è verificata' if it else '; propagation to the entry is unverified'
                else:
                    action = (prose.possible_call(fact['callee'], source_language) + '; l’esecuzione e il salvataggio permanente dei dati restano da verificare') if it else (
                        'may invoke “' + fact['callee'] + '”; durability of the effect is not verified')
                    if not local:
                        action += '; la raggiungibilità dall’ingresso resta da verificare' if it else '; reachability from the entry remains unverified'
                texts[language] = (('nel componente collegato, ' if it else 'in the linked component, ') if not local else '') + prefix + action
            support = shape_support.get((fact['entity_ref'], fact.get('shape_binding')), []) if fact.get('shape_binding') else []
            clauses.append({'kind':kind, 'fact_refs':[fact['fact_id'], *support], 'scope':'entry' if local else 'linked-component',
                            'text_it':texts['it'], 'text_en':texts['en']})
    statements = {}
    for language in ('it', 'en'):
        it = language == 'it'
        outcomes = [c['text_'+language] for c in clauses if c['kind']=='outcome'][:4]
        other = [c['text_'+language] for c in clauses if c['kind']!='outcome'][:3]
        shown = len(outcomes) + len(other)
        total = sum(len(facts) for _, facts in groups)
        parts = [(' oppure ' if it else ' or ').join(outcomes)] if outcomes else []
        parts += other
        if total > shown:
            parts.append((f'altri {total-shown} esiti o dichiarazioni nei dettagli' if it else f'{total-shown} further outcomes or declarations in the details'))
        if not parts:
            parts = ['risultati ed effetti restano da chiarire' if it else 'results and effects remain unknown']
        name = prose.label(record['name']) if it and record['name'].isidentifier() else record['name']
        base = ('L’operazione «'+name+'»: ') if it else ('The “'+record['name']+'” operation: ')
        if record.get('entry_scope'):
            base = ('La funzione interna «'+name+'», nel solo corpo analizzato: ') if it else ('The internal “'+record['name']+'” callable, within its own analyzed body: ')
        statements[language] = base + '; '.join(parts) + '.'
        if record.get('conditional_declaration'):
            statements[language] += (' La dichiarazione è condizionale: non è stabilito quando la funzione sia disponibile.' if it else ' The declaration is conditional: runtime availability is not established.')
    return {'profile':'controlled-narrative/6', 'clauses':clauses, 'omitted_claims':omitted,
            'statement_it':statements['it'], 'statement_en':statements['en']}
