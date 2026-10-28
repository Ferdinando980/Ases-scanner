<p align="center">🔎</p>

<h1 align="center">ASES</h1>

<p align="center">Architecture &amp; Software Evidence Scanner<br/>Sviluppare con un metodo. Capire con le prove.</p>

<p align="center"><a href="README.md">English</a> · <b>Italiano</b></p>

ASES aiuta a capire un progetto esistente e a svilupparlo con un metodo: legge
codice e documentazione, prepara una spiegazione navigabile e collega ciò che dice
alle fonti. La scansione normale funziona sul tuo computer, senza modelli o chiavi
API. Il codice viene letto, mai avviato. Già abbastanza software si avvia da solo.

**Runtime attuale: 1.13.1, sperimentale.** Parti dalla UI; i comandi e i contratti
per le integrazioni sono più sotto. [English](README.md) ·
[Guida alla UI](docs/DESK.it.md) · [Documenti](docs/DOCUMENTS.it.md) ·
[Misure e limiti](docs/ACCURACY.md).

## Perché l'ho costruito

Alcuni progetti iniziano con un'idea e nessuna riga di codice. Altri arrivano con molto codice e un README avvistato per l'ultima volta tre refactoring fa. Volevo un modo utile di lavorare partendo da entrambe le situazioni.

ASES unisce un **kit di ingegneria del software** e uno **scanner Python per comprendere software esistente**. Il kit dà agli assistenti di programmazione un metodo per requisiti, progettazione, implementazione, test e documentazione mantenuta. Lo scanner percorre la direzione inversa: dal codice ricostruisce struttura, relazioni e documentazione supportate dalle fonti, conservando le prove. Funziona localmente senza un LLM o una chiave API.

Le due parti si incontrano nel lavoro quotidiano: capire cosa esiste, decidere cosa cambiare, implementarlo e verificare che codice, test e documenti continuino a raccontare la stessa storia. Possibilmente senza creare uno Strategy Factory Manager per correggere un `if` di due righe.

## Cosa ci trovi oggi

| Ti serve… | ASES ti prepara… |
|---|---|
| Capire un repository | Riepilogo, mappa del codice, route e collegamenti alle righe che sostengono l'analisi |
| Recuperare la documentazione | Requisiti originali, comportamenti ricostruiti, RAD, SDD, ODD e documenti di test, con provenienza e parti da completare |
| Decidere cosa migliorare | Pattern osservati e proposte motivate: problema, prove, alternative semplici e ragioni per lasciar perdere |
| Lavorare sui bisogni del progetto | Operazioni e domande, annotazioni e adozione esplicita dei requisiti, mantenute separate dalle fonti originali |
| Capire cosa è cambiato | Confronti fra snapshot e impatto sui documenti e sulle revisioni |
| Aggiungere una lettura locale | Provider LLM o GLiNER2 facoltativi; producono ipotesi citate da valutare |
| Sviluppare da zero o continuare un progetto | Metodo, istruzioni per gli assistenti e template per requisiti, design, test e tracciabilità |

La 1.13.1 amplia la lettura di ReqView, ARFF e HTML, il riconoscimento dei vincoli
e l'analisi delle funzioni interne o dichiarate dentro condizioni. Mantiene visibili
le incertezze e distingue un corpo letto senza risultati utili da uno non analizzato.
Il conteggio non cresce aggiungendo requisiti immaginari: sarebbe un modo piuttosto
creativo di migliorare le statistiche.

## Provalo dal browser

Con Python 3.11 o successivo, dalla radice del repository:

```console
python -m venv .venv
```

Attiva l'ambiente con `.\.venv\Scripts\Activate.ps1` in PowerShell oppure
`source .venv/bin/activate` su macOS/Linux. Poi:

```console
python -m pip install -e "./runtime[documents]"
ases ui
```

Puoi anche aprire la UI con una cartella già selezionata:
`ases ui /percorso/del/progetto`. L'extra `documents` abilita i PDF testuali;
per il solo scanner basta `python -m pip install -e ./runtime`. Se un vecchio
comando `ases` resta nel PATH, usa `python -m ases --version` e `python -m ases ui`
con il Python dell'ambiente appena preparato. Interfaccia e processo di scansione
devono usare la stessa installazione: il vintage lo lasciamo ai mobili.

