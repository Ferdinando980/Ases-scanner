"""Short and linked reading views from the same saved engineering model."""
from __future__ import annotations
from collections import defaultdict
from collections import Counter
from hashlib import sha256
import re

DOCUMENTS = {'requirements': 'RAD.md', 'user_requirements': 'RAD.md',
             'recovered_requirements': 'RAD.md', 'operations': 'RAD.md',
             'scenarios': 'RAD.md', 'api': 'ODD.md', 'test_cases': 'TCS.md', 'test_results': 'TSR.md'}


def anchor(row):
    return 'record-' + sha256(row['id'].encode()).hexdigest()[:24]


def design_reasoning(model, it):
    rows = [r for r in model.get('structure', {}).get('pattern_findings', []) if r.get('design_review')]
    coverage=model.get('design_review_coverage')
    if not rows and coverage is None: return []
    language = 'it' if it else 'en'
    labels = [('problem','Problema da verificare','Problem to verify'),
              ('expected_benefit','Beneficio atteso','Expected benefit'),
              ('existing_solution','Soluzione già presente','Existing solution'),
              ('simpler_alternative','Alternativa più semplice','Simplest alternative'),
              ('when_not_to_apply','Quando lasciar perdere','When to leave it alone'),
              ('questions','Domande prima di decidere','Questions before deciding')]
    lines = ['## Ragionamento sul progetto' if it else '## Design reasoning', '',
             'Ipotesi statiche e soluzioni già presenti. Nessun beneficio del refactoring è stato misurato.' if it else 'Static hypotheses and existing solutions. No refactoring benefit has been measured.', '']
    if coverage is None:
        lines += ['Copertura non registrata in questo snapshot: non dedurla dall’assenza di proposte.' if it else 'Coverage was not recorded in this snapshot: do not infer it from absent suggestions.', '']
    else:
        counts=Counter(r['status'] for r in coverage)
        coverage_labels=[('ANALYZED','Regole applicate','Rules applied'),('UNKNOWN','Non valutati','Not assessed'),('NOT_SUPPORTED','Non supportati','Not supported')]
        lines += ['- '+(a if it else b)+': '+str(counts[k]) for k,a,b in coverage_labels]
        modern=any(r.get('method')=='syntax-responsibilities/2' for r in coverage)
        language_scope=('Python, JavaScript/TypeScript e Java' if it else 'Python, JavaScript/TypeScript and Java') if modern else 'Python'
        lines += ['', ('Regole limitate su sintassi e nomi per '+language_scope+'. Nessun suggerimento non significa nessun problema. La copertura per file è in scanner-findings.json; non comprende sorgenti esclusi dal perimetro.') if it else ('Bounded syntax/name rules for '+language_scope+'. No suggestion does not mean no problem. Per-file coverage is in scanner-findings.json; sources excluded from scope are not included.'), '']
    if not rows:
        lines += ['Nessuna valutazione di responsabilità prodotta nel perimetro applicato.' if it else 'No responsibility review produced within the applied scope.', '']
    for row in rows:
        review = row['design_review']
        verdict = ('Soluzione già presente' if it else 'Existing solution') if review['verdict']=='REUSE_EXISTING' else ('Da approfondire' if it else 'Investigate')
        lines += ['### '+row['pattern']+' — '+verdict, '']
        for key, title_it, title_en in labels:
            lines += ['**'+(title_it if it else title_en)+'**', '', review[key][language], '']
        lines += [('Prove: ' if it else 'Evidence: ')+', '.join(row.get('evidence', [])), '']
    return lines


def marker(row):
    return '<a id="' + anchor(row) + '"></a>'


def md(value):
    return str(value).replace('\\', '\\\\').replace('`', '\\`').replace('[', '\\[').replace(']', '\\]').replace('|', '\\|').replace('\n', ' ')


def index(model):
    aliases = defaultdict(set)
    rows = {}
    for collection, document in DOCUMENTS.items():
        for row in model.get(collection, []):
            pointer = document + '#' + anchor(row)
            rows[row['id']] = row
            for key in ('id', 'entity_ref', 'declared_id'):
                if row.get(key): aliases[row[key]].add(pointer)
    return aliases, rows


