# Leggere e costruire i documenti

Per la lettura opzionale con modello locale e il confronto di osservazioni HTTP,
vedi [Lettura locale e osservazioni](LOCAL-INTERPRETATION.md). Le ipotesi generate
restano separate dai requisiti e dalle prove della scansione.

[English](DOCUMENTS.md) · Italiano

Avvia `ases ui`, analizza il progetto e apri **Documenti**. La scansione prepara il
rapporto, RAD, SDD, ODD, piano/specifiche/incidenti/risultati dei test e guida alle
istruzioni disponibili. Le parti senza prove restano da completare: il titolo di
una sezione non è una scusa per inventare il contenuto.

![ASES — Esempio sintetico: requisito adottato esplicitamente con autore, ambito, criterio di accettazione e soddisfacimento non verificato, separato dalle specifiche originali.](images/ases-documents.png)

## Due modi diversi di arrivare a una frase

Nel riepilogo, **zero requisiti documentati** significa zero dichiarazioni isolate
nei formati riconosciuti (ID RF/RNF, lista strutturata o frasi esplicite come «Il sistema deve…»), non assenza di bisogni o di
documentazione. La prosa libera è interpretata solo in parte. I gruppi tecnici di
ingressi non contano le funzionalità dell’utente; test nel codice, casi documentati
e risultati importati hanno conteggi separati. JSON/YAML di esperimenti o altri
dialetti senza una lista `requirements` restano inventariati e indicati come non
supportati: non vengono letti come specifiche in prosa.

Per gli HTML riconosciuti, ASES conserva anche gli ID originali di righe marcate
esplicitamente come requisiti e di intestazioni formali seguite da un obbligo.
Se la fonte non dichiara il tipo, compare fra i **requisiti con tipo non dichiarato**;
una riga senza testo resta incompleta. Titolo e stato appartengono alla fonte:
«Active» non significa che il requisito sia soddisfatto.

I riferimenti padre/figlio conservano ruolo, ID e posizione originali. Un ID presente
può essere aperto per il confronto anche quando il documento collegato non è stato
identificato con certezza. Indici, esempi e codice non creano da soli nuovi requisiti;
il codice incluso nel testo di un requisito resta testo, senza essere eseguito.
Questo supporto riguarda strutture precise: confronta sempre un requisito noto con
la fonte prima di usare i conteggi come misura della documentazione completa.

**Dichiarato nel documento** significa che il testo proviene da una specifica
leggibile. Conserva ID, formulazione originale, pagina/cella/riga e hash della
fonte. Attori, priorità, soglie e oracoli possono essere parziali. Le dichiarazioni
discordanti dello stesso ID restano consultabili; ASES non sceglie quale approvare.

Per una frase senza ID, ASES conserva le parole e la posizione originali e mostra
«Requisito senza ID dichiarato». La chiave interna è generata: non è un codice
attribuito all’autore. La classificazione funzionale/non funzionale va rivista;
esempi Markdown, etichette e istruzioni di installazione non diventano requisiti.
Se il percorso della fonte indica un archivio, l’applicabilità alla versione attuale
è segnalata come sconosciuta. Copie in file diversi conservano la loro provenienza:
il conteggio delle dichiarazioni non misura i bisogni attuali distinti del progetto.
Le tabelle HTTP Python a prefisso riconosciute compaiono come `/percorso/*`:
sono candidati statici, eventualmente oscurati da altre route o condizioni.

**Ricostruito dal codice — da confermare** significa che ASES interpreta un flusso
supportato dell’implementazione. Parte da handler HTTP o interfacce pubbliche,
legge condizioni, ritorni, errori e chiamate e produce una frase collegata alle
prove. Distingue i risultati esterni dai ritorni degli helper. Le chiamate vengono
seguite entro limiti espliciti; nomi come `save`, `authorize` o `validate` da soli
non provano persistenza, autorizzazione effettiva o validazione completa.

Con server Python `http.server`, ASES riconosce alcune tabelle di dispatch esatte,
anche se la classe handler nasce in una factory. Il collegamento è un’inferenza
statica citata, non una richiesta HTTP eseguita. Alcune liste letterali di prefissi
sono supportate; precedenza, condizioni e registrazione dinamica restano parziali.
Quando riconosce ingressi HTTP, il riepilogo parte da questi;
in assenza di route usa le API pubbliche. Se queste superano il limite, dà precedenza
ai percorsi applicativi e distribuisce il budget fra file prima degli alberi di
benchmark, esempi e lavoro sperimentale. Tutte le dichiarazioni restano nell’inventario.
Anche la lettura dei corpi dà precedenza ai file degli handler e ai file collegati,
prima di consumare il budget sui benchmark. I corpi omessi restano indicati nella copertura.