1. In **Nuova analisi**, scegli una cartella oppure incolla l’URL HTTPS di un repository pubblico.
2. Avvia: vedi la fase effettiva e il tempo trascorso; puoi interrompere. Le opzioni permettono di escludere cartelle senza modificare il progetto.
3. Apri **Risultati** per il riepilogo e i punti da verificare. **Mappa del codice** collega i simboli alle prove nei sorgenti.
4. In **Documenti**, parti dalle **Operazioni e domande**: leggi cosa fa il codice e completa ciò che conosci. Il RAD distingue requisiti dichiarati e comportamenti ricostruiti; SDD e ODD descrivono architettura, firme e contratti. Puoi seguire le fonti e annotare le voci. **Pacchetto completo** conserva documenti e revisioni in uno ZIP riapribile. Può contenere testi estratti, frammenti di codice, percorsi e metadati: controllalo prima di condividerlo. **Rapporto ridotto** contiene conteggi aggregati e omissioni, senza testi, percorsi, sorgenti o note; non si può riaprire come analisi e i conteggi possono comunque rivelare caratteristiche del progetto.

Per riaprire un pacchetto completo, estrailo e usa **Apri analisi salvata**. L’apertura mostra una sola fase e non ripete la scansione. Cambiare la lingua dell’interfaccia localizza navigazione e spiegazioni a schermo, ma non traduce i Markdown già salvati. Per rigenerarli in inglese dallo snapshot, usa `ases documents ... --language en`, come descritto nella [guida ai documenti](docs/DOCUMENTS.it.md).

Niente caccia al tesoro fra dodici file per capire da dove cominciare. La UI è locale, in italiano e inglese, senza dipendenze frontend da installare. Git serve per i repository remoti. Le analisi non avviano il codice del progetto e non ne eseguono i test.

**Altri strumenti** raccoglie confronti, siti, artefatti, riconciliazione, audit,
esportazione, verifica delle capacità, misurazione sul corpus etichettato, lettura
con modello locale, confronto di osservazioni HTTP e pulizia degli output
riconosciuti. **Metodo e template** permette di compilare e scaricare i documenti
di sviluppo del kit. Requisiti e decisioni li fornisci tu: il codice non può
testimoniare cosa avevano in mente gli stakeholder.

Il progetto analizzato resta intatto. I report della UI sono temporanei: scaricali per conservarli. Un errore o un annullamento mantiene l’ultima analisi completata. Ctrl+C nel terminale chiude la sessione e rimuove i suoi file temporanei; chiudere soltanto la scheda non ferma il processo. La [guida all’interfaccia](docs/DESK.it.md) spiega ambiente, risultati, limiti e recupero dagli errori.

[![La UI ASES con riepilogo, prossimi passi e limiti espliciti.](docs/images/ases-desk.jpg)](docs/images/ases-desk.jpg)

Schermata reale sulla fixture pubblica `runtime/tests/fixture_spring`, usata per dimostrare il funzionamento. [Vedi anche il collegamento fra route, codice e prove](docs/images/ases-desk-evidence.jpg).

## Due parti, tre punti di partenza

| Situazione | Cosa offre ASES | Come si usa |
|---|---|---|
| Nuovo progetto | Requisiti, scenari, decisioni di design, risultati attesi dei test e tracciabilità | L'agente segue standard, skill selezionate e template |
| Progetto esistente e documentato | Analisi dell'impatto, controlli di coerenza e aggiornamento dei materiali interessati | L'agente confronta codice e documentazione prima di modificarli |
| Progetto esistente con documentazione mancante o inaffidabile | Inventario, evidenze strutturali, modelli e documentazione ricostruita | Lo scanner produce una baseline; l'agente valuta incertezze e materiale recuperato |

**Metodo e scanner hanno responsabilità distinte.** Il metodo comprende istruzioni, gate, skill, adapter e template. Lo scanner è software eseguibile. L'installazione Python installa lo scanner; per usare il metodo bisogna configurare anche l'agente con il kit. Il pacchetto non intervista autonomamente gli stakeholder e non implementa un'applicazione a partire da una frase.

## Sviluppare con il metodo

Il percorso è:

```text
intenzione → requisiti → analisi → system design → object design
           → implementazione → test → risultati e tracciabilità
```

[STANDARD.md](STANDARD.md) descrive il metodo; [il router](orchestrator/TASK-ROUTER.md) seleziona procedure e rigore. Una correzione piccola può restare `LEAN`; una funzionalità significativa usa `STANDARD`; interventi architetturali o sensibili per la sicurezza possono richiedere materiali `FORMAL`. La documentazione cambia in base all'impatto: rinominare una variabile non dovrebbe convocare un consiglio di amministrazione.

