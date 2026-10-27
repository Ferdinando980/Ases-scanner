"""Engineering views over saved records; no target access during regeneration."""
from __future__ import annotations

from collections import defaultdict
from importlib.resources import files
import json
from .views import marker, overview, traceability, group_missing, observed_design, design_reasoning


def clean(value):
    return str(value if value is not None else "undeclared / not recovered").replace("\r", "").replace("\x00", "")


def where(loc):
    suffix = " ".join(f"{k}={loc[k]}" for k in ("page", "table", "table_row", "sheet", "cell", "row", "paragraph", "line", "element") if k in loc)
    return clean(loc["path"]) + (" · " + suffix if suffix else "") + " · SHA256 " + loc["sha256"][:12]


def sources(row):
    return "\n".join("- Source: " + where(loc) for loc in row.get("locations", []) + row.get('entry_declaration_locations', []))


def excerpt_sections(model, topics, language):
    lines = []
    for topic, title in topics:
        rows = [r for r in model.get("excerpts", []) if r["kind"] == topic]
        lines += ["## " + title, ""]
        if not rows:
            lines += [("Non recuperato. Servono specifiche o una conferma esplicita: non lo deduciamo dai nomi delle classi." if language == "it" else "Not recovered. Supply a specification or explicit confirmation; class names do not establish this."), ""]
        for row in rows:
            lines += ["### " + row["id"], "", row["text"], "", sources(row), "", "Candidate excerpt — review original context, version and release scope.", ""]
    return lines


