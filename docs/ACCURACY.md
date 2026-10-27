# Misurare la qualità del recupero

Il benchmark confronta ciò che ASES ricostruisce con aspettative esplicite verificabili nei sorgenti. Un modello può superare lo schema e contenere comunque un falso allarme: i due controlli servono a scopi diversi.

## Verifica corrente 1.13.1 — 27 ottobre 2026

Le due correzioni richieste riguardano copertura e classificazione. Le fonti,
etichette e soglie originali restano immutate: **regressioni su casi noti**, non
un nuovo holdout indipendente. Profili: flussi 12, selezione 2, operazioni 4,
narrazione 6, classificazione `constraint-signals/3`; documenti 9 e prosa 3 invariati.

**Copertura:** 90/90 e 239/244 riepiloghi, prima 73/90 e 222/244. Dei 39 ingressi
prima irrisolti, 34 sono recuperati come riepiloghi interni e cinque hanno un corpo
localizzato/analizzato senza fatti ammessi nelle categorie valutate: quattro vuoti,
uno con assegnazione a stato interno. Nessun requisito o ritorno sintetico. I
cinque restano nel conteggio di 244. Tutti i fatti attesi del campione sono inclusi:

| Campione, associazione per posizione | Ritorni TP/FP/FN | Errori TP/FP/FN | Possibili chiamate TP/FP/FN |
|---|---:|---:|---:|
| 90 ingressi | 94/0/0 | 8/0/0 | 1/0/0 |
| 244 ingressi | 174/0/0 | 100/0/0 | 71/0/0 |

Le 140 scansioni non eseguono codice, build o test dei target. La sola selezione
per nome/percorso rimane ambigua con gli omonimi: sul campione 244 dà 125/0/49,
89/0/11 e 51/0/20; è distinta dalla misura per posizione, non cancellata. Il
supplemento congelato mantiene 19/19 chiamate e tre controlli negativi; quote
30/30 Python e 30/30 JS-TS. Nove nomi ammessi, non ogni possibile mutazione/I/O.

**Classificazione senza categorie nell’input:** frasi esatte 625/625 PROMISE e
110/110 ReqView; classi corrette **537/625 (85,92%)** e **110/110**. PROMISE
conserva 48 errori e 40 astensioni nel denominatore; 85 casi migliorano e uno
peggiora rispetto alla 1.12 (saldo +84). Non funzionali: TP318/FP9/FN52,
precisione97,25% e richiamo85,95%; funzionali: TP219/FP39/FN36,
precisione84,88% e richiamo85,88%.

Il peggioramento PROMISE:199 descrive azioni filtrate per stato e livello di
accesso: l’autore lo classifica funzionale, le regole suggeriscono non funzionale.
Il caso resta visibile e l’etichetta originale non cambia. Frasi miste e il
duplicato con etichette opposte impediscono di identificare sempre l’intenzione
dell’autore dal solo testo. Nessuna probabilità calibrata o comprensione generale
è dimostrata. Precedenza dei tipi dichiarati e importazione nativa invariate.

La lacuna di copertura del campione noto è spiegata; la classificazione è migliorata
ma non conclusa. Beta generale ancora NO GO; prove utenti escluse dalla tranche.
La prova precedente GLiNER2 44/80 resta storica e facoltativa, senza nuovi run del
modello. Suite e piattaforme correnti in [SUPPORT.md](SUPPORT.md).

## Checkpoint storico 1.12 — 27 ottobre 2026

Versione sperimentale 1.12: profili `inert-documents/9`, `explicit-prose/3`,
`constraint-signals/2`, `branch-local-flow/11`. Le fonti e le etichette congelate
restano identiche: le correzioni sui casi già noti sono **regressione**, non un
nuovo holdout indipendente. Soglie invariate.

| Testo originale senza categorie nell’input | Frasi esatte | Categorie corrette sul totale | Non funzionali corretti |
|---|---:|---:|---:|
| PROMISE | 625/625 | 453/625 (72,48%) | 239/370 |
| ReqView SRS | 110/110 | 110/110 | 23/23 |