Il kit comprende:

- validazione dei requisiti, analisi dell'impatto e verifica della coerenza;
- progettazione del sistema e degli oggetti, decisioni di riuso e contratti delle API;
- Simplicity Gate prima di aggiungere pattern o astrazioni;
- progettazione dei test con risultati attesi espliciti, regressioni e gestione degli incidenti;
- collegamenti bidirezionali fra requisiti, decisioni, codice, test e risultati;
- template per SOW, RAD, SDD, ODD, decisioni di design e documenti di test TP/TCS/TIR/TSR;
- adapter di istruzioni per diversi assistenti di programmazione.

Il metodo deriva anche da materiale universitario di ingegneria del software: fonti e rispettiva autorità sono dichiarate nella [mappa delle fonti](sources/SOURCE-MAP.md). I template danno una struttura; non rendono utile un documento vuoto per il solo fatto di esistere.

Per adottarlo, colloca il kit nella directory `.ases` del progetto e integra l'adapter adatto nelle istruzioni dell'agente, conservando quelle già presenti. La [guida al metodo](docs/ENGINEERING-WORKFLOW.md) indica file, configurazione ed esempio operativo. Il companion storico `scripts/ases.py` offre suggerimenti di classificazione e controlli sulla presenza dei file; il ragionamento resta responsabilità dell'agente.

## Requisiti: frasi, non una collezione di sigle

Se il progetto ha già specifiche, ASES recupera le dichiarazioni disponibili: ID, testo e fonte, più attori, priorità e soglie dove riesce a separarli. Legge anche PDF testuali, fogli Excel, Word e documentazione HTML. Un file trovato ma non leggibile viene segnalato: non passa automaticamente per «documentazione analizzata».

Sono supportate anche strutture ReqView `.reqw`, ARFF, liste di requisiti
JSON/YAML e forme riconosciute in Markdown e prosa. L'importazione conserva le
parole originali, gli ID e i tipi dichiarati; la classificazione automatica di una
frase senza tipo resta una proposta. «Il sistema deve rispondere entro due
secondi» esprime un vincolo; «il sistema deve mostrare il tempo di risposta»
descrive una funzione. La parola *tempo*, da sola, non decide la categoria.

Nel **reverse engineering**, parte invece dai flussi supportati del codice: richiesta o chiamata pubblica, condizioni, risultati, errori e chiamate con possibili effetti. Da questi costruisce frasi di comportamento e le collega alle prove. Per esempio, può ricostruire che un handler controlla un titolo, dichiara un errore quando manca e prepara una risposta con il campo `id`. Non conclude che un ordine sia stato davvero salvato soltanto perché un metodo si chiama `save`.

In **Documenti** puoi scegliere **Requisiti** per le dichiarazioni originali oppure **Requisiti ricostruiti dal codice** per questa interpretazione. Il RAD conserva entrambe le prospettive. L’ODD aggiunge firme, contratti disponibili e diagrammi; i documenti dei test distinguono definizioni, proposte e risultati importati. Le revisioni restano separate dalle fonti, vengono conservate nel browser per il progetto e incluse nel pacchetto completo; se una nuova scansione cambia il record, il conflitto resta visibile da rivedere.

Le **Operazioni e domande** raggruppano ingressi con gli stessi handler e ti chiedono ciò che il codice non può sapere. Puoi dare un nome comprensibile al flusso, dichiarare il bisogno e indicare autore, ambito e criterio di accettazione. Confermare una lettura non adotta automaticamente un requisito; adottarlo non significa averlo verificato. Il RAD tiene separati questi contributi dalle specifiche originali. Il timbro «fatto» non è incluso nel pulsante Salva.

### Come leggere i numeri senza litigarci