def traceability(model, it):
    aliases, rows = index(model)
    links = model.get('links', [])
    # Document mentions have a cited location, not necessarily a source entity.
    # Keep that provenance instead of rendering an empty unresolved endpoint.
    cited = {}
    for link in links[:20000]:
        if not link.get('source') and link.get('locations'):
            locations = []
            for loc in link['locations']:
                positions = ', '.join(str(k) + '=' + str(loc[k]) for k in ('line', 'page', 'sheet', 'cell', 'element') if loc.get(k) is not None)
                locations.append(str(loc.get('path', '')) + (' · ' + positions if positions else ''))
            cited[link['id']] = '; '.join(locations)
    def ref(identifier):
        if identifier in cited:
            return md(cited[identifier])
        targets = aliases.get(identifier, set())
        label = md(identifier)
        return '[' + label + '](' + next(iter(targets)) + ')' if len(targets) == 1 else label + (' (ambiguous)' if targets else ' (unresolved)')
    lines = ['# Tracciabilità' if it else '# Traceability', '',
             'Collegamenti nei due sensi. Presenza, collegamento, risultato importato e soddisfacimento sono evidenze diverse.' if it else
             'Links in both directions. Presence, linkage, imported results and satisfaction are different evidence.', '',
             '| Da / From | A / To | Base | Authority | Stato / Status |', '|---|---|---|---|---|']
    incoming, outgoing = defaultdict(list), defaultdict(list)
    for link in links[:20000]:
        source, target = link.get('source') or link.get('id', ''), link.get('target', '')
        status = link.get('status', 'unverified')
        lines.append('| ' + ' | '.join((ref(source), ref(target), md(link.get('relation', '')), md(link.get('authority', 'unknown')), md(status))) + ' |')
        incoming[target].append((source, link)); outgoing[source].append((target, link))
    if len(links) > 20000:
        lines += ['', str(len(links) - 20000) + (' collegamenti aggiuntivi nel modello completo.' if it else ' additional links in the complete model.')]
    for identifier in sorted(set(incoming) | set(outgoing)):
        lines += ['', '## ' + ref(identifier), '']
        for direction, mapping in ((('In ingresso' if it else 'Incoming'), incoming), (('In uscita' if it else 'Outgoing'), outgoing)):
            for other, link in mapping.get(identifier, []):
                lines.append('- ' + direction + ': ' + ref(other) + ' · ' + md(link.get('relation', '')) + ' · ' + md(link.get('status', 'unverified')))
    lines += ['', 'Riferimenti ambigui o assenti richiedono revisione. Nessun collegamento certifica il requisito.' if it else
              'Ambiguous or absent references need review. No link certifies a requirement.', '']
    return '\n'.join(lines)