Su PROMISE restano 86 astensioni e 86 classificazioni errate; tutte nel denominatore.
625 righe contengono 622 testi distinti e un gruppo con etichette opposte, conservate.
Il risultato ReqView segue correzioni sui casi noti: non è una garanzia universale.
Importazione nativa: 625/625 righe ARFF e campi categoria conservati (255 F
funzionali, 370 codici opachi non specificati); 110/110 ID/categorie SRS ReqView più
278 ASVS fuori dal perimetro etichettato; 86/86 frasi e ID HTML pubblicati. Il
confronto ARFF per solo testo dà 254 classi corrette, per l’ambiguità del duplicato.
La preservazione per ID delle categorie HTML fornite dà 735/735; il confronto per
testo 733/735. Importare categorie già dichiarate non misura comprensione.

Codice: 140 scansioni di file dai nove repository originali, zero errori, nessuna
esecuzione di codice/build/test dei target. Associazioni univoche per posizione
73/90 e 222/244. Inclusi tutti gli ingressi irrisolti nel denominatore:

| Campione | Ritorni TP/FP/FN | Errori TP/FP/FN | Possibili chiamate TP/FP/FN |
|---|---:|---:|---:|
| 90 ingressi | 77/0/17 | 7/0/1 | 1/0/0 |
| 244 ingressi | 162/0/12 | 93/0/7 | 67/0/4 |

Il supplemento separato e congelato prima delle predizioni comprende 22 ingressi
in 11 file da SQLAlchemy, TypeORM e aiosqlite: 14 chiamate Python, 5 TypeScript e
3 controlli negativi. Con riga sorgente: 19 TP/0 FP/0 FN, controlli negativi 3/3;
con solo nome/percorso: 13/0/6 per omonimie. Quote cumulative Python 30/30 e JS/TS
30/30. Il manifesto originale resta invariato. Curatela nella stessa sessione,
non revisione indipendente; nove nomi ammessi, non ogni mutazione/I/O. Zero FP in
questi ambiti chiusi non è precisione universale.

**GLiNER2 reale:** 80 frasi, 20 funzionali e 20 non funzionali per corpus,
44/80 corrette (55%): PROMISE 19/40, ReqView 25/40; non funzionali 0/20 e 5/20.
Sulle stesse frasi il classificatore ASES 1.12 dà 23/40 e 40/40; la versione 1.11
23/40 e 21/40. Confronto di convenienza bilanciato, senza categorie nell’input;
nessuna stima sulla popolazione o nuova accettazione indipendente. Il modello
resta facoltativo e senza adozione automatica. 80 citazioni esatte; 25,62 s con
cache disco calda, picco processo 2,71 GiB, guard iniziale almeno 4 GiB disponibili.
Il primo run ha perso la misurazione per un errore dello script RAM, conservato;
nessuna modifica a modello/schema/soglia. Tre ulteriori ipotesi con citazioni
esatte verificano il backend su snapshot invariato, non accuratezza semantica.

La classificazione generale e la copertura arbitraria restano insufficienti per
una beta generale. Le prove umane sono escluse da questa tranche. Suite e
piattaforme: [SUPPORT.md](SUPPORT.md). I checkpoint seguenti sono storici.

## Checkpoint storico 1.11 — 26 ottobre 2026

Il runtime sperimentale 1.11 (`inert-documents/8`, `branch-local-flow/10`,
`syntax-tokens/3`) è stato confrontato con le stesse fonti ed etichette congelate.
Questi risultati seguono correzioni guidate dai primi errori: **sono regressione
nota, non un nuovo campione indipendente**. I risultati iniziali restano sotto.

| Prova senza categorie fornite | Frasi esatte prima → dopo | Categoria corretta sul totale prima → dopo |
|---|---:|---:|
| PROMISE, 625 righe | 94 → 613 | 50 → 389 |
| ReqView SRS, 110 requisiti | 76 → 110 | 62 → 87 |

I non funzionali corretti sono 177/370 su PROMISE e 3/23 su ReqView. I tipi suggeriti
espongono indizi e origine; le astensioni restano nel denominatore. La classificazione
generale resta insufficiente. Il modello GLiNER2 facoltativo non è stato valutato
semanticamente: la prova reale si è fermata per memoria disponibile sotto 4 GiB.