| Se trovi… | Vuol dire… |
|---|---|
| Zero requisiti documentati | Nessuna dichiarazione isolata nelle fonti e forme lette. Non significa che il progetto non abbia bisogni o documentazione |
| Operazioni ricostruite | Gruppi tecnici di ingressi: non sono automaticamente funzionalità dell'utente né requisiti approvati |
| Requisiti ricostruiti dal codice | Frasi su condizioni, risultati, errori e possibili chiamate osservabili staticamente; vanno confermate nel contesto |
| Funzione interna | Analisi del suo corpo. La sua presenza non stabilisce che un utente possa chiamarla |
| Dichiarazione condizionale | Il corpo esiste nel sorgente; disponibilità e collegamenti dipendono da condizioni che ASES non risolve completamente |
| Corpo analizzato senza fatti ammessi | Il metodo ha letto il corpo senza ricostruire risultati nelle categorie coperte. Non prova che la funzione sia inutile o senza effetti |
| Test definiti, test nel codice o risultati importati | Conteggi con origini diverse. ASES non ha eseguito quei test |

Per leggere i documenti, comincia dalla panoramica e dalle operazioni; apri il
documento completo quando ti serve il dettaglio:

| Documento | La domanda a cui aiuta a rispondere |
|---|---|
| Panoramica (`OVERVIEW.md`) | Che progetto è, cosa è stato recuperato e dove conviene guardare? |
| RAD | Quali requisiti sono dichiarati, quali comportamenti sono ricostruiti e cosa resta da chiedere? |
| SDD | Come sono organizzati sottosistemi, dipendenze e interazioni ricostruibili? |
| ODD | Quali oggetti, interfacce, firme e contratti emergono? Quali decisioni di design meritano una verifica? |
| TP, TCS, TIR, TSR | Quali test sono previsti, definiti, proposti o accompagnati da risultati importati? |
| Tracciabilità e qualità | Da quale fonte viene ogni voce, cosa è collegato e quali parti sono parziali o sconosciute? |

Una sezione senza prove resta da completare. Anche un documento con un bel titolo
ha il diritto di dire «qui non lo so».

L’interpretazione è statica e parziale, non una lettura universale del dominio. Dispatch dinamico, flussi Java complessi, diagrammi raster, intento degli stakeholder e correttezza runtime richiedono ancora una verifica. Il software può ricostruire una mappa; la telepatia resta fuori dalle dipendenze. La [guida ai documenti](docs/DOCUMENTS.it.md) spiega cosa viene letto, cosa viene inferito e come rigenerare il pacchetto.

## Comprendere codice esistente con lo scanner

[![Pipeline dello scanner: classificare le fonti, estrarre sintassi, ricostruire relazioni statiche, spiegare i finding e confrontare snapshot.](docs/images/ases-pipeline.png)](docs/images/ases-pipeline.svg)

Lo scanner separa sorgenti del progetto e test da file generati, librerie distribuite, tooling e documentazione. Estrae fatti, costruisce un grafo, ricostruisce le relazioni supportate ed esporta documenti leggibili e dati generici. Codice, import e script di build vengono letti come dati; l'applicazione analizzata non viene eseguita.

Puoi usarlo per:

- inventariare moduli, classi, funzioni, interfacce, persistenza e dichiarazioni di test;
- ricostruire route, handler, chiamate e percorsi limitati verso datastore o confini API nelle forme supportate;
- ispezionare segnali locali di controllo/sessione e collegamenti statici ai test;
- rivedere architettura osservata, pattern, conformità e candidati motivati al refactoring;
- analizzare componenti, template, servizi, richieste letterali e corrispondenze frontend/backend supportate;
- generare una baseline documentata e confrontare snapshot successivi senza scambiare uno spostamento di riga per una nuova applicazione.

| Area | Estrazione attuale | Confine pratico |
|---|---|---|
| JavaScript / TypeScript | Parsing Tree-sitter inerte di `.js/.jsx/.mjs/.cjs/.ts/.tsx/.mts/.cts`; binding lessicali, moduli letterali, re-export, forme CommonJS, callback e costrutti Express/NestJS selezionati | Alias del compilatore, dispatch calcolato e comportamento di ordine superiore restano incompleti |
| Python | Dichiarazioni AST, import, collegamenti euristici di chiamata, decorator web selezionati e indizi ORM | Risoluzione delle chiamate parziale; non riproduce la semantica runtime dei binding Python |
| Java | Estrazione euristica di tipi, membri e dipendenze, con annotazioni Spring selezionate | Non è un compilatore Java; mapping delle route servlet e dispatch degli overload non vengono ricostruiti in modo completo |
| Frontend | Struttura Angular/React selezionata, template, HttpClient Angular tipizzato, client importati ammessi, fetch ambientale e form HTML letterali | Grammatiche dei template parziali; script Vue/Svelte incorporati e rendering runtime non sono analizzati esaustivamente |
| Altri linguaggi inventariati | Inventario e classificazione delle fonti dove riconosciuti | Essere nell'inventario non implica avere un parser strutturale |

