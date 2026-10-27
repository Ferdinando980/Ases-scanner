"""Bounded syntax responsibility reviews, never claims of refactoring benefit.

Use syntax-local observations and uniquely resolved import targets as evidence.
No project code is imported or executed. Names are clues, not business semantics.
"""
from __future__ import annotations

import ast
import re
from collections import Counter, defaultdict

PROFILE = 'syntax-responsibilities/2'
MAX_BYTES = 2 * 1024 * 1024
MAX_NODES = 100_000


def coverage_record(rel, status, reason):
    return {'path':rel, 'status':status, 'reason':reason, 'method':PROFILE,
            'scope':'syntax and name-based responsibility clues; no semantic or runtime verification'}


def _local_walk(node):
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(child for child in ast.iter_child_nodes(current)
                     if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)))


def _calls(node):
    return [n for n in _local_walk(node) if isinstance(n, ast.Call)]


def _bindings(fn):
    bound={n.id for n in _local_walk(fn) if isinstance(n,ast.Name) and isinstance(n.ctx,(ast.Store,ast.Del))}
    bound.update(n.arg for n in ast.walk(fn.args) if isinstance(n,ast.arg))
    bound.update(n.name for n in fn.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)))
    bound.update(alias.asname or alias.name.split('.')[0] for n in _local_walk(fn)
                 if isinstance(n,(ast.Import,ast.ImportFrom)) for alias in n.names)
    return bound


def _name(node):
    if isinstance(node, ast.Name): return node.id
    if isinstance(node, ast.Attribute):
        prefix = _name(node.value)
        return prefix + '.' + node.attr if prefix else ''
    return ''


def _words(it, en):
    return {'it': it, 'en': en}


def _review(problem, benefit, simpler, avoid, existing, questions):
    return dict(problem=problem, expected_benefit=benefit, simpler_alternative=simpler,
                when_not_to_apply=avoid, existing_solution=existing, questions=questions,
                verdict='INVESTIGATE', method=PROFILE)


def _service_review(count):
    return _review(
                _words(f'{count} funzioni mescolano risposta HTTP, operazioni applicative e chiamate di persistenza. I ruoli delle ultime due sono indizi basati sui nomi.', f'{count} functions mix HTTP output, application-looking operations and persistence-looking calls. The latter roles are name-based clues.'),
                _words('Un’operazione applicativa riutilizzabile potrebbe mantenere coordinati salvataggi ed errori tra UI, CLI e altre interfacce, se condividono davvero lo stesso caso d’uso.', 'A reusable application operation could coordinate persistence and errors across UI, CLI and other interfaces, if they really share a use case.'),
                _words('Prima estrai una funzione ordinaria e riusa gli helper esistenti; non serve introdurre una gerarchia di servizi.', 'First extract an ordinary function and reuse existing helpers; no service hierarchy is required.'),
                _words('Lascia gli handler diretti se sono l’unico utilizzatore e l’orchestrazione resta breve e stabile. Non spostare controlli HTTP o autorizzazioni senza verificarne il confine.', 'Keep direct handlers if they are the only consumer and orchestration stays short and stable. Do not move HTTP or authorization checks without reviewing their boundary.'),
                _words('Le funzioni collegate nelle prove potrebbero già incapsulare parte del lavoro. Verifica prima cosa manca al loro contratto.', 'Linked functions in the evidence may already encapsulate part of the work. Review what their contracts actually lack first.'),
                _words('Altre interfacce ripetono questa operazione? Salvataggi, errori e transazioni hanno davvero lo stesso contratto? La duplicazione non è dimostrata.', 'Do other interfaces repeat this operation? Do persistence, errors and transactions really share a contract? Duplication is not established.'))


def _registry_review():
    return _review(
                _words('Sono già registrati provider distinti con funzioni di caricamento locali. È un punto di estensione esistente, non una richiesta di aggiungerne un altro.', 'Distinct providers with local loader functions are already registered. This is existing extensibility, not a request to add another abstraction.'),
                _words('Riutilizzare il registro può evitare un secondo meccanismo di selezione, se il contratto è adatto.', 'Reusing the registry may avoid a second selection mechanism, if its contract fits.'),
                _words('Usa le funzioni e il registro già presenti.', 'Use the existing functions and registry.'),
                _words('Non unificare provider con responsabilità diverse solo perché sono registrati nello stesso posto.', 'Do not unify providers with different responsibilities just because they are registered together.'),
                _words('Registrazioni e definizioni dei loader sono indicate nelle prove. Selezione effettiva, compatibilità e caricamento a runtime non sono verificati.', 'Registrations and loader definitions are linked as evidence. Runtime selection, compatibility and loading are not verified.'),
                _words('Il registro esistente copre il nuovo caso d’uso? Non è dimostrato che questi provider siano algoritmi intercambiabili.', 'Does the existing registry cover the new use case? These providers are not established as interchangeable algorithms.'))


