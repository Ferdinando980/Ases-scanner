# Leggere le proposte sui pattern

Il motore principale contiene 22 regole per 16 famiglie, includendo architettura,
pattern di progettazione e l'idioma Factory. Non copre l'intero catalogo GoF.
Il catalogo disponibile è consultabile anche nel quadro della UI. Il modello
linguistico opzionale non produce queste proposte: derivano da analisi statica.

`pattern-opportunities/4` conserva questi criteri di precisione:

- Strategy, State e Command: conta i rami diretti dei costrutti sintattici Java,
  JavaScript/TypeScript e Python. Commenti, stringhe e switch annidati non si sommano
  al costrutto esterno. Un singolo switch resta HINT. Per una proposta richiede lo
  stesso selettore e insieme di casi in funzioni distinte dello stesso file: almeno
  quattro casi per Strategy, almeno tre per State/Command. La ripetizione sintattica
  non prova identità del comportamento o convenienza del refactoring.
- Observer: una normale chiamata `update()` non dimostra una notifica. Gli aggiornamenti
  richiedono nomi di destinatario compatibili con listener/subscriber/observer; restano
  euristiche da verificare. EventEmitter già riconosciuti costituiscono controevidenza.
  Commenti e contenuti letterali sono rimossi nei lettori supportati.
- Factory: richiede costruzioni alternative nei rami dello stesso callable e per
  lo stesso ruolo di ritorno/assegnazione. Costruttori in funzioni diverse non si
  sommano. Gli array numerici nativi JavaScript non sono prodotti applicativi da
  trasformare automaticamente in Factory. Duplicazione e variazione della politica
  di creazione restano da confermare.
- Una proposta basata su benchmark, esperimenti, esempi o `work` viene conservata come
  indizio debole, con pertinenza applicativa da confermare. Il perimetro dei sorgenti
  non viene ristretto di nascosto.
- Il classificatore `project-files/4` riconosce anche alberi espliciti di staging
  vendor con versione ed estrazione, ad esempio `vendor-update/lib-1.2.3/extracted`.
  Quei file restano inventariati come VENDORED e non guidano il codice applicativo.
  Una cartella `work` generica o un modulo chiamato `vendor_update_service` non basta.

I risultati con la stessa impronta stabile regola/file sono raggruppati conservando
le posizioni delle prove. Le schede iniziali mostrano una voce rappresentativa per
famiglia, privilegiando prima le possibili contraddizioni e poi le proposte, con il
numero di voci della famiglia. I risultati completi e gli indizi deboli restano
consultabili separatamente. Questi conteggi non misurano difetti o modifiche necessarie.

Prima di applicare una proposta verifica:

1. Il codice è parte del prodotto che vuoi modificare?
2. Il problema comporta duplicazione, variazione reale o un contratto condiviso?
3. Una soluzione diretta o già fornita dal framework risolve il problema?
4. Il pattern riduce il costo del cambiamento abbastanza da giustificare più struttura?

Confidence è una classificazione della regola, non una percentuale di accuratezza.
Le altre famiglie usano ancora euristiche diverse e non tutte hanno la stessa
copertura sintattica. C#/C++/Kotlin non ricevono suggerimenti di dispatch da questa
regola; un mancato risultato non prova l'assenza di opportunità. Riconoscimento
architetturale, ruolo di business e vantaggi del refactoring richiedono revisione.
Una nuova versione del metodo deve essere distinta da un problema risolto nel codice.

## Ragionamento sul progetto

La UI mostra anche valutazioni delle responsabilità: **problema da verificare →
prove nei sorgenti → beneficio atteso → soluzione già presente → alternativa più
semplice → quando lasciar perdere → domande prima di decidere**. La stessa
valutazione è esportata nel campo opzionale `design_review` e nella sezione
Design reasoning del documento ODD. È disponibile in italiano e inglese nella UI.

Il metodo `syntax-responsibilities/2` applica tre regole, aggiunte alle precedenti 19:

- **Service Layer, da approfondire:** almeno due funzioni nello stesso file
  producono risposte HTTP e coordinano chiamate con indizi di operazione applicativa
  e persistenza. Nomi come `query`, `ingest`, `save` e `persist` sono segnali,
  non dimostrazioni del ruolo di business. Le funzioni helper sono collegate solo
  nel caso Python, quando un import relativo esplicito `from . import modulo` conduce
  a una definizione unica fra i sorgenti ammessi. Negli altri linguaggi questa
  regola conserva le posizioni delle chiamate senza inventarne la destinazione.
  Riutilizzo tra interfacce e duplicazione del caso
  d'uso restano da verificare; estrarre una funzione può bastare.
- **Strategy, da approfondire:** una condizione su provider/backend seleziona
  chiamate a metodi diversi sullo stesso destinatario sintattico con lo stesso ruolo di
  assegnazione o ritorno. È un'ipotesi: contratti, errori, effetti e frequenza dei
  cambiamenti potrebbero rendere preferibile la condizione attuale.