Un import stabilisce un candidato. Una chiamata statica stabilisce un utilizzo ricostruito. Nessuno dei due dimostra traffico di rete. Un wrapper di `HttpClient` non costituisce automaticamente un'emergenza da design pattern.

### Le proposte sui pattern, in pratica

Il catalogo principale contiene **22 regole per 16 famiglie**, fra architettura,
pattern e idioma Factory. Le regole leggono segnali statici; non sfogliano l'intero
catalogo GoF cercando qualcosa da venderti. Il ragionamento aggiunge problema da
verificare, prove, beneficio atteso, soluzione già presente, alternativa più
semplice e condizioni in cui lasciare tutto com'è. Service Layer, Strategy e
Provider Registry sono fra le valutazioni supportate, con ruoli e limiti diversi.

**Proposta da valutare** può indicare una modifica possibile; una **struttura
osservata** descrive invece qualcosa già presente. Un'ipotesi sul comportamento
serve ancora a un altro scopo. Nessuna delle tre equivale a «bug trovato». Il
catalogo e la copertura sono visibili nella UI; [la guida](docs/PATTERN-REVIEW.md)
spiega criteri, controprove e quando un semplice `if` può andare benissimo.

## Finding con le prove allegate

[![Esempio illustrativo di finding ASES con prove, controprove, ruolo della fonte, confidence e interpretazione circoscritta.](docs/images/ases-output.png)](docs/images/ases-output.svg)

I risultati conservano prove, controprove, assunzioni, confidence categorica e limiti. Gli stati dei finding distinguono `OBSERVED`, `INFERRED`, `OPPORTUNITY`, `HINT`, `UNKNOWN`, `CONTRADICTED` e `SUPPRESSED`. Gli stati delle evidenze costituiscono un vocabolario separato. Relazioni statiche e percorsi pubblici restano inferiti, anche quando la sintassi di supporto è osservata direttamente.

Una classe chiamata `Factory` non merita una medaglia al design soltanto perché si è presentata. Un collegamento a un test non prova che sia stato eseguito o superato. Un controllo rilevato non dimostra protezione efficace. La conformità architetturale segue un'architettura prima osservata nel progetto, senza imporne una preferita a tutti.

Identità dell'entità, fingerprint del finding, identità dell'osservazione e identità dello snapshot hanno scopi diversi. La sola formattazione può cambiare posizioni e hash senza cambiare significato. Un'assenza richiede scope confrontabile e copertura del metodo pertinente: un risultato scomparso non è automaticamente un problema risolto.

## Eseguire una scansione

Il percorso più diretto è `ases ui`. Per installazione dettagliata, automazioni e uso da terminale:

<details>
<summary>Ambiente e comandi CLI</summary>

Dalla radice del repository, con Python 3.11 o successivo in un ambiente virtuale attivo:

```sh
python -m pip install -e ./runtime
ases --version

ases scan /percorso/del/progetto --out current.ases
ases scan https://github.com/OWNER/REPOSITORY --out remote.ases
```

Per creare l'ambiente usa `python -m venv .venv`, poi attivalo con `.\.venv\Scripts\Activate.ps1` in PowerShell oppure `source .venv/bin/activate` su macOS/Linux. Se PowerShell non consente l'attivazione, usa direttamente `.\.venv\Scripts\python.exe -m pip install -e ./runtime` e `.\.venv\Scripts\ases.exe`. Git serve per gli URL di repository; una scansione locale non lo richiede. Le dipendenze di sviluppo e test non sono necessarie per scansionare. Per verificare ASES stesso, vedi [TESTING.md](TESTING.md).

Scegli consapevolmente il perimetro dei sorgenti. ASES applica le esclusioni documentate e `.asesignore`; non interpreta automaticamente ogni cartella locale ignorata da Git come codice generato. Esperimenti e fixture temporanee possono richiedere un'esclusione esplicita.

Leggi il risultato in questo ordine:

1. Apri `current.ases/docs/SUMMARY.md` per il riepilogo da rivedere, poi `SYSTEM-OVERVIEW.md` per la struttura ricostruita.
2. Leggi `current.ases/docs/QUALITY.md` e gli unknown prima di giudicare ciò che manca.
3. Cerca il finding in `scanner-findings.json` o `docs/ODD.md`, incluse prove, assunzioni e confidence; controlla i sorgenti indicati.
4. Usa le query qui sotto per seguire una route o un simbolo. Esegui separatamente i test del progetto prima di decidere cosa cambiare.