def _strategy_review():
    return _review(
                _words('Una scelta di provider/backend seleziona metodi diversi sullo stesso destinatario sintattico per produrre lo stesso risultato assegnato o restituito.', 'Provider/backend selection chooses different methods on the same syntactic receiver for the same assigned or returned role.'),
                _words('Una funzione selezionata o un contratto comune potrebbe rendere più locale l’aggiunta di una modalità, se le alternative svolgono davvero lo stesso compito.', 'A selected function or shared contract could localize adding a mode, if the alternatives really perform the same task.'),
                _words('Mantieni la condizione con poche alternative; se serve, passa una funzione. Non iniziare da una classe per ogni modalità.', 'Keep the conditional for a few alternatives; pass a function if needed. Do not start with one class per mode.'),
                _words('Non applicare Strategy se le modalità hanno contratti, effetti o gestione degli errori diversi, oppure se la scelta è stabile e già leggibile.', 'Do not apply Strategy when modes have different contracts, effects or errors, or the choice is stable and readable.'),
                _words('Le modalità sono già raccolte nello stesso oggetto: questo coordinamento può essere sufficiente. Eventuali registri altrove non sono automaticamente collegati a questa scelta.', 'The modes are already gathered on one object: this coordination may suffice. Registries elsewhere are not automatically linked to this choice.'),
                _words('Le modalità hanno input, risultato ed errori compatibili? Quanto spesso cambiano? Nessuna equivalenza o pressione al cambiamento è dimostrata.', 'Do modes share compatible inputs, results and errors? How often do they change? Equivalence and change pressure are not established.'))