def overview(model, it):
    req = model.get('requirements', [])
    user = model.get('user_requirements', [])
    operations = model.get('operations', [])
    sources = model.get('sources', [])
    unread = sum(source.get('extraction') in {'unsupported', 'failed'} for source in sources)
    budget_notice = []
    if any(row.get('path') is None and '1000-entry interpretation limit' in row.get('reason', '') for row in model.get('behavior_coverage', [])):
        budget_notice = [('**Interpretazione incompleta:** è stato raggiunto il limite di 1.000 ingressi. Altri comportamenti del progetto non sono stati interpretati; il riepilogo non rappresenta tutte le funzionalità.' if it else
                          '**Incomplete interpretation:** the 1,000-entry limit was reached. Additional project behavior was not interpreted; this overview does not represent every feature.'), '']
    lines = ['# Il progetto in breve' if it else '# The project at a glance', '',
             'Una lettura sintetica dello stesso modello dei documenti completi. Nessun test del progetto è stato eseguito.' if it else
             'A short reading of the same model as the complete documents. No target tests were executed.', '',
             'Snapshot: ' + model['snapshot_id'], '',
             '## ' + ('Come interpretare questi numeri' if it else 'How to read these numbers'), '',
             ('I requisiti documentati provengono da identificativi RF/RNF, liste strutturate o dichiarazioni HTML esplicite nelle forme supportate. Se la fonte non indica il tipo, il requisito resta fra quelli con tipo non dichiarato. Uno zero non dimostra che il progetto non abbia esigenze: la prosa libera resta interpretata solo in parte.' if it else
              'Documented requirements come from RF/RNF identifiers, structured lists or explicit HTML declarations in supported forms. When the source omits the kind, the requirement remains in the undeclared-kind group. Zero does not prove that the project has no needs; free prose is interpreted only partially.'), '',
             ('I gruppi di ingressi raggruppano comportamenti di API o handler ricostruiti staticamente. Non sono un conteggio delle funzionalità per l’utente. Le definizioni dei test nel codice sono separate dai casi di test documentati e dai risultati importati.' if it else
              'Entry groups collect statically recovered API or handler behavior. They are not a count of user features. Test definitions in source are separate from documented test cases and imported results.'), '',
             (f'Fonti documentali inventariate: {len(sources)}; non lette o di formato non supportato: {unread}. Dettagli e limiti per ciascuna fonte in [DOCUMENT-QUALITY.md](DOCUMENT-QUALITY.md).' if it else
              f'Inventoried document sources: {len(sources)}; unread or unsupported: {unread}. See per-source limits in [DOCUMENT-QUALITY.md](DOCUMENT-QUALITY.md).'), '',
             *budget_notice,
             '| Evidenza / Evidence | Totale / Total |', '|---|---:|',
             '| ' + ('Requisiti documentati riconosciuti, totale' if it else 'Recognized documented requirements, total') + ' | ' + str(len(req)) + ' |',
             '| ' + ('Requisiti funzionali documentati' if it else 'Documented functional requirements') + ' | ' + str(sum(r['kind'] == 'functional' for r in req)) + ' |',
             '| ' + ('Requisiti non funzionali documentati' if it else 'Documented nonfunctional requirements') + ' | ' + str(sum(r['kind'] == 'nonfunctional' for r in req)) + ' |',
             '| ' + ('Requisiti con tipo non dichiarato nella fonte' if it else 'Requirements with no kind declared in source') + ' | ' + str(sum(r.get('kind') == 'unspecified' for r in req)) + ' |',
             '| ' + ('Requisiti dell’utente, non verificati' if it else 'User requirements, unverified') + ' | ' + str(len(user)) + ' |',
             '| ' + ('Comportamenti ricostruiti dal codice' if it else 'Recovered code behaviors') + ' | ' + str(len(model.get('recovered_requirements', []))) + ' |',
             '| ' + ('Gruppi tecnici di ingressi' if it else 'Technical entry groups') + ' | ' + str(len(operations)) + ' |',
             '| ' + ('Definizioni di test riconosciute nel codice' if it else 'Test definitions recognized in source') + ' | ' + str(len(model.get('structure', {}).get('tests', []))) + ' |',
             '| ' + ('Casi di test documentati riconosciuti' if it else 'Recognized documented test cases') + ' | ' + str(len(model.get('test_cases', []))) + ' |',
             '| ' + ('Risultati importati' if it else 'Imported results') + ' | ' + str(len(model.get('test_results', []))) + ' |', '',
             '## ' + ('Operazioni da cui iniziare' if it else 'Operations to start with'), '']
    for row in operations[:16]:
        context = row.get('user_context', {})
        lines += ['### [' + md(context.get('title') or row['name']) + '](RAD.md#' + anchor(row) + ')', '',
                  '\n\n'.join(r['statement_it' if it else 'statement_en'] for r in row.get('behavior_summaries', [])[:1]), '']
        if context.get('purpose'):
            lines += [('Obiettivo fornito dall’utente: ' if it else 'Goal supplied by user: ') + context['purpose'], '']
    if len(operations) > 16:
        lines += [str(len(operations) - 16) + (' altre operazioni nel RAD completo.' if it else ' further operations in the complete RAD.'), '']
    lines += ['## ' + ('Cosa serve ancora chiarire' if it else 'What still needs clarification'), '']
    present = {r['kind'] for r in model.get('excerpts', [])}
    topics = [('purpose', 'Scopo / Purpose'), ('decision', 'Motivazioni / Design rationale'),
              ('persistence', 'Persistenza / Persistence'), ('security', 'Accessi / Access control'),
              ('test-plan', 'Oracoli indipendenti / Independent test oracles')]
    lines += ['- ' + title + ': ' + ('fonte non recuperata' if it else 'source not recovered') for key, title in topics if key not in present]
    if not req: lines.append('- ' + ('Nessuna dichiarazione di requisito isolata nei formati riconosciuti: rivedere la prosa delle fonti prima di concludere che una specifica manchi.' if it else 'No requirement declaration isolated in recognized formats: review source prose before concluding that a specification is missing.'))
    lines += ['- ' + value for value in model.get('unknowns', [])[:5]]
    lines += ['', '## ' + ('Documenti completi' if it else 'Complete documents'), '',
              '- [RAD — ' + ('requisiti e analisi' if it else 'requirements and analysis') + '](RAD.md)',
              '- [SDD — ' + ('struttura e strategie' if it else 'structure and strategies') + '](SDD.md)',
              '- [ODD — ' + ('interfacce e contratti' if it else 'interfaces and contracts') + '](ODD.md)',
              '- [TESTING](TESTING.md) · [TRACEABILITY](TRACEABILITY.md) · [DOCUMENT-QUALITY](DOCUMENT-QUALITY.md)', '',
              'Metodo: ' + model.get('behavior_profile', 'legacy / unknown') + ' · ' + model.get('narrative_profile', 'legacy / unknown'), '']
    return '\n'.join(lines)