Interroga lo snapshot salvato:

```sh
ases inspect current.ases
ases inspect current.ases --collection analysis_unknowns --limit 20
ases inspect current.ases --collection entities --select read --limit 20
ases trace current.ases "GET /users" --direction forward
ases trace current.ases read --direction backward
ases semantic-diff previous.ases current.ases
ases scan /percorso/del/progetto --out next.ases --baseline current.ases
```

Le query leggono le evidenze salvate senza riesaminare silenziosamente sorgenti mutabili. Il matching esatto per ID, nome o percorso espone le ambiguità. La paginazione della risposta è distinta dalla copertura dell'analisi. Le `entities` canoniche includono dichiarazioni che non compaiono nella proiezione legacy più piccola `components`: i due conteggi non sono equivalenti.

</details>

## Cosa restituisce

Una scansione dei sorgenti scrive:

| Output | Scopo |
|---|---|
| `docs/REPORT.it.md`, `REPORT.md` (UI) | Prima lettura in italiano e inglese, con struttura, route, verifiche e prossimo passo |
| `docs/SUMMARY.md`, `SYSTEM-OVERVIEW.md` | Guida alla revisione e panoramica ricostruita del sistema |
| `docs/OVERVIEW.md`, `GUIDE.md`, `DOCUMENT-QUALITY.md` | Panoramica dei documenti di ingegneria, percorso di lettura e copertura delle fonti |
| `docs/RAD.md`, `SDD.md`, `ODD.md` | Ricostruzione di comportamento, architettura e object design dalle evidenze di implementazione |
| `docs/TP.md`, `TCS.md`, `TIR.md`, `TSR.md`, `TRACEABILITY.md` | Piano e casi di test, incidenti, risultati disponibili e collegamenti navigabili |
| `docs/TESTING.md`, `TRACEABILITY.yaml`, `CONTROLS.yaml`, `QUALITY.md` | Baseline dei test, collegamenti, controlli osservati e limiti di qualità/copertura |
| `engineering-model.json`, `engineering-review.json` (quando presente) | Modello dei documenti e contributi dell'utente conservati separatamente |
| `semantic-model.yaml`, `manifest.json`, `validation.json` | Modello semantico, fingerprint di sorgenti/profilo e verifiche di coerenza |
| `scanner-findings.json` | Finding normalizzati, hint e risultati soppressi, feed **1.3** |
| `consumer-context.json` | Contesto legacy **1.5** |
| `consumer-context.v2.json` | Snapshot strutturale **2.0**: entità, osservazioni, relazioni normalizzate, mapping, hash e copertura esplicita |
| `fact-graph.json` | Dati per indagine interna; i consumer possono usare i contratti pubblici |

RAD/SDD/ODD ricostruiti descrivono l'implementazione osservata o inferita. Non recuperano una decisione mai documentata soltanto alzando la confidence. I documenti creati attraverso il metodo di sviluppo possono invece registrare requisiti e decisioni forniti e revisionati esplicitamente durante il lavoro.

### Come interpretare il risultato

| Cosa leggi | Significato | Cosa controllare dopo |
|---|---|---|
| `validation: PASS` | Il modello supera i controlli di coerenza/schema previsti | Non dimostra estrazione completa o correttezza dell'applicazione |
| `OBSERVED` / `INFERRED` | Un'osservazione supportata dai sorgenti / una ricostruzione basata sulle osservazioni | Leggi prove e assunzioni; una chiamata statica non dimostra esecuzione |
| `OPPORTUNITY` / `HINT` | Un candidato al refactoring / un indizio debole | Conferma il problema di design prima di cambiare codice; non sono verdetti |
| `CONTRADICTED` | Una regola dichiarata contrasta con le evidenze recuperate | Verifica che regola, prove e perimetro corrispondano al progetto attuale |
| `PARTIAL` / `UNKNOWN` | Il metodo pertinente è incompleto o non risponde entro questo perimetro | Un risultato mancante non prova un'assenza; copertura e confidence sono distinte |
| `SUPPRESSED` | Il risultato è stato escluso dalla politica di qualificazione/soppressione della regola | Leggi il motivo registrato, senza trattarlo come un finding confermato |
| `library_call` / `external_api_call` | Chiamata a una libreria importata / candidato statico di API-client ammesso | Nessuno dei due prova traffico di rete; gli effetti remoti di client sconosciuti restano irrisolti |
| Un elemento rimosso nel diff | Il secondo snapshot non recupera più quell'elemento | Conferma profili e copertura confrontabili; leggi `uncertain` prima di dichiararlo risolto |

