# La UI locale di ASES

[English](DESK.md) · Italiano

## Installazione e avvio

Dalla radice del checkout, con Python 3.11 o successivo:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "./runtime[documents]"
.\.venv\Scripts\ases.exe ui
```

Su macOS/Linux crea lo stesso ambiente con `python3 -m venv .venv`, installa con `.venv/bin/python -m pip install -e "./runtime[documents]"` e avvia `.venv/bin/ases ui`. Se hai già attivato l’ambiente, basta `ases ui`. Git serve per gli URL di repository. L’opzione `documents` abilita la lettura dei PDF; senza, gli altri lettori funzionano e i PDF risultano non supportati. Template e specifica delle sezioni sono inclusi anche nel pacchetto installabile.

Si apre il browser. Se non succede, usa `ases ui --no-browser` e apri il collegamento stampato nel terminale. Il collegamento dà accesso alla sessione locale: conservalo per riaprire la scheda. `ases ui /percorso/progetto` precompila il campo; non avvia una scansione senza il tuo clic. `--port` sceglie una porta specifica, sempre sul solo indirizzo locale.

## Dalla cartella alla risposta

In **Nuova analisi**, scegli la cartella con il selettore di sistema o incolla il percorso. Se il selettore non è disponibile nell’installazione Python, il campo rimane utilizzabile. In alternativa puoi indicare un URL HTTPS pubblico, senza credenziali: ASES lo clona temporaneamente. Non installa dipendenze del progetto e non esegue il suo codice.

Apri **Opzioni** solo se serve: puoi escludere file o cartelle, un pattern per riga, o indicare una baseline `.ases` precedente. Per esempio `experiments/**` esclude gli esperimenti da questa analisi. Il progetto e il suo `.asesignore` non vengono modificati. Gli ambienti Python riconosciuti tramite `pyvenv.cfg` o `conda-meta/history`, le directory di pacchetti e gli output generati riconosciuti restano fuori perimetro. ASES non applica automaticamente tutte le regole di `.gitignore`.

Durante la scansione vedi la fase effettiva e il tempo trascorso. **Interrompi** termina il processo di lavoro isolato e rimuove i file del tentativo. La UI resta disponibile. Nessuna percentuale inventata per tenere compagnia alla barra di avanzamento.

Al termine, **Risultati** risponde a tre domande: quale struttura è stata ricostruita, quali proposte meritano una verifica e quale passo fare dopo. Segui le route oppure apri **Mappa del codice**, scegli un simbolo e leggi la prova nel sorgente. **Cosa raggiunge** e **Chi lo chiama** mostrano relazioni statiche: non dimostrano che quel percorso sia stato eseguito.

**Copertura** distingue i file e i metodi parziali dalle parti non determinate e mostra le directory escluse. Un controllo sintattico riuscito non significa applicazione corretta; zero proposte non significa zero problemi. I test del progetto vanno eseguiti separatamente. Se una prova sorgente è cambiata dopo la scansione, la UI chiede una nuova analisi invece di mostrarla come se appartenesse ancora allo snapshot.

## Documenti e salvataggio

**Documenti** offre anzitutto **Il progetto in breve** (`OVERVIEW.md`), oltre al rapporto leggibile in italiano o inglese (`REPORT.it.md` / `REPORT.md`). Seguono RAD, SDD e ODD, documenti di test, istruzioni recuperate e qualità della lettura. In **Dai requisiti alle prove** scegli requisiti documentati, frasi ricostruite dal codice, interfacce, test, diagrammi o fonti. Ogni voce mostra testo e provenienza; aprendola trovi condizioni, riferimenti e fonte a pagina, cella o riga. La frase non deve costringerti a indovinare cosa volesse dire un ID.

La lingua dell’interfaccia localizza la navigazione e le spiegazioni del reader; i documenti Markdown salvati mantengono la lingua originale. Per rigenerarli in inglese dallo snapshot senza ripetere la scansione, consulta il comando `ases documents ... --language en` nella [guida ai documenti](DOCUMENTS.it.md).

Il RAD conserva i requisiti dichiarati nelle specifiche, inclusi attori, priorità e soglie quando leggibili. Senza specifiche, ASES interpreta i flussi supportati del codice e propone frasi separate: ingressi, condizioni, ritorni, errori e chiamate con possibili effetti. Non ricava obiettivi di business o intenzioni originali dal nome di una funzione. L’ODD riporta package, firme, tipi dichiarati, commenti, contratti e diagrammi statici; non richiede di trovare per forza un pattern. [La guida ai documenti](DOCUMENTS.it.md) spiega formati e limiti.

Puoi annotare, confermare o segnalare una voce con **Salva e rigenera documenti**. La revisione resta separata dalla fonte, entra nello ZIP e viene conservata nel browser per lo stesso progetto. Ricaricando la pagina o ripetendo la scansione viene recuperata; se il record cambia, resta visibile come conflitto da rivedere. L’archivio del browser dipende da origine e porta: per conservare il lavoro scarica il rapporto. Le anteprime lunghe sono abbreviate; lo ZIP completo conserva i file completi. L’HTML contenuto nelle fonti non viene eseguito.

**Scarica pacchetto completo** crea uno ZIP con `START-HERE.md`, documenti e snapshot JSON/YAML. Non copia l’intero repository, ma il modello documentale conserva testi estratti, celle, commenti API e frammenti di codice, oltre a nomi, percorsi, prove e metadati: controlla il contenuto prima di condividerlo. Estrai lo ZIP in una cartella per riaprirlo con **Apri analisi salvata**; puoi indicare anche la cartella dei sorgenti per leggere le prove. L’esploratore usa snapshot v2. Gli snapshot storici restano leggibili con gli strumenti CLI e i rispettivi documenti, senza conversioni implicite.

Non viene aggiunta una cartella `.ases` al progetto. La UI conserva un’analisi completata e un tentativo in corso: un errore o un annullamento mantiene il risultato precedente, chiaramente indicato come ultima analisi completata. Una nuova analisi riuscita sostituisce la precedente. **Svuota la sessione** elimina il rapporto temporaneo; Ctrl+C nel terminale chiude il servizio e ripulisce la sessione. Chiudere la sola scheda non ferma il servizio. Arresti forzati del sistema possono lasciare file nella directory temporanea del sistema operativo.

## Le altre funzioni

| Voce | Risultato |
|---|---|
| Confronto | Finding e differenze semantiche fra due cartelle `.ases`; le differenze incerte restano esplicite |
| Sito pubblico | Campione di 1–10 pagine, form e script; niente accesso al backend o esecuzione JavaScript |
| Artefatto | Inventario statico dell’artefatto locale e delle source map |
| Riconciliazione | Corrispondenze fra snapshot sorgente, artefatto ed eventuali osservazioni runtime importate |
| Audit | Scostamenti dalla baseline nella cartella del progetto; segnala anche una baseline assente |
| Esportazione | JSON nel contratto 1.5 o 2.0 |
| Capacità ASES | Riconoscimento statico delle capacità; non esecuzione della suite di test |
| Accuratezza | Misure sul corpus incluso (`bundled`) o su un corpus JSON etichettato; non accuratezza universale |
| Pulizia | Anteprima di un output ASES riconosciuto e conferma esplicita della sua rimozione; rifiuta kit, progetti e voci collegate |

Le anteprime delle operazioni possono abbreviare liste lunghe. I conteggi usano il risultato completo e il rapporto scaricato conserva i dati originali. Le directory delle due analisi da confrontare devono essere già estratte, non ZIP.

**Metodo e template** è un percorso distinto: scegli SOW, RAD, SDD, ODD o documenti di test, compila il testo e scarica le bozze. Le bozze sono salvate nel browser per questo progetto e questa origine; puoi scaricarle in Markdown per conservarle altrove. Requisiti approvati e documentazione ricostruita dal codice hanno autorità diverse. Il kit guida il lavoro; il pulsante non sostituisce le decisioni di progetto.

## Limiti pratici

La UI accetta fino a 5.000 sorgenti, 128 MiB complessivi e 2 MiB per singolo sorgente; uno snapshot letto dalla UI può raggiungere 256 MiB. Il limite complessivo di un’operazione è cinque minuti; il clone remoto ha un limite di due minuti. Restringi il perimetro o usa la CLI per scansioni più grandi intenzionali. I limiti non sono una garanzia di consumo costante di memoria per qualsiasi input.

Le liste del codice mostrano 40 elementi per pagina; quelle documentali 20. L’esplorazione espande fino a 64 nodi: consulta il suo stato di copertura e usa la CLI per limiti diversi. Il sorgente ha un’anteprima di contesto e un limite di 1 MiB. Le anteprime documentali mostrano al massimo 120.000 caratteri o 1.500 righe; questi limiti di visualizzazione non cambiano la copertura dello scanner.

Il servizio è pensato per una persona sul proprio computer. Non esporlo tramite proxy o tunnel: usa solo `127.0.0.1`, verifica host e origine e richiede la chiave di sessione per le API. Non usa servizi di generazione esterni, telemetria, font remoti o CDN. [TESTING.md](../TESTING.md) descrive le verifiche riproducibili.

## Scegliere cosa scaricare

Il selettore **Cosa vuoi conservare?** parte dal **Pacchetto completo**: mantiene il
lavoro e consente di riaprirlo dopo aver estratto lo ZIP. Il **Rapporto ridotto**
contiene solo conteggi aggregati e una lista esplicita delle omissioni, senza testi,
percorsi, sorgenti o note. Non è uno snapshot riapribile e i conteggi possono comunque
rivelare caratteristiche del progetto. L'indice `EXPORT-CONTENTS.json` dichiara il
contenuto di entrambi. Nessun pacchetto viene inviato automaticamente.

Il pacchetto completo ammette fino a 512 MiB di file non compressi e 128 MiB di ZIP
compresso. La scrittura dei file nell’archivio avviene a blocchi e il buffer ZIP si
ferma al limite compresso; l’analisi rimane disponibile se l’esportazione non riesce.
Se supera il
limite, l'analisi resta disponibile e puoi scegliere il rapporto ridotto o restringere
una nuova scansione. Non affidare l'unica copia delle revisioni alla memoria del browser.

I controlli principali funzionano da tastiera e mostrano il focus. Le liste mantengono
il focus quando cambi filtro; i link dei documenti aprono il documento e la voce
corrispondente, oppure segnalano un'anteprima abbreviata. La verifica a schermo stretto
è una prova del layout, non una certificazione di accessibilità. Vedi la
[matrice delle verifiche](SUPPORT.md) per ambienti e limiti effettivamente provati.
