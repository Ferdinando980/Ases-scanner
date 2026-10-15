# Misurare la qualità del recupero

Il benchmark confronta ciò che ASES ricostruisce con aspettative esplicite verificabili nei sorgenti. Un modello può superare lo schema e contenere comunque un falso allarme: i due controlli servono a scopi diversi.

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

## Risultato verificato

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