Questa interpretazione non ricostruisce automaticamente il bisogno originale di
business. Non è un motore universale di comprensione del codice: dispatch dinamico,
comportamento di librerie esterne, concorrenza ed eccezioni transitive possono
restare sconosciuti. Java ha una ricostruzione dei corpi più limitata di Python e
JS/TS. Gli invarianti dichiarati nei commenti non sono proprietà dimostrate.

Nei flussi supportati, un `return` interrompe la lettura del percorso: il codice
dopo non viene promosso a comportamento del sistema. Il ramo successivo a un’uscita
anticipata conserva la sua condizione; chiamate con `and`/`or` o `&&`/`||` conservano
il vincolo di esecuzione. ASES legge anche risposte HTTP supportate senza `return`
e ritorni condizionali. Un `return`, insomma, non è un consiglio arredativo.

Quando loop, dispatch delle eccezioni, override condizionali in `finally` o budget
di analisi impediscono una ricostruzione completa, apri **Limiti di questo flusso**.
Gli errori di un helper collegato restano dichiarazioni del componente: ASES non
li trasforma automaticamente in errori propagati all’ingresso. Un aggiornamento
del metodo può cambiare l’interpretazione e richiedere di ricontrollare una nota.

## Dal requisito alla prova

La vista iniziale **Operazioni e domande** raccoglie gli ingressi che hanno lo stesso
insieme esplicito di handler. Condividere soltanto un helper non unisce due funzioni.
Apri una scheda per leggere la spiegazione, le chiamate e le domande su obiettivo,
attore e verifica. Puoi dare un nome leggibile all'operazione e rispondere: il
contesto resta una tua dichiarazione, separata dai fatti del codice.

In **Requisiti ricostruiti dal codice**, **Le affermazioni e le loro prove** porta
dalla singola frase alla riga che la sostiene. Le espressioni originali restano nei
dettagli. Un percorso parziale non diventa completo perché è scritto meglio.

1. Scegli **Requisiti** oppure **Requisiti ricostruiti dal codice**. Nell’elenco
   leggi la frase, non soltanto la sigla.
2. Apri la voce: controlla condizioni, risultati, autorità e fonti. I riferimenti
   espliciti portano alle API o ai test quando il collegamento è recuperabile.
3. Apri il codice o l’estratto salvato di pagina/cella. Una fonte non letta limita
   le conclusioni anche quando un riferimento non viene trovato.
4. Annota, conferma o segnala una correzione. La nota non riscrive la fonte.
5. Scarica il pacchetto completo. Le annotazioni sono in `engineering-review.json`, separate
   da `engineering-model.json`. Con una nuova scansione, una nota su un record
   cambiato resta conservata come conflitto da rivedere.

La copia nel browser dipende da origine/porta e dati locali del browser. Lo ZIP
è la copia da conservare e riaprire; cancellare i dati del browser può eliminare
le annotazioni non esportate. I report della sessione sono temporanei.

## Scrivere o adottare un requisito

In **Operazioni e domande** o **Requisiti inseriti o adottati**, apri **Scrivi un nuovo
requisito**. Indica ID univoco, tipo funzionale/non funzionale, testo, autore, ambito
e criterio di accettazione indipendente. Anche un progetto senza codice può
contenere requisiti inseriti da una persona; ASES non inventa l'implementazione.

Per partire da una ricostruzione, apri **Adotta esplicitamente come requisito** e
scrivi il bisogno da adottare. Confermare una lettura, rispondere a una domanda e
adottare un requisito sono azioni diverse. Il requisito ha autorità umana e il suo
soddisfacimento resta **non verificato**. Compare nel RAD separatamente dalle
specifiche originali; puoi modificarne i campi dalla scheda.

Le nuove azioni usano revisioni `ases-engineering-review/1.1`; le annotazioni 1.0
restano leggibili. Conserva modello e revisione nell'esportazione: il modello di
base rimane immutabile e la revisione conserva le tue dichiarazioni. Se il candidato
cambia o scompare, il requisito resta con supporto **da ricontrollare**; il vecchio
contesto non viene applicato silenziosamente alla nuova ricostruzione. Il confronto
documentale legge anche requisiti e contesto della revisione salvata.