La confidence è categorica (`low`, `medium`, `high`), non una probabilità calibrata. Il numero di test recuperati conta dichiarazioni e collegamenti: non è un'esecuzione dei test né una misura della copertura del codice. Una pagina con scritto PASS può meritare comunque una lettura molto attenta.

### Dove finiscono i file

`--out` seleziona una cartella persistente. Senza quel parametro, la scansione locale usa `.ases`; se contiene già il metodo di sviluppo o materiale non riconosciuto, i risultati vanno in `ases-scan.ases`. Il metodo installato viene conservato. Una destinazione esplicita già piena di materiale non riconosciuto viene rifiutata.

Per un URL di repository, l'output persistente predefinito è `<nome-repository>.ases` nella cartella corrente. Il checkout è temporaneo e viene ripulito dopo la scansione; il report rimane per poterlo leggere. Preferisci `--out` esplicito quando confronti esecuzioni. Non usare la stessa destinazione per baseline e nuova scansione: un output riconosciuto già presente viene sostituito.

Gli output generati hanno il marcatore `.ases-output`. Scansioni ripetute sostituiscono output riconosciuti; la pulizia richiede quel marcatore e rifiuta kit di sviluppo o radici di repository. Il semplice suffisso `.ases` non autorizza a cancellare una directory.

```sh
ases clean current.ases
ases clean --all
```

`--all` riguarda gli output riconosciuti direttamente nella cartella corrente. Conserva risultati persistenti quando servono come baseline; usa una directory temporanea per esperimenti usa e getta. Un benchmark dovrebbe lasciare misure, non uno strato archeologico nella cartella dei progetti.

## Siti, artefatti forniti e osservazioni importate

```sh
ases scan-site https://example.org --max-pages 5
ases scan-artifact supplied-dist --out artifact.ases
ases reconcile-artifact current.ases artifact.ases/artifact-snapshot.json
ases export current.ases --schema 2.0 --out context-v2.json
```

La modalità sito campiona HTML pubblico dalla stessa origine, rispetta `robots.txt` e registra pagine, form, riferimenti agli script e indizi sul framework. Non esegue JavaScript né invia form; architettura sorgente e comportamento renderizzato dal client restano non osservati.

La modalità artefatti legge bundle JS locali, source map e campi selezionati dei manifest entro limiti espliciti di file, byte e nodi. La correlazione distingue byte identici, asserzioni delle source map, ambiguità, discordanza e corrispondenza sconosciuta. L'eventuale input runtime deve essere già stato prodotto da un collector esterno. ASES non avvia build, non acquisisce runtime, non recupera map mancanti e non stabilisce equivalenza arbitraria fra simboli trasformati o verità di deployment. Uno script caricato non è una funzionalità eseguita.

## Modelli locali e osservazioni HTTP

La scansione normale usa parser e regole. Se vuoi aggiungere una lettura con un
modello, **Altri strumenti → Interpreta con un modello locale** offre due provider:

| Provider | Cosa serve | Cosa restituisce |
|---|---|---|
| `llm` | Un server chat locale già avviato, compatibile con llama.cpp, su indirizzo loopback numerico | Ipotesi su pochi estratti selezionati, con citazioni |
| `gliner2` | Runtime Python e modello già disponibili sul computer; almeno 4 GiB di RAM libera prima del caricamento | Proposte di classificazione collegate alle frasi originali, entro il budget di lettura |

ASES non scarica modelli. Le proposte finiscono in `INTERPRETATION.md` e
`interpretation.json`; non riscrivono requisiti o snapshot. Una citazione corretta
dimostra che la frase esiste, non che il modello l'abbia capita. Nel campione
misurato GLiNER2 ha classificato correttamente 44 frasi su 80: nessuna promozione
automatica a oracolo del progetto. [Configurazione, limiti e misure](docs/LOCAL-INTERPRETATION.md).