La lettura nativa conserva 110/110 ID e categorie SRS da ReqView e 278 requisiti
ASVS aggiuntivi, fuori dallo scope etichettato; non sono automaticamente falsi
positivi. ARFF conserva 625/625 frasi e codici originali: F è funzionale, mentre
370 codici opachi restano non specificati. HTML pubblicato: 86/86 frasi e ID.
Preservare categorie già fornite non misura comprensione. Nel confronto per testo,
la frase PROMISE con etichette opposte resta ambigua; i campi per ID sono verificati
separatamente senza correggere le etichette originali.

Sul campione di codice da 244 ingressi, 221 associazioni univoche (prima 175).
Includendo gli ingressi non risolti: ritorni **161 TP / 0 FP / 13 FN**, errori
**92/0/8**, possibili chiamate ammesse **67/0/4**. Il campione iniziale da 90 dà
58/0/36, 7/0/1 e 1/0/0. Le quote positive effetti restano Python 16/30 e JS/TS
25/30, sotto il minimo: nessuna soglia è stata ridotta. Zero falsi positivi in
questo ambito chiuso non è una precisione universale. Le chiamate sono statiche,
limitate ai nove nomi ammessi; non provano esecuzione o effetti sul sistema.

Le 140 scansioni completate non hanno eseguito codice, build o test dei progetti.
Compatibilità e suite del prodotto sono riportate in [SUPPORT.md](SUPPORT.md).

## Esecuzione

Dalla directory runtime/, con le dipendenze di test installate:

~~~sh
python tools/evaluate_accuracy.py --out ../accuracy-results.ases
~~~

Per un corpus diverso, aggiungi --corpus /percorso/corpus.json. La destinazione deve essere vuota o un output ASES riconosciuto. Il valutatore rifiuta materiale utente, il proprio codice e il corpus come destinazione. I sorgenti dei casi vengono analizzati in una directory temporanea e ripuliti; non vengono eseguiti, importati o usati per installare dipendenze.

| File | Come usarlo |
|---|---|
| report.html | Aprilo nel browser: filtra per capacità o errore ed espandi un caso per leggere sorgente, motivazione e confronto atteso/osservato |
| REPORT.md | Stessi risultati in un documento leggibile senza interfaccia interattiva |
| results.json | Dati strutturati, ambiente, hash e risultati dei singoli casi per confronti riproducibili |

Il report HTML è autonomo e non richiede richieste di rete. I file persistono finché non li rimuovi con ases clean; le scansioni intermedie vengono invece eliminate automaticamente.

## Leggere i numeri

Ogni caso dichiara sorgenti, collezione e selettori valutati, aspettative presenti/assenti, motivazione e completezza del solo ambito selezionato. La completezza dell'oracolo non dichiara completo lo scanner.

| Esito | Significato |
|---|---|
| TP | Risposta attesa recuperata |
| FP | Risposta espressamente esclusa, oppure extra nel solo ambito dichiarato completo |
| FN | Risposta attesa mancante |
| TN | Risposta espressamente esclusa che non viene emessa |
| Non valutato | Risposta non annotata in un ambito dichiarato incompleto |

Precisione = TP/(TP+FP): quante risposte valutate sono corrette. Richiamo = TP/(TP+FN): quante risposte attese vengono trovate. F1 = 2TP/(2TP+FP+FN). Se il denominatore è nullo, il valore è non misurabile, non 100%. I negativi non gonfiano precisione e richiamo.

Una predizione non annotata non è automaticamente vera o falsa. Le capacità fuori dai selettori non vengono valutate: zero non valutati nella tabella non significa aver controllato tutto l'output. Gli unknown possono verificare che ASES dichiari un limite senza inventare risultati; non valgono come recupero del comportamento mancante.

Il confronto considera tipo/file/nome per le entità, estremi e direzione per le relazioni, regola/stato per i suggerimenti. Non verifica tutte le proprietà semantiche. Una collisione nella proiezione viene segnalata e fa fallire il caso.

## Nuove fonti e classificazione dei requisiti — 25 ottobre 2026