def render_documents(model, language="it"):
    it = language == "it"
    relations_by_source, links_by_source = defaultdict(list), defaultdict(list)
    for relation in model.get("relations", []):
        relations_by_source[relation["source"]].append(relation)
    for link in model.get("links", []):
        links_by_source[link.get("source")].append(link)
    spec = json.loads(files("ases.engineering").joinpath("resources/sections.json").read_text(encoding="utf-8"))
    preface = ("Questa è una ricostruzione con fonti: requisiti dichiarati, sintassi osservata e inferenze restano distinti. Nessun test del progetto è stato eseguito. Le sezioni non recuperate indicano cosa manca; non sono requisiti inventati per riempire la pagina." if it else "This is a reconstruction with sources: documented requirements, observed syntax and inferences remain distinct. No target tests were executed. Unknown sections identify missing evidence; they are not invented requirements.")
    identity = f"Snapshot: {model['snapshot_id']}\n\nEngineering model: {model['model_digest']}\n\n"
    def start(title):
        guides = {
            'RAD': ('Qui trovi i bisogni dichiarati nei documenti e, separatamente, i comportamenti ricostruiti dal codice. Parti dalle spiegazioni: una ricostruzione va confermata e non dimostra che un requisito sia soddisfatto.', 'Declared needs and reconstructed code behavior are kept separate. Start with the explanations; a reconstruction needs confirmation and does not prove satisfaction.'),
            'SDD': ('Qui trovi la struttura del sistema e le decisioni dichiarate nelle fonti. I collegamenti osservati descrivono dipendenze statiche; non dimostrano che una chiamata venga eseguita.', 'Read system structure and decisions declared in sources here. Observed links describe static dependencies, not proof that a call executes.'),
            'ODD': ('Qui trovi componenti, interfacce e contratti di dettaglio. Nomi e firme servono a ritrovare il codice: da soli non spiegano lo scopo di business né provano il funzionamento.', 'Read components, interfaces and detailed contracts here. Names and signatures locate source; they do not establish business purpose or correct operation.'),
        }
        guide = guides.get(title.split(' ', 1)[0])
        return ["# " + title, "", preface, "", *(["## Come leggere questo documento" if it else "## How to read this document", "", guide[0 if it else 1], ""] if guide else []), identity]
    rad = start("RAD — Requisiti e analisi" if it else "RAD — Requirements and analysis")
    rad += excerpt_sections(model, [("purpose", "Scopo e obiettivi" if it else "Purpose and goals"), ("current-proposed", "Sistema corrente e proposto" if it else "Current and proposed system")], language)
    for kind, title in (("functional", "Requisiti funzionali" if it else "Functional requirements"), ("nonfunctional", "Requisiti non funzionali" if it else "Nonfunctional requirements"), ("unspecified", "Requisiti con tipo non dichiarato" if it else "Requirements without a declared kind")):
        rad += ["## " + title, ""]
        rows = [r for r in model["requirements"] if r["kind"] == kind]
        if not rows:
            rad += ["Nessun requisito recuperato con questa classificazione. Le classificazioni non dichiarate hanno una sezione separata." if it else "No requirements recovered with this classification. Undeclared kinds have a separate section.", ""]
        for row in rows:
            label = row.get('declared_id') or ('Requisito senza ID dichiarato' if it else 'Requirement without a declared ID')
            if row.get('recognition') in {'explicit-prose/1', 'explicit-prose/2', 'explicit-prose/3'}:
                rad += ['Classificazione da rivedere; chiave interna generata, nessun ID dichiarato nella fonte.' if it else 'Review classification; internal key generated, no ID declared in source.', '']
            if row.get('modality'):
                labels = {'mandatory': ('Obbligo dichiarato', 'Stated obligation'), 'recommendation': ('Raccomandazione', 'Recommendation'),
                          'stated-behavior': ('Comportamento descritto dalla fonte', 'Behavior described by the source'),
                          'capability': ('Capacità o permesso dichiarato', 'Stated capability or permission')}
                rad += [labels.get(row['modality'], (row['modality'], row['modality']))[0 if it else 1] + (' (' + row['modal_text'] + ')' if row.get('modal_text') else '') + '.', '']
            if row.get('subject_missing'):
                rad += ['La frase originale omette il soggetto: attore e applicabilità restano da chiarire.' if it else 'The original sentence omits its subject: actor and applicability need clarification.', '']
            classification = row.get('classification', {})
            if classification.get('origin') == 'text-heuristic':
                rad += [('Tipo suggerito da indizi testuali, da verificare: ' if it else 'Type suggested by textual signals, review required: ') + ', '.join(classification.get('evidence', [])), '']
            statement = row.get("statement") or ("La fonte non contiene un enunciato testuale del requisito; i campi e la provenienza sono conservati senza completare il contenuto." if it else "The source contains no requirement statement; fields and provenance are retained without filling in missing content.")
            satisfaction = row.get("satisfaction", "not-verified")
            rad += [marker(row), "### " + label, "", statement, "", "Authority: document-declaration · satisfaction: " + str(satisfaction), "",
                    "```json", json.dumps(row["fields"], ensure_ascii=False, indent=2), "```", "", "Scope: " + clean(row["scope"]), "", sources(row), ""]
            if row.get("review"):
                rad += ["User review: " + clean(row["review"]), ""]
    rad += ["## Requisiti inseriti o adottati dall’utente" if it else "## User-authored or adopted requirements", "",
            "Questi bisogni sono forniti dall’utente. Non modificano le fonti originali e il loro soddisfacimento non è verificato." if it else "These needs are supplied by the user. They do not alter original sources; their satisfaction is unverified.", ""]
    for row in model.get("user_requirements", []):
        rad += [marker(row), "### " + row["declared_id"], "", row["statement"], "",
                ("Tipo: " if it else "Kind: ") + row["kind"] + " · authority: user-confirmation · satisfaction: not-verified", "",
                ("Autore: " if it else "Author: ") + row["author"], "", ("Ambito: " if it else "Scope: ") + row["scope"], "",
                ("Criterio di accettazione: " if it else "Acceptance criterion: ") + row["acceptance"], "",
                ("Supporto da ricontrollare: il requisito è conservato, ma il candidato originale è assente o cambiato." if it else "Support needs review: the requirement is retained, but its original candidate is absent or changed.") if row["support_state"]=="needs-review" else "Support: " + row["support_state"], ""]
    rad += excerpt_sections(model, [("constraint", "Vincoli" if it else "Constraints")], language)
    rad += ["## Requisiti funzionali ricostruiti dal codice" if it else "## Functional requirements reconstructed from code", "",
            "Queste frasi interpretano i flussi supportati dell’implementazione: non sono requisiti originali approvati. Condizioni, risultati ed effetti rimangono collegati al codice e ai limiti della ricostruzione." if it else "These sentences interpret supported implementation flows; they are not approved original requirements. Conditions, results and effects remain tied to source and reconstruction limits.", ""]
    for row in model.get("recovered_requirements", []):
        if row.get('entry_scope') in {'lexical-local', 'package-local', 'implementation-local', 'conditional-local'}:
            rad += ['Funzione interna: il riepilogo riguarda soltanto il suo corpo, senza attribuirle il comportamento delle funzioni chiamate o un ingresso pubblico.' if it else 'Internal callable: this summary covers only its own body, without importing called functions or asserting a public entry.', '']
        if row.get('conditional_declaration'):
            rad += ['La dichiarazione è dentro una condizione o un blocco di controllo: la sua disponibilità durante l’esecuzione non è stabilita.' if it else 'This declaration is inside conditional/control syntax: runtime availability is not established.', '']
        rad += [marker(row), "### " + row["name"], "", row["statement_it"] if it else row["statement_en"], "", sources(row), "",
                "Vedi la prova: espressioni originali, condizioni e proposte di test (non eseguiti)." if it else "Evidence: original expressions, conditions and proposed tests (not executed).", "",
                "Inputs: " + clean(row.get("inputs")), "", "```json", json.dumps({k: row.get(k, []) for k in ("conditions", "external_outcomes", "returns", "errors", "effects", "flow_limits", "test_ideas")}, ensure_ascii=False, indent=2), "```", ""]
        if row.get("review"):
            rad += ["User review: " + clean(row["review"]), ""]
    rad += ["## Operazioni e domande da chiarire" if it else "## Operations and questions to clarify", ""]
    for row in model.get("operations", []):
        context = row.get("user_context", {})
        rad += [marker(row), "### " + (context.get("title") or row["name"]), "", "ID: " + row["id"], "",
                "Raggruppamento statico degli ingressi espliciti; non è un caso d’uso approvato né una prova dell’ordine globale delle chiamate." if it else "Static grouping of explicit entry points; not an approved use case or proof of global call order.", ""]
        for behavior in row["behavior_summaries"]:
            rad += [behavior["statement_it"] if it else behavior["statement_en"], ""]
        for question in row["questions"]:
            answer = context.get(question["id"])
            rad += ["- " + question["text_it" if it else "text_en"] + (" " + ("Risposta dell’utente: " if it else "User answer: ") + answer if answer else (" Da chiarire." if it else " To clarify."))]
        rad += ["", sources(row), ""]
        if row["supported_steps"]:
            rad += ["Chiamate supportate (ordine globale non stabilito):" if it else "Supported calls (global order not established):", ""]
            rad += ["- " + step["callee"] + " · " + step["scope"] + " · line " + str(step["line"]) for step in row["supported_steps"]]
        if row["omitted_steps"]:
            rad += [str(row["omitted_steps"]) + (" chiamate aggiuntive nello snapshot." if it else " additional calls in the snapshot.")]
        rad += [""]
    rad += ["## Scenari e casi d’uso" if it else "## Scenarios and use cases", ""]
    for row in model.get("scenarios", []):
        rad += [marker(row), "### " + row["declared_id"], "", row["text"], "", sources(row), "", "Trigger, actors, entry/exit, main/alternative/error paths: retain declared text; missing fields remain unknown.", ""]
    rad += ["## Comportamenti osservati nel codice" if it else "## Observed code behavior", ""]
    for row in model.get("structure", {}).get("behaviors", []):
        rad += ["- " + clean(row.get("name", row.get("id"))) + " · static observation; not an approved requirement"]
    rad += [""] + excerpt_sections(model, [("navigation", "Modelli di analisi e navigazione" if it else "Analysis and navigation models"), ("glossary", "Glossario e definizioni" if it else "Glossary and definitions")], language)
    sdd = start("SDD — Architettura e decisioni" if it else "SDD — Architecture and decisions")
    sdd += excerpt_sections(model, [("design-goal", "Obiettivi di design" if it else "Design goals"), ("decision", "Decisioni e compromessi" if it else "Decisions and trade-offs")], language)
    sdd += ["## Sottosistemi e servizi" if it else "## Subsystems and services", ""]
    for row in model.get("structure", {}).get("components", []):
        sdd += ["- " + clean(row.get("name", row.get("id"))) + " · " + clean(row.get("kind")) + " · " + clean(row.get("source") or row.get("path"))]
    sdd += excerpt_sections(model, [("deployment", "Deployment e ambienti" if it else "Deployment and environments"), ("persistence", "Persistenza" if it else "Persistence"), ("security", "Accesso e sicurezza dichiarata" if it else "Declared access and security"), ("concurrency", "Concorrenza e risorse" if it else "Concurrency and resources"), ("boundary", "Avvio, arresto e recupero" if it else "Startup, shutdown and recovery")], language)
    odd = start("ODD — Interfacce e progettazione di dettaglio" if it else "ODD — Interfaces and object design")
    odd += design_reasoning(model, it)
    odd += ["## Introduzione e convenzioni" if it else "## Introduction and conventions", "",
            "Le schede seguono il linguaggio dichiarato. La visibilità Python è una convenzione; i tipi mancanti restano non dichiarati. I contratti nei commenti sono dichiarazioni e le guardie sono rami osservati. Non deduciamo molteplicità, ordine delle chiamate, invarianti o motivazioni per decorare un diagramma." if it else "Class/module/function sheets follow the declared language. Python naming visibility is a convention; missing JS/Python types stay undeclared. Contracts from comments are declarations, guards are observed branches. No multiplicity, call order, invariant or design rationale is inferred to decorate a diagram.", "",
            "## Package e moduli" if it else "## Packages and modules", ""]
    packages = defaultdict(list)
    for row in model["api"]:
        packages[row.get("package", ".")].append(row)
    for package, rows in sorted(packages.items()):
        odd += ["### " + clean(package or "default"), "", (f"{len(rows)} dichiarazioni recuperate. Le responsabilità provengono dai commenti, quando disponibili." if it else f"{len(rows)} recovered declarations. Responsibilities are taken from source comments where available."), ""]
        odd += ["- " + clean(r.get("qualified_name", r["name"])) + " · " + r["id"] for r in rows]
    odd += ["", "## Interfacce e contratti" if it else "## Interfaces and contracts", ""]
    if not model["api"]:
        odd += ["No supported API declarations recovered; consult API coverage. This does not establish that the target has no API.", ""]
    for row in model["api"]:
        odd += [marker(row), "### " + clean(row.get("qualified_name", row["name"])), "", "```" + ("python" if row["language"] == "Python" else ""), row["signature"], "```", "",
                "Kind: " + row["kind"] + " · visibility: " + row["visibility"] + " · owner: " + clean(row.get("owner")), "",
                ("Responsabilità / commento sorgente: " if it else "Responsibility / source comment: ") + clean(row.get("responsibility")), "",
                ("Parametri: " if it else "Parameters: ") + clean(row.get("params")) + ("\n\nRestituisce: " if it else "\n\nReturns: ") + clean(row.get("return_type")), ""]
        for key in ("attributes", "bases", "contracts", "errors_declared", "declared_throws", "errors_observed", "guards_observed"):
            if row.get(key):
                odd += [key + ":", "", "```json", json.dumps(row[key], ensure_ascii=False, indent=2), "```", ""]
        edges = relations_by_source.get(row.get("entity_ref"), [])
        if edges:
            odd += ["Dipendenze / collegamenti statici osservati:" if it else "Dependencies / observed static links:", ""] + ["- " + r["relation"] + " → " + r["target"] for r in edges] + [""]
        related = links_by_source.get(row["id"], [])
        odd += ["- " + r["relation"] + " → " + r["target"] for r in related]
        odd += [sources(row), "", "Effetti, persistenza, concorrenza e sicurezza: questa sola dichiarazione non li dimostra. Consulta SDD e sorgenti." if it else "Effects / persistence / concurrency / security: consult SDD and source; not established by this declaration alone.", ""]
        if row.get("review"):
            odd += ["User review: " + clean(row["review"]), ""]
    odd += ["## Diagrammi delle classi e dei moduli" if it else "## Class and module diagrams", ""]
    for diagram in model.get("diagrams", []):
        names = {r["id"]: "N" + str(i) for i, r in enumerate(diagram["nodes"])}
        odd += ["### " + diagram["name"], "", "```mermaid", "classDiagram"]
        for node in diagram["nodes"]:
            odd += [f'class {names[node["id"]]}["{re_safe(node["name"])}"]']
            if node["kind"] == "module":
                odd += [f'<<module>> {names[node["id"]]}']
        for edge in diagram["edges"]:
            arrow = "--|>" if edge["relation"] in {"extends", "implements"} else "..>"
            odd += [f'{names[edge["source"]]} {arrow} {names[edge["target"]]} : {edge["relation"]} (static)']
        odd += ["```", "", diagram["limits"], ""]
    if model.get("document_api"):
        odd += ["## Interfacce dichiarate nella documentazione" if it else "## Documented interfaces", "", "These signatures come from static documentation, not from source parsing. Check version and source before treating them as current interfaces.", ""]
        for row in model["document_api"]:
            odd += ["```", row["signature"], "```", "", sources(row), ""]
    odd += excerpt_sections(model, [("decision", "Riuso e decisioni motivate" if it else "Reuse and justified decisions"), ("glossary", "Glossario" if it else "Glossary")], language)
    testing = start("TESTING — Evidenze e limiti" if it else "TESTING — Evidence and limits")
    testing += [(f"Test definiti: {len(model.get('test_cases', []))}. Risultati importati: {len(model.get('test_results', []))}. Test del progetto eseguiti da ASES: 0." if it else f"Defined test records: {len(model.get('test_cases', []))}. Imported result records: {len(model.get('test_results', []))}. Target tests executed by ASES: 0."), "",
                "Un risultato può essere storico, copiato o privo di revisione associata. Leggi TP/TCS/TIR/TSR e il perimetro prima di confrontarlo con i requisiti." if it else "A result may be historical, copied or unbound to a revision. Read TP/TCS/TIR/TSR and source scope before comparing results to requirements.", ""]
    tp = start("TP — Piano dei test" if it else "TP — Test plan")
    tp += excerpt_sections(model, [("test-plan", "Strategia, oracoli e criteri dichiarati" if it else "Declared strategy, oracles and criteria")], language)
    tp += ["## Ambito, ambienti e sospensione/ripresa" if it else "## Scope, environments and suspension/resumption", "", "Le dichiarazioni importate sono parziali. Criteri, versioni, ambienti ed esclusioni mancanti richiedono un piano specifico. I soli collegamenti fra codice e test non bastano." if it else "Imported declarations above are partial. Missing criteria, versions, environments and exclusions require a project-specific test plan. Code-test links alone do not establish this.", ""]
    tcs = start("TCS — Specifiche dei test" if it else "TCS — Test specifications")
    for row in model.get("test_cases", []):
        tcs += [marker(row), "## " + row.get("declared_id", row["id"]), "", row["text"], "", sources(row), "", "Status: definition only. Preconditions, inputs, steps, expected result and category/partition frames are retained as declared excerpts; missing fields are not generated as executed tests.", ""]
    tir = start("TIR — Incidenti importati" if it else "TIR — Imported incidents")
    tsr = start("TSR — Risultati importati" if it else "TSR — Imported results")
    tsr += ["Nessun test del progetto è stato eseguito. Data, ambiente e revisione assenti restano sconosciuti. Report identici non sono prove indipendenti multiple." if it else "No target test was run. Missing timestamp/environment/revision binding stays unknown. Identical reports count once as independent evidence.", ""]
    for row in model.get("test_results", []):
        block = [marker(row), "## " + row["id"], "", "```json", json.dumps({k: row.get(k) for k in ("result", "counters", "sessions", "independent_evidence", "revision_bound")}, ensure_ascii=False, indent=2), "```", "", sources(row), ""]
        tsr += block
        if row.get("result", {}) and row["result"].get("status") in {"error", "failure"}:
            tir += block
    guide = start("GUIDE — Uso e installazione" if it else "GUIDE — Usage and installation")
    guide += excerpt_sections(model, [("guide", "Istruzioni disponibili" if it else "Available instructions"), ("deployment", "Installazione dichiarata" if it else "Declared installation")], language)
    guide += ["I comandi sono citati dalle fonti: non sono stati eseguiti né garantiti aggiornati. Controlla piattaforma, percorsi, dipendenze, versioni e tipo di artefatto prima di usarli." if it else "Commands are quoted from sources, not executed or guaranteed current. Check platform, paths, dependencies, versions and artifact type before using them.", ""]
    quality = start("DOCUMENT-QUALITY — Copertura e controlli" if it else "DOCUMENT-QUALITY — Coverage and checks")
    quality += ["```json", json.dumps(model["coverage"], ensure_ascii=False, indent=2), "```", "", "## Fonti / Sources", ""]
    for src in model["sources"]:
        quality += [f"- {src['path']}: extraction={src['extraction']}; interpretation={src['interpretation']}; copy_of={src.get('copy_of')}"]
        quality += ["  - " + n for n in src["limitations"]]
    quality += ["", "## Controlli: deterministici, euristici e umani" if it else "## Checks: deterministic / heuristic / manual", "", "I controlli indicano cosa rivedere; non assegnano un voto al prodotto. Semantica del dominio e correttezza UML richiedono revisione." if it else "Checks identify review work, not a product quality score. No automated language or UML correctness certification.", ""]
    for control in model.get("quality_controls", []):
        quality += ["- " + control["id"] + " · " + control["method"] + " · " + control["status"] + ": " + control["scope"]]
    quality += [""]
    for issue in model["issues"]:
        quality += ["### " + issue["kind"] + " · " + issue.get("method", "review"), "", clean(issue.get("meaning", issue.get("text", issue.get("record_ref")))), "", sources(issue), ""]
    for doc in (rad, sdd, odd):
        doc += ["## Tracciabilità / Traceability", "", "[Collegamenti nei due sensi](TRACEABILITY.md). Un collegamento non prova il soddisfacimento." if it else "[Links in both directions](TRACEABILITY.md). A link does not prove satisfaction.", ""]
    quality += ["", "## Open questions", ""] + ["- " + u for u in model["unknowns"]]
    review = model.get("review_state")
    if review:
        quality += ["", "## User review", "", "```json", json.dumps(review, ensure_ascii=False, indent=2), "```"]
    observed_rad, observed_sdd, observed_odd = observed_design(model, it)
    rad += observed_rad; sdd += observed_sdd; odd += observed_odd
    _ = spec  # Installed section contract is deliberately read by every regeneration.
    rendered = {name: "\n".join(group_missing(lines, it)) + "\n" for name, lines in {"RAD.md": rad, "SDD.md": sdd, "ODD.md": odd, "TESTING.md": testing,
                "TP.md": tp, "TCS.md": tcs, "TIR.md": tir, "TSR.md": tsr, "GUIDE.md": guide, "DOCUMENT-QUALITY.md": quality}.items()}
    rendered['OVERVIEW.md'] = overview(model, it)
    rendered['TRACEABILITY.md'] = traceability(model, it)
    return rendered


def re_safe(name):
    return "".join(c for c in name if c.isalnum() or c in "_ .")