def group_missing(lines, it):
    output, missing = [], []
    for line in lines:
        if line.startswith(('Non recuperato. Servono specifiche', 'Not recovered. Supply a specification')) and len(output) >= 2 and output[-2].startswith('## '):
            missing.append(output[-2][3:]); del output[-2:]
        else:
            output.append(line)
    if missing:
        output += ['', '## ' + ('Da completare con fonti o conferme' if it else 'To complete with sources or confirmation'), '']
        output += ['- ' + title for title in dict.fromkeys(missing)]
        output += ['', 'Queste informazioni non sono state recuperate; non sono requisiti dedotti dai nomi del codice.' if it else
                   'This information was not recovered; it is not inferred from code names.', '']
    return output


def observed_design(model, it):
    """Retain the earlier code-only views without appending a second document."""
    structure=model.get('structure', {})
    def evidence(row):
        return ', '.join(row.get('evidence', []) or row.get('provenance', {}).get('evidence', []))
    def findings(rows):
        result=[]
        for row in rows:
            result += ['- **'+md(row.get('pattern', row.get('rule_id', ''))) +'** · '+md(row.get('status', 'UNKNOWN'))+' / '+md(row.get('confidence', 'unknown'))+': '+str(row.get('reason', row.get('message', ''))),
                       '  - '+('Prove: ' if it else 'Evidence: ')+evidence(row)]
            if row.get('guidance'):result.append('  - '+('Limite: ' if it else 'Guardrail: ')+row['guidance'])
        return result
    rad=[]
    actors=structure.get('actors', [])
    if actors:
        rad += ['## Attori ricostruiti' if it else '## Recovered actors', '',
                'Ruoli inferiti dalla struttura, non conferme degli stakeholder.' if it else 'Roles inferred from structure, not stakeholder confirmation.', '']
        rad += ['- '+md(r.get('name',r.get('id')))+' · '+evidence(r) for r in actors]
    sdd=[];odd=[]
    declarations=defaultdict(list)
    for row in model.get('excerpts', []):
        if row.get('kind')!='current-proposed':continue
        current=bool(re.search(r'sistema corrente|current system|as-is|attualmente|currently',row['text'],re.I))
        proposed=bool(re.search(r'sistema proposto|proposed system|to-be|futur',row['text'],re.I))
        declarations['current' if current and not proposed else 'proposed' if proposed and not current else 'mixed'].append(row)
    labels={'current':('Sistema corrente dichiarato','Declared current system'),'proposed':('Sistema proposto dichiarato','Declared proposed system'),'mixed':('Corrente/proposto da distinguere nelle fonti','Current/proposed declarations needing separation')}
    for key,rows in declarations.items():
        sdd += ['## '+labels[key][0 if it else 1],'', 'Fonte documentale; non una decisione ricostruita dal nome del codice.' if it else 'Document declaration; not a design decision inferred from code names.','']
        for row in rows:
            sdd += [row['text'],'']+['- '+md(loc['path']) for loc in row.get('locations',[])]+['']
    frontend=structure.get('frontend') or {}
    if isinstance(frontend,dict) and any(frontend.values()):
        sdd += ['## Struttura frontend osservata / Observed frontend structure' if it else '## Observed frontend structure', '']
        labels={'components':'Componenti','templates':'Template','services':'Servizi','stores':'Store','routes':'Route','api_calls':'Chiamate API'}
        sdd += ['- '+(labels.get(k,k) if it else k)+': '+str(len(v)) for k,v in frontend.items() if isinstance(v,list) and v]
    frontend_findings=structure.get('frontend_findings', [])
    if frontend_findings:
        title='## Architettura frontend e conformità / Frontend architecture and conformance' if it else '## Frontend architecture and conformance'
        section=[title,'',*findings(frontend_findings),'']
        sdd += section;odd += section
    for key,title_it,title_en in (('data_stores','Archivi osservati','Observed data stores'),('trust_boundaries','Confini di fiducia osservati','Observed trust boundaries')):
        rows=structure.get(key, [])
        if rows:
            sdd += ['## '+(title_it if it else title_en),'']+['- '+md(r.get('name',r.get('id')))+' · '+evidence(r) for r in rows]+['']
    conflicts=structure.get('conflicts', [])+structure.get('unknowns', [])
    if conflicts:
        sdd += ['## Conflitti e aspetti non determinati' if it else '## Conflicts and unknowns','']
        sdd += ['- '+str(r.get('statement') or r.get('reason') or r.get('message','')) for r in conflicts]
    patterns=[r for r in structure.get('pattern_findings', []) if r.get('status')!='HINT']
    if patterns:
        odd += ['## Pattern supportati dal codice / Backend and code-level pattern analysis' if it else '## Backend and code-level pattern analysis','',*findings(patterns),'']
    hints=structure.get('pattern_hints', [])
    if hints:
        odd += ['## Segnali deboli esclusi dal feed principale' if it else '## Hints excluded from the main feed','',*findings(hints),'']
    return rad,sdd,odd