Sul profilo `inert-documents/7` sono stati valutati due nuovi campioni con categorie
già assegnate dagli autori: [PROMISE NFR](https://zenodo.org/records/268542),
625 righe, e il documento SRS del
[progetto dimostrativo ReqView](https://www.reqview.com/doc/example-project/),
110 requisiti. Le categorie originali sono rispettivamente 255/370 e 87/23
funzionali/non funzionali. Due lettori delle fonti sono stati confrontati prima
delle predizioni; nessun addestramento o correzione del motore ha usato questi risultati.

Per la prova di classificazione, ASES ha ricevuto soltanto le frasi originali in
un file di testo: nessun ID, categoria o titolo di sezione che suggerisse la risposta.
Questa è una proiezione dichiarata in un formato supportato, non una prova di
lettura dei formati nativi. Il confronto del testo ammette solo normalizzazione
Unicode NFC e degli spazi, senza somiglianza approssimata.

| Campione | Frasi recuperate esattamente | Categorie corrette fra le frasi recuperate | Recuperate e classificate correttamente sul totale |
|---|---:|---:|---:|
| PROMISE | 94/625 (15,04%) | 50/94 (53,19%) | 50/625 (8,00%) |
| ReqView SRS | 76/110 (69,09%) | 62/76 (81,58%) | 62/110 (56,36%) |

**La classificazione euristica della prosa libera richiede ancora revisione.**
Il risultato su ReqView non include alcun non funzionale classificato correttamente;
su PROMISE sono 4 su 370. Una percentuale calcolata soltanto sulle frasi recuperate
non deve nascondere quelle mancanti. Gli errori di classificazione sono un problema
diverso dalle frasi non recuperate.

La prova separata di importazione HTML, con ID e categoria esplicitamente forniti,
conserva 735/735 ID e i rispettivi campi categoria. È conservazione di dichiarazioni,
non comprensione della frase. Il primo confronto basato sul solo testo lascia due
righe PROMISE ambigue: la stessa frase ha due etichette originali differenti.
Il controllo per ID è riportato separatamente, senza correggere quelle etichette.
PROMISE contiene 622 testi distinti su 625 righe; le righe dello stesso progetto
e i duplicati non sono osservazioni indipendenti.

Con i byte e le estensioni originali, i formati ARFF e REQW non producono requisiti:
non sono formati documentali supportati. Anche gli 86 ID nella pagina HTML pubblicata
dell'esempio SRS ReqView non vengono recuperati da questo profilo. Il risultato
positivo sull'importazione adattata non dimostra il supporto di questi originali.

Le etichette esterne offrono un riferimento verificabile, non una definizione
universale di funzionale/non funzionale. La revisione automatizzata può controllare
identità delle fonti, fedeltà dei campi, duplicati, contraddizioni e coerenza degli
oracoli; una revisione dell'autore o di un altro modello resta distinta dalla
validazione umana indipendente. Le fonti di terzi e i rapporti di questa prova non
sono inclusi nel pacchetto distribuito.

## Nuovo campione di codice — 25 ottobre 2026

La stessa wheel congelata è stata provata su nove nuovi repository pubblici:
Click, Tenacity, Tortoise ORM, date-fns, Ramda, MikroORM, Apache Commons Text,
Vavr e Jdbi. Revisioni e aspettative sono state fissate prima delle scansioni.
Nessun codice, test o processo di build di questi progetti è stato eseguito.

Il campione iniziale comprende 90 ingressi; uno strato distinto comprende 244
ingressi e 747 asserzioni, di cui 345 fatti positivi e 402 assenze di categoria.
La scelta del secondo strato cerca deliberatamente errori ed effetti: non è una
selezione casuale rappresentativa di tutti i progetti. Due quote positive sugli
effetti restano insufficienti: Python 16/30 e JS/TS 25/30. I due strati non vengono
presentati come due conferme indipendenti.

Il primo confronto usa nome e percorso esatti, conservando anche i selettori
ambigui o non risolti come mancanti:

| Categoria, strato da 244 ingressi | TP | FP | FN |
|---|---:|---:|---:|
| Espressioni restituite | 85 | 2 | 89 |
| Errori esplicitamente sollevati | 72 | 0 | 28 |
| Possibili chiamate con nome ammesso | 44 | 0 | 27 |

Una seconda misura, dichiarata prima della prova, usa anche la riga di definizione
per associare il risultato alla funzione: risolve 175/244 ingressi. Sul denominatore
intero, inclusi i positivi non recuperati, i conteggi sono rispettivamente
118/2/56, 77/0/23 e 61/0/10. La misura sulle sole funzioni risolte resta distinta:
non può nascondere le altre 69.

Una successiva verifica sintattica attribuisce i due FP sui ritorni al comparatore,
non a ritorni sbagliati ricostruiti dallo scanner: un'espressione TypeScript differisce
solo per CRLF/LF e un'altra per parentesi esterne ridondanti. Il risultato iniziale
è conservato; la diagnosi separata non aggiunge copertura e non fa superare i criteri
di richiamo. La verifica mantiene distinte parentesi che cambiano precedenza,
operatori diversi e spazi nelle stringhe.

Le assenze negli effetti riguardano soltanto chiamate con nome terminale `save`,
`create`, `insert`, `update`, `delete`, `remove`, `write_text`, `write_bytes`, `commit`.
Non significano assenza di assegnazioni, I/O, eccezioni dei metodi chiamati o
modifiche reali a un database. La revisione dei casi mancanti distingue selezione
dei metodi privati, costrutti Java fuori dal profilo e un difetto di associazione
fra API e fatti per un metodo di un builder annidato. Questi risultati non
approvano l'accuratezza generale del recupero su codice nuovo.

## Regressione sintetica inclusa

Il corpus incluso contiene **16 casi sintetici e 39 etichette esplicite**. Il risultato registrato su Windows/Python 3.14.7 è:

| Capacità | TP | FP | FN | TN | Precisione | Richiamo |
|---|---:|---:|---:|---:|---:|---:|
| Route dichiarate | 7 | 0 | 0 | 10 | 100% | 100% |
| Dichiarazioni di test | 5 | 0 | 0 | 5 | 100% | 100% |
| Chiamate locali risolte | 2 | 0 | 0 | 3 | 100% | 100% |
| Classificazione chiamate | 1 | 0 | 0 | 1 | 100% | 100% |
| Suggerimenti Observer | 2 | 0 | 0 | 2 | 100% | 100% |
| Limiti dichiarati | 0 | 0 | 0 | 1 | non misurabile | non misurabile |

Passano **16/16 casi** e **16/16 controlli di stabilità** dopo l'aggiunta di commenti e righe vuote. Un caso passa se rispetta le aspettative, gli schemi, gli unknown obbligatori, l'unicità della proiezione e le verifiche di stabilità richieste. I casi sui limiti possono passare il controllo di prudenza senza contribuire ai positivi recuperati.

Codici di uscita: 0 = criteri soddisfatti; 1 = misurazione completata con scostamenti; 2 = input non valido o errore operativo intercettato. Un errore operativo non equivale a una misurazione negativa completata.

## Limiti della misura

Le etichette hanno motivazioni ispezionabili, ma la revisione indipendente non è ancora completata. I casi includono regressioni note e non costituiscono un campione rappresentativo né un insieme indipendente mai usato durante le correzioni. Il 100% di una riga non è l'accuratezza di ASES su qualsiasi repository.

I suggerimenti architetturali richiedono giudizio: tre notifiche dirette possono giustificare una possibilità di disaccoppiamento, non l'obbligo di applicare un pattern. Le emissioni EventEmitter riconosciute sono controevidenza; bus personalizzati, sottoclassi, factory tra moduli e mutazioni arbitrarie restano parziali. Le utility importate non diventano automaticamente confini remoti, mentre gli effetti dei client non riconosciuti restano irrisolti.

I controlli di stabilità riguardano cambi di posizione, non ogni refactoring. Gli hash identificano i byte del corpus e del codice eseguito: non attestano autorevolezza, indipendenza o correttezza delle etichette. Il benchmark non misura sicurezza, traffico, esecuzione dei test del progetto o correttezza di ogni frase nei documenti generati. Sistemi operativi e versioni non provati richiedono verifiche proprie.

## Aggiungere un caso

Parti da un comportamento osservabile e definisci le aspettative prima di eseguire la prova. Includi un positivo, un negativo vicino e, dove serve, un caso non supportato con unknown atteso. Dichiara completo un ambito soltanto se puoi controllarne tutte le risposte. Mantieni separati i casi di regressione dai futuri campioni indipendenti e conserva i disaccordi da revisionare.

Il corpus è in [runtime/tests/fixture_accuracy/corpus.json](../runtime/tests/fixture_accuracy/corpus.json). I test del misuratore controllano anche falsi allarmi e omissioni iniettati intenzionalmente; passare quei test non sostituisce la lettura del risultato del benchmark. Per eseguire suite e valutatori aggiuntivi, vedi [TESTING.md](../TESTING.md).