## Che cosa viene letto

| Fonte | Recupero | Limite |
|---|---|---|
| Markdown, testo, YAML/JSON | Testo e record espliciti di requisito | Prosa libera e formati personalizzati restano parziali |
| PDF | Pagine testuali e tabelle, con intestazioni ripetute/continuate | Niente OCR o comprensione automatica dei diagrammi; cifratura ed errori sono segnalati |
| XLSX | Tutti i fogli e le celle popolate, formule e cache distinte, riferimenti interni semplici | Nessuna esecuzione di formule o macro; link esterni/riferimenti calcolati possono restare irrisolti |
| DOCX | Paragrafi e testo delle tabelle | Layout, disegni e semantica visiva non interpretati |
| HTML/Javadoc | Testo e firme statiche disponibili | Nessuno script o generatore viene eseguito; una firma documentata può essere obsoleta |
| JUnit/JaCoCo XML e righe di report XLSX | Risultati dichiarati, date/scope disponibili e contatori | Risultati importati, non test eseguiti ora; commit/ambiente spesso assenti |
| Selenium `.side` | Definizioni dei test | Non esecuzioni |
| MPP, formati legacy e altri non supportati | Inventario e limite esplicito | Nessuna interpretazione implicita |

Per i PDF installa `python -m pip install -e "./runtime[documents]"` dal checkout.
Gli altri lettori usano la libreria standard. Senza lettore PDF, la scansione
continua e segnala la capacità assente.

Limiti degli input: 32 MiB per documento, 128 MiB complessivi, 1.000 pagine per
PDF, 250.000 celle popolate per workbook e 128 MiB di espansione ZIP. Le frasi
da codice seguono al massimo quattro chiamate/40 entità, con 1.000 punti d’ingresso
e 50.000 fatti di corpo per analisi. I limiti raggiunti restano nella copertura.

## Rigenerare senza ripetere la scansione

```console
ases documents current.ases --out documenti --language it
ases documents current.ases --out documenti-rivisti --review revisione.json --language it
ases documents-diff previous.ases current.ases --out impatto.json
```

La rigenerazione legge lo snapshot salvato; non richiede i sorgenti e non avvia il
progetto. Usa una directory separata: rifiuta cartelle sconosciute e documenti
generati modificati manualmente. Il pacchetto registra snapshot padre, versione del
modello e digest della revisione. Il confronto segue record e riferimenti; una
scomparsa non significa automaticamente «risolto» e un hash diverso non dimostra
un cambiamento di significato.

## Interpretare i controlli

`DOCUMENT-QUALITY.md` distingue lettura completa/parziale, fonti non supportate e
controlli deterministici/euristici. Varianti dello stesso ID richiedono contesto:
possono essere versioni o estratti diversi. Un RNF senza soglia numerica può avere
un oracolo qualitativo valido. Una checklist tutta «sì», una formula con una X o
un test collegato non provano che il requisito sia soddisfatto.

Il rapporto indica anche parametri documentati assenti dalla firma, contesti espliciti dei contratti da rivedere, riferimenti non risolti e oracoli strutturati non recuperati. Semantica dei contratti, decisioni di architettura, partizioni dei test e validità dei comandi importati hanno una voce separata di revisione umana. I corpi dei documenti conservano anche termini tecnici e campi in inglese.

Il modello esportato contiene testo estratto, celle, commenti e frammenti di codice: controllane il contenuto prima di condividerlo.

Il profilo dei flussi `/3` associa anche i rami Java locali ai relativi esiti, senza prendere in prestito il corpo del metodo successivo. Cicli, switch, eccezioni e finalizzatori Java restano parziali: i loro esiti interni non vengono spacciati per uscite incondizionate. La [tabella delle capacità](FLOW-COVERAGE.md) distingue ciò che è recuperato da ciò che richiede ancora verifica; «parziale» non è un sinonimo diplomatico di «tutto a posto».

Le proposte di test ricostruite dal codice servono alla caratterizzazione: devono
essere confrontate con un oracolo indipendente, altrimenti si rischia solo di
fotografare bene un bug. [TESTING.md](../TESTING.md) spiega le misure ispezionabili
di requisiti, campi, collegamenti e controlli; non esiste un voto globale al progetto.