- **Provider Registry, già presente:** chiamate esplicite a `register_provider` o `registerProvider`
  con almeno due chiavi letterali distinte e loader locali. La registrazione
  osservata suggerisce di verificare il riuso; non prova caricamento a runtime,
  un Service Layer o algoritmi intercambiabili. Le chiavi devono appartenere
  allo stesso ricevitore sintattico e alla stessa funzione di registrazione:
  registri e funzioni diverse non si sommano. Non è un nuovo pattern GoF.

La versione attuale riguarda Python, JavaScript/TypeScript e Java sintatticamente
leggibili, fino a 2 MiB e 100.000 nodi per file. Non esegue i sorgenti. Usa AST Python
e i parser Tree-sitter già installati, senza nuove dipendenze.
Gli altri linguaggi continuano a ricevere le regole
precedenti; assenza di valutazioni non significa architettura adeguata. Un'ipotesi
resta HINT e non aumenta il conteggio delle proposte OPPORTUNITY. I benefici non
sono misurati. Nessun modello linguistico è necessario per queste valutazioni.

La verifica del comportamento e del contratto di esportazione è in
`runtime/tests/test_design_review.py`; i limiti e gli indizi negativi fanno parte
del risultato, non sono nascosti dietro il nome del pattern.

## Copertura delle valutazioni

La voce «Dove è stato applicato il ragionamento?» distingue i file su cui sono
state applicate le regole limitate, quelli non valutati e i linguaggi non
supportati da questo specifico metodo. La classificazione riguarda i sorgenti
ammessi al perimetro, non dipendenze o file esclusi. Un file Python può non
ricevere valutazioni perché non contiene segnali pertinenti: non diventa per
questo un'architettura approvata.

Nel feed il campo opzionale `design_review_coverage` conserva per ogni file metodo,
stato, motivo e scope: `ANALYZED` significa regole applicate, `UNKNOWN` indica
lettura/sintassi non disponibile o un limite superato; `NOT_SUPPORTED` indica
un linguaggio non coperto. Non sostituisce la copertura delle altre analisi ASES.
L'ODD mantiene gli stessi conteggi anche dopo la rigenerazione dallo snapshot.
Gli snapshot precedenti senza questo campo mostrano «copertura non registrata»;
non si inventa una misura retroattiva dai suggerimenti presenti o assenti.

`runtime/tests/fixtures/design-review-cases.json` contiene dodici casi controllati
con segnali attesi e segnalazioni da non produrre. Il confronto è eseguito da
`test_design_review_coverage.py`: è una regressione dichiarata su sintassi e nomi,
non una stima indipendente dell'accuratezza architetturale su progetti reali.

Le dodici fixture aggiuntive in `design-review-syntax-cases.json` esercitano le tre
regole e gli handler già deleganti su JavaScript, TypeScript e Java. Altri test
controllano commenti/stringhe, nomi riassegnati o nascosti, registrazioni separate,
chiavi duplicate, output differenti, assegnazioni composte e budget sintattici.

## Forme supportate e limiti nei nuovi linguaggi

- Gli handler JS/TS devono contenere chiamate con indizi applicativi e di
  persistenza, oltre a uscite HTTP esplicite su `res`, `response`, `reply` o `h`.
  Sono ammesse catene semplici come `res.status(200).json(...)`. In Java è ammessa
  anche una risposta esplicita `ResponseEntity.ok(...)` o `status(...).body(...)`.
  Il tipo effettivo del ricevitore e la funzione dei metodi restano da verificare.
- Strategy considera i rami diretti di `if/else` che restituiscono una chiamata
  oppure assegnano allo stesso identificatore, anche con `await` in JS/TS.
  Dichiarazioni locali ai due rami e assegnazioni composte non provano un output
  condiviso. Non è un'analisi generale di ternari, alias o dispatch dinamico.
- In JS/TS i loader devono essere funzioni uniche a livello di modulo,
  dichiarate o assegnate a variabili, senza riassegnazioni riconosciute o
  mascheramenti locali. Non si risolvono loader importati.
- In Java si riconoscono riferimenti `this::loader` o `NomeClasse::loader` a
  metodi unici della classe dichiarata. Overload, classi anonime e riferimenti
  esterni non vengono risolti da questa regola. Non si verifica il contratto
  funzionale o la validità della compilazione.

Gli snapshot del metodo precedente `python-responsibilities/1` restano leggibili
e indicano la loro copertura Python originale; una rigenerazione non applica
retroattivamente il nuovo supporto. Il nuovo schema accetta entrambi i metodi.
Un consumer che fissa i valori del profilo deve aggiornare il proprio schema
prima di leggere il nuovo profilo, senza scambiare il cambio di metodo per una
correzione del progetto analizzato.
