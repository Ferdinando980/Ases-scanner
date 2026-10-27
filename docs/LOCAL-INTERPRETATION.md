# Interpretazione locale e osservazioni HTTP

La scansione normale resta deterministica e non richiede un modello. Da **Altri
strumenti → Interpreta con un modello locale** puoi scegliere uno snapshot salvato
e uno dei due provider locali. ASES non scarica modelli e non esegue il progetto
analizzato.

Il provider predefinito `llm` usa un server compatibile con l'API chat di llama.cpp,
già avviato sul computer. Il provider facoltativo `gliner2` usa un runtime Python e
una cartella modello locale scelti dall'operatore. Il runtime deve già avere
GLiNER2, PyTorch e `psutil`; la cartella deve contenere `config.json` e
`model.safetensors`, con gli eventuali file tokenizer e configurazione supportati.
Il fingerprint registra il contenuto di configurazione e pesi, non certifica
l'intero ambiente o la sua autenticità. GLiNER2 funziona offline: ASES non installa
dipendenze, non avvia download e non cerca modelli in percorsi privati predefiniti.
Il worker richiede almeno 4 GiB di memoria disponibile prima di caricare il modello.

Il server deve usare un indirizzo numerico loopback: `http://127.0.0.1:8080/v1`
oppure `http://[::1]:8080/v1`. Niente credenziali, proxy, DNS o redirect automatici.
Solo i brani selezionati vengono inviati al server locale scelto. Il comportamento
interno di quel server resta sotto il controllo di chi lo ha configurato.

```sh
ases interpret current.ases --endpoint http://127.0.0.1:8080/v1 --max-excerpts 3 --out reading
```

Per GLiNER2, indica esplicitamente runtime e modello già disponibili:

```sh
ases interpret current.ases --provider gliner2 --python-executable /path/to/python --model-path /path/to/local-model --out reading
```

L'output contiene `INTERPRETATION.md` e `interpretation.json`. Il provider LLM
seleziona una citazione tramite indice; GLiNER2 associa invece la frase classificata
alla sua fonte originale. Una citazione esatta prova che quelle parole esistono: non
rende automaticamente corretta la conclusione del modello. Le proposte restano
ipotesi da confermare, senza modificare RAD, requisiti riconosciuti o snapshot. Il
modello non guadagna una laurea in ingegneria del software perché ha restituito un
JSON ben formato.

Il provider LLM legge da uno a sei estratti di 80–1.400 caratteri, dando precedenza
a README e RAD non archiviati; la UI usa tre estratti. Sono accettate al massimo due
proposte per estratto, con risposta di 600 token e timeout di 45 secondi per
richiesta. Risposte invalide o senza citazioni vengono scartate. GLiNER2 legge fino
a tre unità dalla CLI per impostazione predefinita (`--max-excerpts` cambia il
limite) e fino a 40 dalla UI, limitate a 2.000 caratteri ciascuna; il risultato registra
le unità omesse. Le parti non lette restano scoperte. Qualità, tempi e memoria
dipendono dal modello e vanno misurati sul proprio caso.
Il worker controlla i token senza troncamento e riserva 128 token per il contesto
del classificatore: è un margine prudente, non una garanzia per ogni variante
del modello. Le unità oltre il budget vengono omesse con una motivazione.
La prova del 27 ottobre 2026 ha misurato GLiNER2 su 80 frasi originali senza
categorie nell’input, bilanciate 20 funzionali e 20 non funzionali per corpus:
44/80 classificazioni corrette (PROMISE 19/40, ReqView 25/40). È un campione di
convenienza, non una stima generale o un holdout indipendente. Il run completato,
con cache disco già calda, richiede 25,62 s e raggiunge 2,71 GiB di RAM del
processo; il controllo iniziale richiede almeno 4 GiB disponibili. La prima
misurazione ha perso i risultati per un errore nello script di memoria e resta
registrata separatamente. Nessuna modifica di modello, schema o soglia dopo le
predizioni. Il backend ASES ha inoltre prodotto tre ipotesi con tre citazioni
esatte da uno snapshot invariato; è una prova di integrazione, non tre nuovi casi
semanticamente corretti. Il punteggio non calibrato non è una probabilità di
correttezza: le proposte restano ipotesi e non vengono adottate automaticamente.
Vedi [misure e limiti](ACCURACY.md).

## Percorsi dinamici e comportamento durante l'esecuzione

ASES può confrontare osservazioni HTTP raccolte da un operatore o da strumenti
del progetto. Non avvia il progetto e non invia richieste automaticamente.

```sh
ases runtime-template current.ases --out observations.json
# Compila collector, environment, captured_at e observations con le prove raccolte.
ases runtime-check current.ases --observations observations.json --out correlation.json
```

Esempio di una voce in `observations`:

```json
{"method":"GET","path":"/items/one","status":200}
```

Puoi aggiungere `handler_entity_ref` se lo strumento di raccolta ha identificato
l'handler e il suo ID nello snapshot. Il template vincola osservazioni e sorgenti
tramite identità dello snapshot e digest del manifest. Questi vincoli evitano
confronti accidentali fra versioni diverse; non autenticano il raccoglitore.
Non inserire query, frammenti, credenziali o corpi delle risposte.

La stessa funzione è disponibile in **Altri strumenti → Confronta osservazioni
HTTP**. Un percorso eseguito ma non ricostruito resta `dynamic-or-unreconstructed`;
non viene inventato un handler statico. Più corrispondenze restano ambigue, senza
scegliere automaticamente la precedenza. Un percorso non osservato non è assente,
rotto o irraggiungibile. Le osservazioni importate non sono esecuzioni verificate
indipendentemente da ASES. Il numero massimo è 1.000 osservazioni per file.

## Anteprime dei sorgenti grandi

L'anteprima verifica il file a blocchi, fino a 128 MiB, conservando solo le 33 righe
intorno alla posizione richiesta. Le righe oltre 2.000 caratteri vengono accorciate
con un avviso. Hash cambiati, percorsi esterni e collegamenti non autorizzati restano
bloccati. Un problema nell'anteprima compare vicino alla prova senza nascondere il
risultato dell'analisi. Questa lettura non amplia il perimetro della scansione.