Per misurare anche i fatti che sostengono le frasi, dal checkout usa
`ases documents-evaluate runtime/tests/fixture_documents/behavior-corpus.json --out behavior-evaluation`.
Il rapporto mostra risultati, errori ed effetti possibili con TP/FP/FN e casi
ispezionabili. Valuta corpi d’ingresso selezionati; non assegna una percentuale di
comprensione generale e non esegue il progetto.

## Una prima lettura, poi i dettagli

Apri **Il progetto in breve** (`OVERVIEW.md`): operazioni, requisiti funzionali e
non funzionali disponibili, test e domande aperte. I collegamenti portano alle
voci dei documenti completi. **Collegamenti nei due sensi** (`TRACEABILITY.md`)
mostra anche il percorso inverso; un riferimento ambiguo resta tale. Nessuna
colonna con un numero equivale a una verifica riuscita.

Il confronto documentale distingue spostamenti, firme, comportamento, testo dei
requisiti, perimetro e metodo. Un possibile spostamento non trasferisce automaticamente
le conferme. I requisiti adottati restano presenti se cambia la fonte, ma il loro
supporto richiede revisione. Una voce scomparsa non è automaticamente risolta.

Per conservare il lavoro scegli **Pacchetto completo** prima del download: contiene
documenti, modello, revisioni e indice dei contenuti. Il **Rapporto ridotto** conserva
solo conteggi e omissioni; non conserva il lavoro e non si riapre come analisi.
Controlla sempre un pacchetto completo prima di condividerlo: contiene testi e prove.

### I campi osservati non sono uno schema completo

Per una costante locale JavaScript/TypeScript supportata, la frase sul risultato
può avere due prove: il ritorno e la dichiarazione dell'oggetto che ne fornisce i
campi. Apri entrambi i collegamenti. «Elenco parziale» significa che possono
esistere altri campi: lo schema completo non spunta per buona educazione.
Mutazioni o riferimenti incerti possono impedire del tutto questa inferenza.
Si descrive l'implementazione; non si dimostra l'intento originale né il
soddisfacimento di un requisito non funzionale.

Nei fogli usa colonne separate per ID, Statement/Descrizione, Attore e
Priority/Priorità. Nelle matrici di tracciabilità sono riconosciute anche intestazioni
come «ID Requisito» e «Descrizione Requisito»; negli altri fogli serve
un'intestazione che identifichi esplicitamente i requisiti. L'intestazione vale
per il singolo foglio.

Una X scritta nella cella, sotto l'ID di un test, conserva il collegamento dichiarato
al requisito della riga. È ammesso anche un riferimento diretto a una cella interna
contenente un valore esplicito. Formule calcolate, catene di riferimenti e risultati
memorizzati delle formule non vengono interpretati. Se l'ID del test non ha una
definizione corrispondente, il collegamento resta non risolto: un riferimento al
test padre non viene esteso automaticamente ai suoi sottocasi. Nessuna X dimostra
che il test sia stato eseguito o superato.

## Leggere prima la spiegazione

Le nuove analisi spiegano in italiano condizioni semplici, risultati con campi,
errori espliciti e possibili chiamate. Per esempio, un confronto sulla durata diventa
“il campo «minuti» di «richiesta» è inferiore a 15”; un risultato esplicito può indicare
“«stato» vale «occupata»”. La spiegazione non deve diventare codice con una cravatta.

Nel Desk, apri una scheda per leggere **Cosa significa**. **Vedi la prova nel codice**
mostra espressione originale, percorso e sorgente. Nei documenti, **Vedi il dettaglio
tecnico** apre firme, JSON e altri blocchi di codice. I file Markdown esportati mantengono
anche questi dettagli, utili per chi deve controllare o sviluppare.

Se un'espressione è troppo complessa per il traduttore, ASES lo dice e rimanda alla
prova: non inventa un significato dal nome di una funzione. Una chiamata possibile
non dimostra esecuzione o salvataggio permanente. Queste frasi restano ricostruzioni
da confermare, separate dai requisiti dichiarati e dal loro soddisfacimento.

Le analisi precedenti conservano il testo originale: per ottenere la nuova sintesi
serve una nuova scansione. Una modifica del metodo può richiedere di rivedere le
conferme precedenti; non cancella automaticamente i bisogni adottati dall'utente.