def responsibility_reviews(files, *, coverage=None):
    """Return arguments for the shared finding builder plus structured rationale."""
    trees = {}
    native=[]
    coverage = coverage if coverage is not None else []
    for path, rel, text in files:
        from ..scanners.javascript import EXTENSIONS
        suffix=path.suffix.lower()
        if suffix not in EXTENSIONS|{'.py','.java'}:
            coverage.append(coverage_record(rel,'NOT_SUPPORTED','language_not_supported'))
            continue
        if len(text.encode('utf-8')) > MAX_BYTES:
            coverage.append(coverage_record(rel,'UNKNOWN','source_byte_limit'))
            continue
        if suffix!='.py':
            from .design_review_syntax import syntax_reviews
            findings,reason=syntax_reviews(rel,text,suffix,MAX_NODES)
            native.extend(findings)
            coverage.append(coverage_record(rel,'ANALYZED' if reason=='bounded_rules_applied' else 'UNKNOWN',reason))
            continue
        try:
            tree = ast.parse(text)
            if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
                coverage.append(coverage_record(rel,'UNKNOWN','syntax_node_limit'))
                continue
            trees[rel] = tree
            coverage.append(coverage_record(rel,'ANALYZED','bounded_rules_applied'))
        except (SyntaxError, ValueError, RecursionError):
            coverage.append(coverage_record(rel,'UNKNOWN','python_syntax_unavailable'))
            continue
    out = native
    for rel, tree in trees.items():
        definitions = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        counts = Counter(n.name for n in definitions)
        funcs = {n.name: n for n in definitions if counts[n.name] == 1}
        # Resolve only explicit relative `from . import module` links to admitted files.
        linked = {}
        import_counts = Counter(alias.asname or alias.name.split('.')[0] for node in _local_walk(tree)
                                if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names)
        shadowed = {n.id for n in _local_walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del))}
        shadowed.update(n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.level and node.module is None:
                parts = rel.split('/')[:-node.level]
                for alias in node.names:
                    target = '/'.join(parts + [alias.name + '.py'])
                    binding = alias.asname or alias.name
                    if target in trees and binding not in shadowed and import_counts[binding] == 1: linked[binding] = target
        handlers = []
        for fn in funcs.values():
            calls = _calls(fn)
            names = [_name(c.func) for c in calls]
            # Transport output plus domain-looking work and persistence-looking work.
            response = [c for c in calls if _name(c.func).rsplit('.', 1)[-1] in {'_json', 'jsonify', 'send_response'}]
            operation = [c for c in calls if _name(c.func).rsplit('.', 1)[-1] in {'ingest', 'mutate', 'query', 'execute'} or re.fullmatch(r'_?(?:apply|run|execute|ui)_(?:\w+_)?(?:mutation|query|query_projection)', _name(c.func).rsplit('.', 1)[-1])]
            persistence = [c for c in calls if _name(c.func).rsplit('.', 1)[-1] in {'save', 'commit', 'persist'} or _name(c.func).rsplit('.', 1)[-1].startswith('_persist_')]
            if not (response and operation and persistence): continue
            evidence = {f'{rel}:{n.lineno}' for n in response + operation + persistence}
            local_bindings = _bindings(fn)
            # Include only statically unique module function definitions, not guessed callees.
            for name in names:
                if name.count('.') != 1: continue
                module, symbol = name.split('.')
                target = linked.get(module) if module not in local_bindings else None
                if target:
                    matches = [n for n in trees[target].body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == symbol]
                    if len(matches) == 1: evidence.add(f'{target}:{matches[0].lineno}')
            handlers.append((fn, evidence))
        if len(handlers) >= 2:
            review = _service_review(len(handlers))
            out.append(dict(rule_id='review.service_responsibilities', status='HINT', confidence='low',
                reason=review['problem']['en'], evidence=sorted({e for _, ev in handlers for e in ev}),
                guidance=review['simpler_alternative']['en'], scope='project', review=review,
                signals={'positive':[f'{len(handlers)} transport/application/persistence mixtures'], 'negative':['roles partly name-based; duplicated use case and refactoring benefit unverified']}))

        # Explicit lazy registration is existing extensibility, not an absent pattern.
        registrations = defaultdict(list)
        rebound_loaders={n.id for n in ast.walk(tree) if isinstance(n,ast.Name) and isinstance(n.ctx,(ast.Store,ast.Del))}
        for fn in funcs.values():
            for call in _calls(fn):
                if _name(call.func).rsplit('.', 1)[-1] != 'register_provider' or len(call.args) < 2: continue
                key, loader = call.args[:2]
                if isinstance(key, ast.Constant) and isinstance(key.value, str) and isinstance(loader, ast.Name) and loader.id in funcs and loader.id not in _bindings(fn)|rebound_loaders:
                    receiver=_name(call.func).rsplit('.',1)[0] if isinstance(call.func,ast.Attribute) else ''
                    registrations[(fn.lineno,receiver)].append((key.value, call, funcs[loader.id]))
        for group in registrations.values():
            if len({key for key, _, _ in group})<2:continue
            review = _registry_review()
            review['verdict'] = 'REUSE_EXISTING'
            out.append(dict(rule_id='review.provider_registry', status='OBSERVED', confidence='medium',
                reason=review['problem']['en'], evidence=sorted({f'{rel}:{n.lineno}' for _, call, loader in group for n in (call, loader)}),
                guidance=review['simpler_alternative']['en'], scope='file', review=review,
                signals={'positive':['literal provider registrations and local loader definitions'], 'negative':['runtime contract and interchangeability not verified']}))

        # Branches selecting methods on the same receiver and assigning the same role.
        for owner in ast.walk(tree):
            if not isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)): continue
            groups = defaultdict(list)
            for node in _local_walk(owner):
                if not isinstance(node, ast.If) or not node.orelse: continue
                tests = [n for n in ast.walk(node.test) if isinstance(n, (ast.Name, ast.Attribute))]
                selectors = {_name(n) for n in tests if _name(n).rsplit('.', 1)[-1] in {'provider', 'backend', 'extractor_provider', 'engine'} }
                if not selectors: continue
                branches = [node.body, node.orelse]
                selected = []
                for branch in branches:
                    choices = []
                    for statement in branch:
                        if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
                            role, value = statement.targets[0].id, statement.value
                        elif isinstance(statement, ast.Return): role, value = 'return', statement.value
                        else: continue
                        if isinstance(value, ast.Await): value = value.value
                        if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute) and _name(value.func.value):
                            choices.append((role, _name(value.func.value), value.func.attr, statement.lineno))
                    selected.append(choices)
                for a in selected[0]:
                    for b in selected[1]:
                        if a[:2] == b[:2] and a[2] != b[2]: groups[a[:2]].extend([a, b])
            if not groups: continue
            sites = [s for group in groups.values() for s in group]
            review = _strategy_review()
            out.append(dict(rule_id='review.strategy_variants', status='HINT', confidence='low', reason=review['problem']['en'],
                evidence=sorted({f'{rel}:{s[3]}' for s in sites}), guidance=review['simpler_alternative']['en'],
                scope='file', review=review, signals={'positive':['conditional method alternatives with shared receiver and output role'],
                'negative':['semantic equivalence, change pressure and benefit unverified']}))
    return out