Per confrontare ciò che il codice suggerisce con richieste HTTP osservate,
**Confronta osservazioni HTTP** legge un file fornito da te. Puoi prepararlo con
`ases runtime-template current.ases --out observations.json`, completarlo con
raccolta, ambiente e osservazioni, poi usare
`ases runtime-check current.ases --observations observations.json --out correlation.json`.
Il confronto conserva identità dello snapshot, ambiguità e percorsi non ricostruiti.
ASES non avvia il server analizzato e non genera richieste per provarlo.

## Indipendente dai consumer

ASES offre procedure generiche di sviluppo ed evidenze strutturali. Altri strumenti possono usarle per documentazione, manutenzione, cybersecurity e assurance insieme ad altre fonti. Rischio, compliance, priorità organizzative e valutazioni finali sull'efficacia dei controlli spettano al consumer. ASES funziona autonomamente e non richiede il modello interno di un consumer o un lettore del grafo grezzo.

## Verifiche e stato attuale

La **1.13.1 è sperimentale** e richiede Python 3.11 o successivo. La
[CI pubblica](https://github.com/Ferdinando980/ases-scanner/actions/workflows/tests.yml)
verifica Windows, Ubuntu e macOS con Python 3.11 e 3.14. Le prove del pacchetto
installato e i dettagli degli ambienti sono nella [matrice](docs/SUPPORT.md).

Le misure correnti sono del 27 ottobre 2026. Sono regressioni su casi già noti,
con fonti ed etichette conservate; non una valutazione indipendente su progetti mai
visti:

| Prova | Risultato | Come leggerlo |
|---|---|---|
| Suite Windows/Python 3.14.7 | 775 superati, 1 saltato | Il caso sui collegamenti simbolici richiede permessi; non conta come superato |
| Pacchetto installato, Ubuntu/macOS × Python 3.11/3.14 | 776 superati per ambiente, zero saltati | Compatibilità e regressioni del pacchetto, non correttezza dei progetti analizzati |
| Riepiloghi dal codice, due campioni | 90/90 e 239/244 | Cinque corpi sono stati analizzati senza fatti ammessi; i fatti attesi sono recuperati con associazione per posizione. La sola ricerca per nome/percorso resta ambigua |
| Testo originale dei requisiti | 625/625 PROMISE, 110/110 ReqView | Conservazione del testo nelle fonti valutate |
| Categoria suggerita senza tipo nell'input | 537/625 PROMISE (85,92%), 110/110 ReqView | PROMISE include 48 errori e 40 astensioni nel totale; non è un punteggio generale di comprensione |

La classificazione migliora, ma sul campione PROMISE un caso peggiora rispetto
alla versione precedente: resta registrato. Conservare una categoria già dichiarata
e dedurla dalla frase sono prove diverse. La prosa arbitraria, le chiamate dinamiche
e il significato applicativo restano parziali; revisione indipendente e utilità per
gli utenti non sono ancora misurate. Per una beta generale il via libera resta
aperto. Tutti i denominatori e i limiti sono in [ACCURACY.md](docs/ACCURACY.md).
I numeri servono a capire dove fidarsi, non a mettere cinque stelline al proprio codice.

Puoi eseguire le verifiche di ASES seguendo [TESTING.md](TESTING.md), oppure usare
**Misura l’accuratezza su un corpus** nella UI con un corpus etichettato compatibile. I casi
sintetici forniti verificano regressioni controllate; un tuo corpus con aspettative
e perimetro espliciti misura quel perimetro, senza diventare automaticamente
una prova indipendente.

Parti dalla [guida al metodo](docs/ENGINEERING-WORKFLOW.md) per lo sviluppo, dalla [guida CLI](runtime/README.md) per i comandi e da [TESTING.md](TESTING.md) per riprodurre le verifiche. [Terminologia delle evidenze](EPISTEMOLOGY.md), [regole dei pattern](PATTERN-RULES.md) e [contratti dei consumer](integrations/CONSUMER-CONTRACT.md) chiariscono interpretazione e integrazione. Dispatch dinamico, middleware globali, route servlet, client/bus personalizzati ed esecuzione runtime restano limiti dei rispettivi metodi. Zero opportunità speculative è un risultato valido.

## Licenza

Copyright © 2026 Ferdinando Gregorio Fernandez. Tutti i diritti riservati. Il codice è visibile per valutazione professionale; riuso, redistribuzione e opere derivate non sono consentiti. Vedi [LICENSE](LICENSE). Le dipendenze conservano i propri termini in [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
