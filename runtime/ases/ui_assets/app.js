'use strict';

// All project text is untrusted data. Render it with textContent, never HTML.
const $ = id => document.getElementById(id);
const el = (tag, text, className) => {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
};
function stored(area,key){try{return window[area].getItem(key);}catch{return null;}}
function remember(area,key,value){try{window[area].setItem(key,value);}catch{/* Session link remains the fallback. */}}
let language = stored('localStorage','ases-language') === 'en' ? 'en' : 'it';
let token = location.hash.slice(1) || stored('sessionStorage','ases-session') || '';
if (location.hash) {
  remember('sessionStorage','ases-session', token);
  history.replaceState(null, '', location.pathname);
}
let report = null, page = 'overview', offset = 0, generation = 0, requestNumber = 0;
let selectedItem = null, kitData = null, drafts = {}, activeTemplate = '', busy = false;
try{drafts=JSON.parse(stored('localStorage','ases-template-drafts')||'{}');}catch{}
let activeAction = 'scan';
const sourcesByAction = {};
let workspaceView = 'form', lastStatus = null, sourceRequest = 0;
let requestedCollection = null;
let draftDirty = false;
const words = {
  it: {
    desk:'sul tavolo',local:'Lavora sul tuo computer',eyebrow:'UN PO’ D’ORDINE, PRIMA DEL REFACTORING',
    title:'Il codice c’è.\nFacciamoci un’idea.',lead:'Una cartella, un’analisi leggibile. Poi puoi seguire ogni indizio fino al codice. Anche quello che speravi fosse già documentato.',
    folder:'Cartella del progetto',analyze:'Analizza il progetto ↗',task:'Cosa vuoi fare?',
    inputHint:'Percorso locale oppure URL HTTPS di un repository pubblico. I documenti vengono creati insieme all’analisi.',
    step1:'Prima, il quadro.',step1p:'Struttura, route e punti da rivedere, raccolti in una risposta breve.',
    step2:'Poi, le prove.',step2p:'Apri un risultato e leggi la riga che lo sostiene. Senza caccia al file.',
    step3:'Il giudizio resta tuo.',step3p:'Collegamenti statici e zone non coperte restano riconoscibili. Il verde è un colore, non un certificato.',
    footer:'Sessione locale e temporanea. Nessun sorgente viene caricato su un servizio esterno. Repository remoti e siti richiedono accesso alla rete. Scarica il rapporto per conservarlo; Ctrl+C ferma ASES e rimuove i file temporanei.',
    download:'Scarica il rapporto ↓',clear:'Svuota la sessione',search:'Cerca nei risultati',
    exportMode:'Cosa vuoi conservare?',exportReduced:'Rapporto ridotto — solo conteggi',exportFull:'Pacchetto completo — documenti e revisioni',
    overview:'Il quadro',findings:'Da rivedere',entities:'Esplora i collegamenti',files:'Copertura',documents:'Documenti',
    observations:'Osservazioni',behaviors:'Percorsi ricostruiti',controls:'Controlli locali',tests:'Dichiarazioni di test',
    external_systems:'Confini esterni',structural_relations:'Relazioni statiche',unknowns:'Incertezze',hints:'Indizi deboli',suppressed:'Risultati soppressi',
    running:'Analisi in corso. Sto leggendo le fonti; il progetto non viene avviato.',complete:'Analisi pronta. I test del progetto non sono stati eseguiti.',
    working:'Operazione in corso…',done:'Operazione completata. Leggi il risultato e i suoi limiti.',
    failed:'L’operazione non è stata completata.',noSession:'Apri il collegamento di sessione stampato da ases ui nel terminale.',
    summary:'Ecco cosa emerge.',limits:'Una mappa, non un verdetto.',
    limitsText:'Una dichiarazione osservata, un collegamento inferito e una parte non coperta sono cose diverse. Qui restano separate.',
    start:'Da dove partire',startText:'Apri i candidati alla revisione, segui le prove e verifica il contesto. Nessun finding non significa automaticamente nessun problema.',
    browse:'Esplora route e simboli →',review:'Apri i risultati →',coverage:'Guarda i limiti →',
    sourceFiles:'file sorgente inventariati',routeCount:'route ricostruite',reviewCount:'candidati alla revisione',
    findingsDesc:'Proposte e contraddizioni prima; poi i risultati osservati. Le regole descrivono segnali, non sentenze.',
    entitiesDesc:'Scegli una route o un simbolo. Puoi vedere le prove, chi lo chiama e cosa raggiunge nel grafo statico.',
    filesDesc:'Copertura del metodo per file e famiglia di relazioni. Non è una percentuale di accuratezza.',
    select:'Scegli un risultato per vedere prove e collegamenti.',empty:'Nessun risultato in questa selezione. La copertura resta da controllare.',
    confidence:'Confidence',assumptions:'Assunzioni',counter:'Controprove',guidance:'Cosa valutare',evidence:'Prove nei sorgenti',
    missingEvidence:'Nessuna posizione sorgente disponibile per questo elemento.',forward:'Cosa raggiunge →',backward:'← Chi lo chiama',
    trace:'Collegamenti ricostruiti',traceLimit:'Sono collegamenti statici, non una traccia di esecuzione. Espansione limitata a 64 nodi; gli estremi allegati possono essere di più.',
    noLinks:'Nessun collegamento ammesso trovato: non prova isolamento a runtime.',
    unknownLabel:'Copertura',raw:'Dettagli completi',previous:'← Prima',next:'Dopo →',results:'risultati',
    docsTitle:'La documentazione è già sul tavolo.',docsText:'Questi documenti sono stati ricostruiti dalle fonti disponibili. Non sono requisiti approvati né decisioni attribuibili agli autori. Aprili qui o scarica l’intero rapporto.',
    docSummary:'Una prima lettura dei risultati e dei limiti.',
    docOverview:'Struttura del sistema ricostruita dal codice.',
    docQuality:'Copertura, incognite e limiti dell’estrazione.',
    docRad:'Modello di analisi recuperato: da verificare con le persone interessate.',
    docSdd:'Architettura e relazioni osservate o inferite.',
    docOdd:'Dettagli strutturali e candidati alla revisione.',
    docTesting:'Dichiarazioni e collegamenti ai test; nessun test eseguito.',
    docOther:'Dati recuperati e relativi collegamenti.',
    openDoc:'Apri documento',closeDoc:'Chiudi documento',snapshot:'Identità dello snapshot',json:'Dati completi (JSON)',
    siteSummary:'Sono state osservate pagine pubbliche, senza eseguire JavaScript o accedere al codice backend.',
    sitePages:'pagine osservate',siteForms:'form osservati',siteLimits:'Il sito pubblicato non racconta tutto il sistema. Route interne, autorizzazioni effettive e comportamento runtime restano non verificati.',
    operation:'Il risultato, con i suoi confini.',operationText:'Il riepilogo qui sotto deriva dai dati restituiti da ASES. Nell’archivio trovi il risultato completo.',
    compareText:'Le differenze descrivono due analisi. Un elemento scomparso non è automaticamente un problema risolto: servono perimetro, metodo e copertura confrontabili.',
    auditText:'Questo controllo rileva scostamenti dalla baseline salvata nella cartella del progetto. PASS significa nessuno scostamento rilevato dal controllo, non qualità certificata.',
    artifactText:'Inventario dell’artefatto fornito. Non viene compilato o eseguito; il comportamento distribuito resta da verificare.',
    reconcileText:'Le corrispondenze correlano sorgenti, artefatti ed eventuali osservazioni importate. Caricato, presente ed eseguito non sono sinonimi.',
    exportText:'Esportazione pronta. Lo schema 2.0 conserva lo snapshot pubblico; lo schema 1.5 mantiene il contratto storico.',
    selfcheckText:'Riconoscimento statico dei file delle capacità ASES. Non equivale a eseguire la suite di test.',
    kitTitle:'Documenti da scrivere, senza il foglio bianco.',kitText:'Scegli un template, compilalo e scaricalo. Qui le intenzioni le scrivi tu: il codice non può testimoniare cosa avevano in mente gli stakeholder.',
    kitGuide:'Come usare il metodo',kitDownload:'Scarica i documenti compilati ↓',kitLabel:'Documento',draft:'Contenuto del documento',
    kitMissing:'I template richiedono il checkout completo di ASES. Avvia la UI dopo l’installazione modificabile dalla cartella runtime del repository.',
    kitMemory:'Le bozze restano in questa pagina e si perdono alla chiusura o al ricaricamento. Scaricale per conservarle.',
    accuracyText:'Misura sui casi etichettati del corpus: falsi allarmi, omissioni e risultati per capacità. Non è una stima di accuratezza su qualsiasi progetto. La revisione indipendente delle etichette resta da completare.',
    optional:'opzionale',before:'Analisi precedente (.ases)',after:'Analisi successiva (.ases)',localRoot:'Cartella sorgenti per aprire le prove',artifactSnapshot:'Snapshot dell’artefatto',runtime:'Osservazioni runtime importate',schema:'Schema di esportazione',pages:'Massimo pagine (1–10)',mappings:'Mapping runtime (lista JSON)',baseline:'Baseline precedente (.ases)',extra:'Opzioni',sourceSnapshot:'Analisi sorgente (.ases)',target:'Percorso',siteUrl:'URL pubblico del sito',corpus:'Corpus etichettato (bundled = corpus incluso)',structure:'Elementi ricostruiti',noReview:'Non sono emersi candidati alla revisione dalle regole applicate. Parti dai collegamenti e dalla copertura: l’assenza di finding non dimostra l’assenza di problemi.',
  },
  en: {
    desk:'on the desk',local:'Runs on your computer',eyebrow:'A LITTLE ORDER, BEFORE THE REFACTOR',
    title:'The code is here.\nLet’s get our bearings.',lead:'One folder, one readable analysis. Then follow each clue back to the code. Including the bit everyone thought was documented.',
    folder:'Project folder',analyze:'Analyze project ↗',task:'What would you like to do?',
    inputHint:'Local path or public HTTPS Git repository URL. Documentation is generated with the analysis.',
    step1:'First, the picture.',step1p:'Structure, routes and review candidates, collected in a short answer.',
    step2:'Then, the evidence.',step2p:'Open a result and read the line behind it. No file treasure hunt.',
    step3:'You make the call.',step3p:'Static links and uncovered areas stay visible. Green is a color, not a certificate.',
    footer:'Local, temporary session. No source is uploaded to an external service. Remote repositories and websites require network access. Download the report to keep it; Ctrl+C stops ASES and removes temporary files.',
    download:'Download report ↓',clear:'Clear session',search:'Search results',
    exportMode:'What do you want to keep?',exportReduced:'Reduced report — counts only',exportFull:'Complete package — documents and reviews',
    overview:'The picture',findings:'To review',entities:'Explore links',files:'Coverage',documents:'Documents',
    observations:'Observations',behaviors:'Recovered paths',controls:'Local controls',tests:'Test declarations',external_systems:'External boundaries',structural_relations:'Static relations',unknowns:'Unknowns',hints:'Weak hints',suppressed:'Suppressed results',
    running:'Analyzing. Reading sources; the project is not being started.',complete:'Analysis ready. Project tests were not executed.',
    working:'Operation in progress…',done:'Operation completed. Read the result and its limits.',failed:'The operation did not complete.',noSession:'Open the session link printed by ases ui in your terminal.',
    summary:'Here is what turns up.',limits:'A map, not a verdict.',limitsText:'An observed declaration, an inferred link and an uncovered area are different things. They stay separate here.',
    start:'Where to begin',startText:'Open review candidates, follow their evidence and check the context. No findings does not automatically mean no problems.',
    browse:'Explore routes and symbols →',review:'Open results →',coverage:'See the limits →',
    sourceFiles:'source files inventoried',routeCount:'routes recovered',reviewCount:'review candidates',
    findingsDesc:'Suggestions and contradictions first, then observed results. Rules describe signals, not verdicts.',
    entitiesDesc:'Choose a route or symbol. See the evidence, its callers and what it reaches in the static graph.',
    filesDesc:'Method coverage by file and relation family. This is not an accuracy percentage.',
    select:'Choose a result to see evidence and links.',empty:'No results in this selection. Coverage still needs checking.',
    confidence:'Confidence',assumptions:'Assumptions',counter:'Counter-evidence',guidance:'What to consider',evidence:'Source evidence',
    missingEvidence:'No source location is available for this item.',forward:'What it reaches →',backward:'← What calls it',
    trace:'Recovered links',traceLimit:'Static links, not an execution trace. Expansion is limited to 64 nodes; attached endpoints may add more.',
    noLinks:'No admitted links found: this does not prove runtime isolation.',unknownLabel:'Coverage',raw:'Full details',previous:'← Previous',next:'Next →',results:'results',
    docsTitle:'The documentation is already on the desk.',docsText:'These documents were recovered from available sources. They are not approved requirements or decisions attributed to the original authors. Open them here or download the entire report.',
    docSummary:'A first reading of results and limitations.',docOverview:'System structure recovered from source.',docQuality:'Coverage, unknowns and extraction limits.',docRad:'Recovered analysis model: review it with the people involved.',docSdd:'Observed or inferred architecture and relationships.',docOdd:'Structural details and review candidates.',docTesting:'Test declarations and links; no tests executed.',docOther:'Recovered data and its links.',
    openDoc:'Open document',closeDoc:'Close document',snapshot:'Snapshot identity',json:'Complete data (JSON)',
    siteSummary:'Public pages were observed, without running JavaScript or accessing backend source.',
    sitePages:'pages observed',siteForms:'forms observed',siteLimits:'A published site does not reveal the whole system. Internal routes, effective authorization and runtime behavior remain unverified.',
    operation:'The result, with its boundaries.',operationText:'This summary uses the data returned by ASES. The archive contains the complete result.',
    compareText:'Differences describe two analyses. A missing item is not automatically a resolved issue: scope, method and coverage must be comparable.',
    auditText:'This checks drift against the baseline stored in the project folder. PASS means no drift detected by this check, not certified quality.',
    artifactText:'Inventory of the supplied artifact. Nothing is built or executed; deployed behavior still needs verification.',
    reconcileText:'Matches correlate source, artifacts and optional imported observations. Loaded, present and executed are different claims.',
    exportText:'Export ready. Schema 2.0 preserves the public snapshot; schema 1.5 keeps the historical contract.',
    selfcheckText:'Static recognition of ASES capability files. This does not run the test suite.',
    kitTitle:'Engineering documents, without the blank page.',kitText:'Choose a template, fill it in and download it. You supply the intentions: source code cannot testify to what stakeholders originally meant.',
    kitGuide:'How to use the method',kitDownload:'Download your documents ↓',kitLabel:'Document',draft:'Document content',
    kitMissing:'Templates require the full ASES checkout. Start the UI after an editable installation from the repository runtime folder.',
    kitMemory:'Drafts stay in this page and are lost on close or reload. Download them to keep them.',
    accuracyText:'Measurement on the labeled corpus: false alarms, omissions and per-capability results. This is not an accuracy estimate for arbitrary projects. Independent label review remains pending.',
    optional:'optional',before:'Previous analysis (.ases)',after:'Next analysis (.ases)',localRoot:'Source folder for evidence previews',artifactSnapshot:'Artifact snapshot',runtime:'Imported runtime observations',schema:'Export schema',pages:'Maximum pages (1–10)',mappings:'Runtime mappings (JSON list)',baseline:'Previous baseline (.ases)',extra:'Options',sourceSnapshot:'Source analysis (.ases)',target:'Path',siteUrl:'Public website URL',corpus:'Labeled corpus (bundled = included corpus)',structure:'Recovered elements',noReview:'No review candidates were recovered by the applied rules. Start with links and coverage: no findings does not prove no problems.',
  }
};
const t = key => words[language][key] || key;
Object.assign(words.it,{
  kitMemory:'Le bozze vengono conservate in questo browser. Scaricale per avere una copia indipendente; le annotazioni dell’analisi sono incluse anche nel rapporto.',
  docRad:'Requisiti documentati, comportamenti osservati, scenari e punti da confermare.',docOdd:'Package, firme, contratti dichiarati e diagrammi statici.',
  docsText:'Qui trovi ciò che dichiarano i documenti e ciò che si vede nel codice, con fonti separate. Puoi correggere la lettura, seguire i riferimenti e scaricare tutto.',
  workspace:'SPAZIO DI LAVORO',newProject:'Nuova analisi',currentResult:'Risultati',openSaved:'Apri analisi salvata',tools:'Altri strumenti',method:'Metodo e template',
  sessionNote:'Report temporanei. Scaricali per conservarli.',chooseFolder:'Scegli cartella…',inProgress:'ANALISI IN CORSO',cancel:'Interrompi',cancelling:'Sto interrompendo…',cancelled:'Analisi interrotta. Puoi modificare il perimetro e riprovare.',
  errorTitle:'Non ho completato questa operazione',retryHint:'Correggi il percorso o restringi il perimetro e riprova. L’ultima analisi completata resta disponibile.',retry:'Torna al progetto',
  title:'Capisci il progetto,\nprima di cambiarlo.',eyebrow:'NUOVA ANALISI',lead:'Scegli una cartella o incolla l’URL di un repository. ASES prepara una lettura del codice, i punti da verificare e la documentazione.',
  folder:'Progetto da analizzare',analyze:'Avvia analisi',inputHint:'Cartella locale o URL HTTPS di un repository pubblico. Il codice viene letto, mai avviato.',
  footer:'Tutto resta sul computer. Repository remoti e siti richiedono rete. Ctrl+C nel terminale chiude la sessione e rimuove i report temporanei.',
  step1:'Una risposta leggibile',step1p:'Struttura del progetto e risultati principali, raccolti in una pagina.',step2:'Le prove a un clic',step2p:'Dal risultato alla riga di codice, con collegamenti da seguire e verificare.',step3:'Documenti pronti',step3p:'Panoramica, architettura e baseline dei test, da leggere o scaricare.',
  summary:'Cosa ho trovato',limits:'Cosa resta da verificare',limitsText:'I collegamenti descrivono una ricostruzione statica. Verifica il comportamento eseguendo i test del progetto.',
  start:'Il prossimo passo',findings:'Risultati da rivedere',entities:'Mappa del codice',reviewCount:'proposte da verificare',sourceFiles:'sorgenti nel perimetro',
  exclude:'Escludi cartelle o file',excludeHint:'Un pattern per riga, per esempio work/** o experiments/**. Si applicano solo a questa analisi.',
  excluded:'Cartelle fuori perimetro',excludedHint:'Queste directory non sono state analizzate. Non possiamo dedurre l’assenza di problemi al loro interno.',
  scopeLimit:'Il perimetro è troppo grande per la UI: massimo 5.000 sorgenti, 128 MiB totali e 2 MiB per file. Escludi dipendenze, copie o esperimenti nelle opzioni e riprova. La CLI resta disponibile per scansioni più grandi.',
  documentPreview:'Anteprima abbreviata. Il documento completo è nel rapporto scaricabile.',downloadWorking:'Preparo il rapporto…',emptyReview:'Non sono emerse proposte da rivedere. Puoi comunque esplorare il codice e controllare la copertura.',
});
Object.assign(words.en,{
  kitMemory:'Drafts are kept in this browser. Download an independent copy; analysis annotations are also included in the report.',
  docRad:'Documented requirements, observed behavior, scenarios and open questions.',docOdd:'Packages, signatures, declared contracts and static diagrams.',
  docsText:'Read what the documents declare and what the source shows, with separate evidence. Review the interpretation, follow references and download the complete package.',
  workspace:'WORKSPACE',newProject:'New analysis',currentResult:'Results',openSaved:'Open saved analysis',tools:'More tools',method:'Method & templates',
  sessionNote:'Temporary reports. Download them to keep them.',chooseFolder:'Choose folder…',inProgress:'ANALYSIS IN PROGRESS',cancel:'Stop analysis',cancelling:'Stopping…',cancelled:'Analysis stopped. Adjust the scope and try again.',
  errorTitle:'This operation did not complete',retryHint:'Correct the path or narrow the scope and try again. Your last completed analysis is still available.',retry:'Back to the project',
  title:'Understand the project\nbefore changing it.',eyebrow:'NEW ANALYSIS',lead:'Choose a folder or paste a repository URL. ASES prepares a reading of the code, points to check and documentation.',
  folder:'Project to analyze',analyze:'Start analysis',inputHint:'Local folder or public HTTPS Git repository URL. Code is read, never started.',
  footer:'Everything stays on this computer. Remote repositories and websites require network access. Ctrl+C in the terminal ends the session and removes temporary reports.',
  step1:'A readable answer',step1p:'Project structure and main results, collected on one page.',step2:'Evidence one click away',step2p:'From a result to the source line, with links you can follow and check.',step3:'Documents ready',step3p:'Overview, architecture and test baseline, ready to read or download.',
  summary:'What turned up',limits:'What still needs checking',limitsText:'Links describe a static reconstruction. Check behavior by running the project tests.',
  start:'Your next step',findings:'Results to review',entities:'Code map',reviewCount:'suggestions to check',sourceFiles:'source files in scope',
  exclude:'Exclude folders or files',excludeHint:'One pattern per line, such as work/** or experiments/**. Applies to this analysis only.',
  excluded:'Folders outside the scope',excludedHint:'These directories were not analyzed. No absence of problems can be inferred inside them.',
  scopeLimit:'The scope exceeds the desk limits: 5,000 source files, 128 MiB total or 2 MiB per file. Exclude dependencies, copies or experiments in the options and try again. The CLI supports larger intentional scans.',
  documentPreview:'Preview shortened. The download contains the complete document.',downloadWorking:'Preparing report…',emptyReview:'No review suggestions were recovered. You can still explore the code and check coverage.',
});
const actionNames = {
  interpret:['Interpreta con un modello locale','Interpret with a local model'],
  'runtime-check':['Confronta osservazioni HTTP','Compare HTTP observations'],
  scan:['Analizza un progetto + crea i documenti','Analyze a project + generate documents'],
  site:['Osserva un sito pubblico','Observe a public website'],
  open:['Apri un’analisi salvata','Open a saved analysis'],
  compare:['Confronta due analisi','Compare two analyses'],
  artifact:['Analizza un artefatto di build','Inspect a build artifact'],
  reconcile:['Collega sorgenti, artefatti e runtime','Reconcile source, artifact and runtime'],
  audit:['Controlla gli scostamenti dalla baseline','Check drift against the project baseline'],
  export:['Esporta un’analisi','Export an analysis'],
  selfcheck:['Controlla le capacità di ASES','Check ASES capabilities'],
  accuracy:['Misura l’accuratezza su un corpus','Measure accuracy on a corpus'],
  clean:['Pulisci un output ASES salvato','Clean a saved ASES output'],
  kit:['Scrivi documenti con il metodo ASES','Write documents with the ASES method'],
};
Object.assign(words.it,{localEndpoint:'Server del modello locale (solo 127.0.0.1 o ::1)',provider:'Provider locale',llmProvider:'Server LLM locale',glinerProvider:'GLiNER2 offline',pythonExecutable:'Percorso del runtime Python locale',modelPath:'Cartella del modello GLiNER2 già presente',httpObservations:'File JSON delle osservazioni HTTP',interpretText:'Lettura opzionale di un campione di brani tramite il provider locale scelto. Produce ipotesi citate: non modifica i requisiti recuperati.', 'runtime-checkText':'Confronta osservazioni fornite con lo snapshot, senza inviare richieste al progetto.'});
Object.assign(words.en,{localEndpoint:'Local model server (127.0.0.1 or ::1 only)',provider:'Local provider',llmProvider:'Local LLM server',glinerProvider:'Offline GLiNER2',pythonExecutable:'Local Python runtime path',modelPath:'Existing GLiNER2 model directory',httpObservations:'HTTP observations JSON file',interpretText:'Optional interpretation of a sample of excerpts through the selected local provider. Cited hypotheses stay separate from recovered requirements.', 'runtime-checkText':'Compare supplied observations with the snapshot without sending target requests.'});
const labelAction = action => actionNames[action][language === 'it' ? 0 : 1];
function button(text, action, className='text-button') {
  const b = el('button', text, className); b.type='button';
  b.addEventListener('click', () => Promise.resolve().then(action).catch(showError));
  return b;
}
function showError(error) {
  const message=error.message || String(error);
  let readable=message.includes('UI_SCOPE_LIMIT')?t('scopeLimit'):message;
  if(language==='it'&&message.includes('folder picker is unavailable'))readable='La selezione di cartelle del sistema non è disponibile. Incolla il percorso nel campo del progetto.';
  if(language==='it'&&message.includes('Not a directory:'))readable='Non trovo la cartella indicata. Controlla il percorso del progetto e riprova.';
  if(language==='it'&&message.includes('Requirement ID already exists'))readable='Questo ID di requisito esiste già. Scegli un ID diverso: la dichiarazione originale viene conservata.';
  if(language==='it'&&message.includes('User requirement needs bounded nonempty'))readable='Compila requisito, autore, ambito e criterio di accettazione con testo non vuoto, entro i limiti indicati.';
  if(language==='it'&&message.includes('Requirement ID uses letters'))readable='Nell’ID usa lettere, numeri, punti, trattini, due punti o underscore, senza spazi.';
  if(language==='it'&&message.includes('The session changed'))readable='La sessione è cambiata. Riapri l’analisi corrente prima di salvare la revisione.';
  $('error').textContent=readable;
  $('error-panel').hidden=false;
}
function clearError() { $('error-panel').hidden=true; $('error').textContent=''; }
async function api(path, options={}) {
  const headers = {'X-ASES-Token':token, ...options.headers};
  if (report?.snapshot_id && /^(items|source|trace|document|download|engineering|engineering-source|engineering-review)(\?|$)/.test(path)) headers['X-ASES-Snapshot']=report.snapshot_id;
  const response = await fetch('/api/'+path, {...options, headers, cache:'no-store'});
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.error || response.statusText);
  }
  return response;
}
const json = async (path, options) => (await api(path, options)).json();
const post = (path, body) => ({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
function renderLanguage() {
  document.documentElement.lang=language;
  document.title=language==='it'?'ASES — sul tavolo':'ASES — on the desk';
  document.querySelectorAll('[data-t]').forEach(node=>node.textContent=t(node.dataset.t));
  renderExportNotice();
  $('language').textContent=language==='it'?'EN':'IT';
  $('language').setAttribute('aria-label',language==='it'?'Switch to English':'Passa all’italiano');
  $('title').textContent=t('title');
  $('search').placeholder=language==='it'?'Nome, percorso, stato…':'Name, path, state…';
  const current=$('task').value || 'scan';
  $('task').replaceChildren(...Object.keys(actionNames).map(action=>{
    const option=el('option',labelAction(action)); option.value=action; return option;
  }));
  $('task').value=current;
  configureForm(false);
  if(report&&workspaceView==='report') renderReport();
  if(workspaceView==='tools')renderTools();
  if(lastStatus&&busy)renderProgress(lastStatus);
}
function extraField(name, label, {value='',optional=true,type='text'}={}) {
  const wrap=el('div',undefined,'field');
  const l=el('label',t(label)+(optional?' ('+t('optional')+')':''));
  l.htmlFor='option-'+name;
  const field=el(type==='textarea'?'textarea':'input');
  field.id='option-'+name; field.name=name; field.value=value;
  if(type!=='textarea') field.type=type;
  field.required=!optional;
  if(name==='pages'){field.min='1';field.max='10';}
  wrap.append(l,field);return wrap;
}
function configureForm(reset=true) {
  const action=$('task').value;
  if(reset && action!==activeAction){sourcesByAction[activeAction]=$('source').value;$('source').value=sourcesByAction[action]||(action==='accuracy'?'bundled':'');activeAction=action;}
  const old={}; $('extra-fields').querySelectorAll('input,textarea,select').forEach(n=>old[n.name]=n.value);
  $('extra-fields').replaceChildren();
  $('kit').hidden=action!=='kit';
  $('source').closest('.input-row').hidden=action==='kit';
  $('source').required=action!=='kit';
  $('scan-form').querySelector('label[for=source]').hidden=action==='kit';
  $('scan-form').querySelector('.hint').hidden=action==='kit';
  const sourceLabel=action==='accuracy'?'corpus':action==='site'?'siteUrl': ['open','compare','reconcile','export','clean','interpret','runtime-check'].includes(action)?(action==='compare'?'before':'sourceSnapshot'):action==='artifact'?'target':'folder';
  $('scan-form').querySelector('label[for=source]').textContent=t(sourceLabel);
  $('source').placeholder=action==='site'?'https://example.org':action==='scan'?'C:\\projects\\bookshop  /  https://github.com/owner/repo':action==='open'||action==='compare'||action==='export'||action==='reconcile'?'C:\\reports\\previous.ases':'C:\\projects\\bookshop';
  $('scan').textContent=action==='scan'?t('analyze'):labelAction(action)+' ↗';
  const add=(name,label,opts={})=>$('extra-fields').append(extraField(name,label,{...opts,value:reset?opts.value||'':old[name]??opts.value??''}));
  if(action==='scan'){
    const details=el('details');details.append(el('summary',t('extra')),extraField('exclude','exclude',{value:reset?'':old.exclude||'',type:'textarea'}),el('p',t('excludeHint'),'muted'),extraField('baseline','baseline',{value:reset?'':old.baseline||''}));$('extra-fields').append(details);
  }
  if(action==='site') add('pages','pages',{value:'5',optional:false,type:'number'});
  if(action==='open') add('other','localRoot');
  if(action==='compare') add('other','after',{optional:false});
  if(action==='interpret'){
    const wrap=el('div',undefined,'field'),label=el('label',t('provider')),select=el('select');
    select.name='provider';select.id='option-provider';label.htmlFor=select.id;
    for(const [value,key] of [['llm','llmProvider'],['gliner2','glinerProvider']]){const option=el('option',t(key));option.value=value;select.append(option);}
    select.value=old.provider||'llm';wrap.append(label,select);$('extra-fields').append(wrap);
    add('endpoint','localEndpoint',{value:'http://127.0.0.1:8080/v1',optional:true});
    add('python_executable','pythonExecutable',{optional:true});
    add('model_path','modelPath',{optional:true});
    const updateProviderFields=()=>{
      const gliner=select.value==='gliner2';
      $('option-endpoint').required=!gliner;
      $('option-python_executable').required=gliner;
      $('option-model_path').required=gliner;
    };
    select.addEventListener('change',updateProviderFields);updateProviderFields();
  }
  if(action==='runtime-check') add('other','httpObservations',{optional:false});
  if(action==='reconcile'){
    add('other','artifactSnapshot',{optional:false});add('baseline','runtime');add('mappings','mappings',{value:'[]',type:'textarea'});
  }
  if(action==='export'){
    const wrap=el('div',undefined,'field'),label=el('label',t('schema')),select=el('select');
    select.name='schema';select.id='option-schema';label.htmlFor=select.id;
    for(const version of ['2.0','1.5']) { const option=el('option',version);option.value=version;select.append(option); }
    if(!reset&&old.schema)select.value=old.schema;wrap.append(label,select);$('extra-fields').append(wrap);
  }
  if(action==='kit') loadKit().catch(showError);
  $('scan').hidden=action==='kit';
  $('choose-folder').hidden=!['scan','artifact','audit','selfcheck','open'].includes(action);
  $('title').textContent=action==='scan'?t('title'):labelAction(action);
  $('lead').textContent=action==='scan'?t('lead'):toolDescription(action);
}
async function run(event) {
  event.preventDefault();clearError();
  if($('task').value==='kit'||busy) return;
  generation++; requestNumber++; selectedItem=null;
  busy=true;$('scan').disabled=true;$('task').disabled=true;
  $('status').textContent='';$('scan-form').hidden=true;$('cancel').disabled=false;$('cancel').textContent=t('cancel');
  showWorkspace('form');renderProgress({stage:'starting',elapsed:0});
  const options={};new FormData($('scan-form')).forEach((value,key)=>{if(!['source','task'].includes(key))options[key]=value;});
  try {
    await json('scan',post('scan',{source:$('source').value,action:$('task').value,options}));
    await poll();
  }catch(error){showError(error);finishBusy();}
}
function finishBusy() {
  busy=false;$('scan').disabled=false;$('task').disabled=false;$('scan-form').hidden=false;$('job').hidden=true;
  $('current-result').disabled=!report;$('current-docs').disabled=!report||report.kind!=='scan';
  if(workspaceView==='form')$('introduction').hidden=false;
}
async function poll() {
  const state=await json('status');
  lastStatus=state;
  if(state.has_result&&!report)report=await json('report');
  if(['running','cancelling'].includes(state.status)){busy=true;$('scan-form').hidden=true;renderProgress(state);setTimeout(()=>poll().catch(error=>{showError(error);finishBusy();}),700);return;}
  finishBusy();
  if(state.status==='failed'){showWorkspace('form');throw new Error(state.error);}
  if(state.status==='cancelled'){showWorkspace('form');$('status').textContent=t('cancelled');return;}
  if(state.status==='complete'){
    report=await json('report');page='overview';offset=0;$('search').value='';
    $('status').textContent='';
    renderReport();
  }
}
function toolDescription(action){
  const descriptions={
    interpret:[words.it.interpretText,words.en.interpretText],
    'runtime-check':[words.it['runtime-checkText'],words.en['runtime-checkText']],
    open:['Riapri una cartella .ases per leggere risultati e documenti. Puoi indicare anche i sorgenti per aprire le prove.','Reopen an .ases folder to read results and documents. Attach its source folder to preview evidence.'],
    compare:['Confronta due analisi salvate: finding, struttura e differenze che restano incerte.','Compare saved analyses: findings, structure and differences that remain uncertain.'],
    site:['Osserva un campione di pagine pubbliche, form e script. Il backend resta fuori da questa osservazione.','Observe a sample of public pages, forms and scripts. The backend remains outside this observation.'],
    artifact:['Leggi un artefatto locale e le sue source map, senza compilarlo o eseguirlo.','Read a local artifact and its source maps, without building or executing it.'],
    reconcile:['Correla uno snapshot sorgente con un artefatto e, se disponibili, osservazioni runtime importate.','Correlate a source snapshot with an artifact and optional imported runtime observations.'],
    audit:['Cerca scostamenti rispetto alla baseline salvata nella cartella del progetto.','Check for drift against the baseline saved in the project folder.'],
    export:['Prepara un’esportazione JSON nel contratto 1.5 o 2.0.','Prepare a JSON export using contract 1.5 or 2.0.'],
    selfcheck:['Controlla il riconoscimento statico delle capacità di ASES. Per eseguire i test, usa TESTING.md.','Check static recognition of ASES capabilities. Use TESTING.md to run its tests.'],
    accuracy:['Misura falsi allarmi e omissioni su casi etichettati. Non è un voto universale allo scanner.','Measure false alarms and omissions on labeled cases. This is not a universal scanner score.'],
    clean:['Prima vedi l’output riconosciuto e il suo contenuto; poi puoi confermarne la rimozione.','Preview a recognized output and its contents before confirming removal.'],
    kit:[t('kitText'),t('kitText')],
  };
  return descriptions[action]?.[language==='it'?0:1]||t('lead');
}
function showWorkspace(view){
  workspaceView=view;
  $('introduction').hidden=view!=='form'||busy;$('analysis').hidden=view!=='report';$('tools').hidden=view!=='tools';$('kit').hidden=view!=='kit';
  $('welcome').hidden=view!=='form'||$('task').value!=='scan'||busy;
  $('job').hidden=!busy;
  $('current-result').disabled=!report;$('current-docs').disabled=!report||report.kind!=='scan';
  const active=view==='tools'?'open-tools':view==='kit'?'open-kit':view==='report'?(page==='documents'?'current-docs':'current-result'):$('task').value==='open'?'open-snapshot':'new-project';
  document.querySelectorAll('.nav-item').forEach(b=>b.setAttribute('aria-current',b.id===active?'page':'false'));
}
function selectTask(action){
  if(busy){$('job').hidden=false;return;}
  clearError();$('status').textContent='';$('task').value=action;configureForm();showWorkspace(action==='kit'?'kit':'form');
  if(action!=='kit')$('source').focus();
}
function renderTools(){
  const target=$('tools');target.replaceChildren(el('p',t('tools'),'eyebrow'),el('h1',language==='it'?'Un compito alla volta.':'One task at a time.'));
  const grid=el('div',undefined,'tools-grid');
  Object.keys(actionNames).filter(action=>!['scan','open','kit'].includes(action)).forEach(action=>{
    const b=button('',()=>selectTask(action),'tool');b.append(el('h2',labelAction(action)),el('p',toolDescription(action)),el('span','→'));grid.append(b);
  });target.append(grid);
}
function renderProgress(state){
  $('job').hidden=false;
  $('introduction').hidden=true;$('welcome').hidden=true;
  $('job-title').textContent=$('source').value.split(/[\\/]/).filter(Boolean).pop()||labelAction($('task').value);
  const openingSnapshot=$('task').value==='open';
  const names=openingSnapshot?(language==='it'?['Riapertura snapshot']:['Reopening snapshot']):language==='it'?['Perimetro dei file','Lettura dei sorgenti','Struttura e collegamenti','Verifiche e documenti','Preparazione del rapporto']:['File scope','Reading source','Structure and links','Checks and documents','Preparing report'];
  const indices={starting:0,inventory:0,clone:0,java:1,javascript:1,python:1,frontend:1,relations:2,model:2,validation:3,documents:3,'document-inputs':3,'document-analysis':3,'document-api':3,'behavior-interpretation':3,'document-rendering':3,presentation:4,complete:4};
  const current=openingSnapshot?0:indices[state.stage];
  const specific=language==='it'?{java:'Leggo i sorgenti Java',javascript:'Leggo JavaScript e TypeScript',python:'Leggo i sorgenti Python',frontend:'Leggo componenti e template','document-inputs':'Leggo la documentazione del progetto','document-analysis':'Interpreto le dichiarazioni nei documenti','document-api':'Ricostruisco interfacce e firme','behavior-interpretation':'Interpreto condizioni, risultati ed errori nel codice','document-rendering':'Scrivo i documenti e salvo le prove'}:{java:'Reading Java source',javascript:'Reading JavaScript and TypeScript',python:'Reading Python source',frontend:'Reading components and templates','document-inputs':'Reading project documentation','document-analysis':'Interpreting document declarations','document-api':'Recovering interfaces and signatures','behavior-interpretation':'Interpreting conditions, outcomes and errors in source','document-rendering':'Writing documents and saving evidence'};
  Object.assign(specific,language==='it'?{clone:'Scarico il repository pubblico',site:'Osservo le pagine pubbliche',artifact:'Leggo l’artefatto fornito',open:'Apro lo snapshot salvato',compare:'Confronto le due analisi',reconcile:'Correlazione di sorgenti e artefatti',export:'Preparo l’esportazione',accuracy:'Verifico il corpus etichettato',clean:'Controllo l’output da rimuovere'}:{clone:'Downloading public repository',site:'Observing public pages',artifact:'Reading supplied artifact',open:'Opening saved snapshot',compare:'Comparing analyses',reconcile:'Correlating source and artifact',export:'Preparing export',accuracy:'Evaluating labeled corpus',clean:'Checking output to remove'});
  $('stage').textContent=state.status==='cancelling'?t('cancelling'):openingSnapshot?specific.open:specific[state.stage]||names[current]||(language==='it'?'Analisi in corso':'Analysis in progress');
  const seconds=Math.floor(state.elapsed||0);$('elapsed').textContent=(language==='it'?'Tempo trascorso: ':'Elapsed: ')+Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0');
  $('job-stages').replaceChildren(...names.map((name,index)=>el('li',name,index<current?'done':index===current?'active':'')));
}
function renderReport() {
  showWorkspace('report');
  $('report-title').textContent=report.project?.name || labelAction(report.action);
  $('report-caption').textContent=report.kind==='scan'?(language==='it'?'Ultima analisi completata. Test del progetto non eseguiti.':'Last completed analysis. Project tests were not executed.'):t('done');
  $('project-label').textContent=labelAction(report.action);
  const pages=report.kind==='scan'?['overview','findings','entities','files','documents']:['overview'];
  $('tabs').replaceChildren(...pages.map(key=>{
    const b=button(t(key),()=>navigate(key),'');b.setAttribute('aria-current',page===key?'page':'false');return b;
  }));
  $('overview').hidden=page!=='overview';$('browser').hidden=!['findings','entities','files'].includes(page);
  $('documents').hidden=page!=='documents';
  if(page==='overview')renderOverview();
  else if(page==='documents')renderDocuments();
  else setupBrowser();
}
function navigate(key,collection=null) {
  clearError();page=key;requestedCollection=collection;offset=0;selectedItem=null;requestNumber++;$('search').value='';renderReport();
}
function stat(value,label) {
  const node=el('div',undefined,'number');node.append(el('strong',String(value)),el('span',label));return node;
}
function renderOverview() {
  const target=$('overview');target.replaceChildren();
  if(report.kind==='operation'){renderOperation(target);return;}
  const grid=el('div',undefined,'overview-grid'),summary=el('div',undefined,'summary'),note=el('aside',undefined,'note');
  summary.append(el('h2',t('summary')));
  const site=report.action==='site';
  if(site)summary.append(el('p',t('siteSummary')));
  else{
    const structure=report.structure||{},parts=[];
    const names=language==='it'?{controller:['controller','controller'],service:['servizio','servizi'],repository:['repository','repository'],class:['classe','classi'],function:['funzione','funzioni'],frontend_component:['componente frontend','componenti frontend']}:{controller:['controller','controllers'],service:['service','services'],repository:['repository','repositories'],class:['class','classes'],function:['function','functions'],frontend_component:['frontend component','frontend components']};
    for(const kind of ['controller','service','repository','class','function','frontend_component'])if(structure[kind])parts.push(structure[kind]+' '+names[kind][structure[kind]===1?0:1]);
    summary.append(el('p',(language==='it'?'Nel codice ho ricostruito: ':'Recovered from the code: ')+(parts.length?parts.join(', '):report.counts.entities+' '+(language==='it'?'elementi strutturali':'structural elements'))+'.'));
    summary.append(el('p',report.counts.routes?(language==='it'?'Le route riconosciute si possono seguire fino agli handler e ai collegamenti statici supportati.':'Recognized routes can be followed to their handlers and supported static links.'):(language==='it'?'Non sono state ricostruite route nelle forme supportate. Puoi esplorare i simboli e le dipendenze rilevati.':'No routes were recovered in supported forms. You can explore recovered symbols and dependencies.')));
    if(report.custom_http_routing_unresolved)summary.append(el('p',language==='it'?'Il routing HTTP Python personalizzato è interpretato parzialmente: le tabelle esatte nelle forme supportate sono ricostruite; prefissi, collegamenti dinamici e registrazione effettiva possono restare sconosciuti.':'Custom Python HTTP routing is interpreted partially: supported exact-match tables are reconstructed; prefixes, dynamic links and runtime registration may remain unknown.','warning'));
  }
  const numbers=el('div',undefined,'numbers');
  if(site){
    const pages=report.data?.pages||[];
    numbers.append(stat(report.data?.counts?.pages??pages.length,t('sitePages')),stat(report.data?.counts?.forms??pages.reduce((n,p)=>n+(p.forms||[]).length,0),t('siteForms')));
  }else numbers.append(stat(report.counts.files,t('sourceFiles')),stat(report.counts.routes,t('routeCount')),stat(report.counts.review,t('reviewCount')));
  summary.append(numbers,el('h3',t('start')));
  summary.append(el('p',site?t('siteLimits'):report.counts.review?(language==='it'?'Parti dai risultati da verificare: ogni proposta ha motivazioni e prove da aprire.':'Start with the results to check: each suggestion has reasons and evidence you can open.'):(language==='it'?'Non sono emerse proposte di modifica dalle regole applicate. Parti dalla mappa del codice e dalla panoramica già generata.':'The applied rules recovered no change suggestions. Start with the code map and the generated overview.')));
  const actions=el('div',undefined,'next-actions');
  actions.append(button(report.counts.review?t('review'):report.counts.routes?(language==='it'?'Segui le route →':'Follow the routes →'):(language==='it'?'Esplora il codice →':'Explore code →'),()=>navigate(report.counts.review?'findings':'entities',report.counts.review?null:report.counts.routes?'routes':'entities'),'primary'));
  actions.append(button(language==='it'?'Leggi i documenti':'Read documents',()=>navigate('documents'),'secondary'));summary.append(actions);
  note.append(el('h2',t('limits')));
  if(site)note.append(el('p',t('siteLimits')));
  else{
    note.append(el('p',(language==='it'?'Copertura strutturale parziale o sconosciuta: ':'Partial or unknown structural coverage: ')+report.counts.incomplete_files+' / '+report.counts.files+' '+(language==='it'?'sorgenti.':'source files.')));
    note.append(el('p',(language==='it'?'Punti non determinati dall’analisi: ':'Unknowns recorded by the analysis: ')+report.counts.unknowns+'.'));
    note.append(el('p',t('limitsText')));
  }
  note.append(button(t('coverage'),()=>navigate('files')));
  if(report.action==='selfcheck')note.append(el('p',t('selfcheckText')),rawDetails(report.data));
  if(!site){const structure=el('details');structure.append(el('summary',t('structure')));for(const [kind,count]of Object.entries(report.structure||{})){const row=el('div',undefined,'coverage-row');row.append(el('span',kind),el('span',count));structure.append(row);}summary.append(structure);}
  const highlights=report.highlights||[];
    if(highlights.length){const block=el('section',undefined,'highlights');block.append(el('h3',language==='it'?'Risultati raggruppati':'Grouped results'));highlights.forEach(item=>{const b=button('',()=>{navigate('findings','findings');selectedItem=item;renderDetail(item,'findings');},'highlight');b.append(badge(item.status),el('span',item.pattern||item.message||item.id));if(item.group_count>1)b.append(el('span',item.group_count+' '+(language==='it'?'voci in questa famiglia':'records in this family')));block.append(b);});summary.append(block);}
    if(report.pattern_catalog){const catalog=el('details');catalog.append(el('summary',language==='it'?'Quali pattern cerca ASES?':'Which patterns does ASES look for?'),el('p',report.pattern_catalog.rules+' '+(language==='it'?'regole per ':'rules for ')+report.pattern_catalog.families.length+' '+(language==='it'?'famiglie: ':'families: ')+report.pattern_catalog.families.join(', ')),el('p',language==='it'?'Copertura parziale, non l’intero catalogo GoF. Indizi strutturali e proposte non dimostrano che un refactoring sia utile. Benchmark ed esperimenti richiedono conferma di pertinenza applicativa.':'Partial coverage, not the complete GoF catalog. Structural hints and candidates do not establish refactoring benefit. Benchmarks and experiments require confirmation of application relevance.'));summary.append(catalog);}
    if(report.design_reviews?.length){const block=el('section',undefined,'highlights');block.append(el('h3',language==='it'?'Ragionamento sul progetto':'Design reasoning'),el('p',language==='it'?'Ipotesi da approfondire e soluzioni già presenti. Nessun beneficio del refactoring è stato misurato.':'Hypotheses to investigate and existing solutions. No refactoring benefit has been measured.'));for(const item of report.design_reviews){const b=button('',()=>{navigate('findings',item.status==='HINT'?'hints':'findings');selectedItem=item;renderDetail(item,'findings');},'highlight');b.append(el('strong',item.pattern),el('span',item.design_review.verdict==='REUSE_EXISTING'?(language==='it'?'Soluzione già presente — valuta il riuso':'Existing solution — consider reuse'):(language==='it'?'Da approfondire, non una modifica richiesta':'Investigate, not a required change')),el('span',item.design_review.problem?.[language]||item.message));block.append(b);}summary.append(block);}
    if(!site){const coverage=el('details');coverage.append(el('summary',language==='it'?'Dove è stato applicato il ragionamento?':'Where was design reasoning applied?'));const data=report.design_review_coverage;if(!data)coverage.append(el('p',language==='it'?'Questo snapshot non registra la copertura delle valutazioni di responsabilità. Non possiamo ricavarla dall’assenza di suggerimenti; serve una nuova scansione.':'This snapshot does not record responsibility-review coverage. Absence of suggestions cannot establish it; a new scan is needed.'));else{const counts=data.counts||{},labels=language==='it'?{ANALYZED:'Regole applicate',UNKNOWN:'Non valutati',NOT_SUPPORTED:'Non supportati'}:{ANALYZED:'Rules applied',UNKNOWN:'Not assessed',NOT_SUPPORTED:'Not supported'};for(const [key,label]of Object.entries(labels))coverage.append(el('p',label+': '+(counts[key]||0)));const modern=(data.files||[]).some(row=>row.method==='syntax-responsibilities/2');coverage.append(el('p',language==='it'?(modern?'Regole limitate su sintassi e nomi per Python, JavaScript/TypeScript e Java. Non è comprensione completa del dominio. Nessun suggerimento non significa nessun problema.':'Questo snapshot usa le precedenti regole limitate per Python. Gli altri linguaggi non ricevono queste valutazioni. Nessun suggerimento non significa nessun problema.'):(modern?'Bounded syntax/name rules for Python, JavaScript/TypeScript and Java. This is not complete domain understanding. No suggestion does not mean no problem.':'This snapshot uses the earlier bounded Python rules. Other languages do not receive these responsibility reviews. No suggestion does not mean no problem.')));const reasons=language==='it'?{bounded_rules_applied:'regole limitate applicate',language_not_supported:'linguaggio non supportato da questo metodo',source_byte_limit:'file oltre il limite di lettura',syntax_node_limit:'struttura oltre il limite di nodi',syntax_unavailable:'sintassi non interpretabile',python_syntax_unavailable:'sintassi Python non interpretabile',source_structure_unavailable:'lettura strutturale non disponibile',source_unavailable_during_scan:'sorgente non disponibile durante la scansione'}:{bounded_rules_applied:'bounded rules applied',language_not_supported:'language not supported by this method',source_byte_limit:'source byte limit exceeded',syntax_node_limit:'syntax node limit exceeded',syntax_unavailable:'syntax unavailable',python_syntax_unavailable:'Python syntax unavailable',source_structure_unavailable:'source structure unavailable',source_unavailable_during_scan:'source unavailable during scan'};const rank={UNKNOWN:0,NOT_SUPPORTED:1,ANALYZED:2},rows=[...(data.files||[])].sort((a,b)=>(rank[a.status]??3)-(rank[b.status]??3)||a.path.localeCompare(b.path));const list=el('ul');for(const row of rows.slice(0,50))list.append(el('li',row.path+' — '+(reasons[row.reason]||row.reason)));coverage.append(list);if(rows.length>50)coverage.append(el('p',language==='it'?'Mostrati 50 file; la copertura completa è nel pacchetto, in scanner-findings.json.':'Showing 50 files; complete coverage is in scanner-findings.json inside the package.'));}summary.append(coverage);}
    if(report.weak_pattern_hints)summary.append(button(report.weak_pattern_hints+' '+(language==='it'?'indizi deboli — da approfondire':'weak hints — investigate further'),()=>navigate('findings','hints')));
  grid.append(summary,note);target.append(grid);
}
function renderOperation(target) {
  target.append(el('h2',t('operation')));
  if(report.action!=='clean')target.append(el('p',t(report.action+'Text')));
  target.append(el('p',t('operationText')));
  const data=report.data||{};
  if(report.action==='interpret'){
    target.append(el('h3',language==='it'?'Ipotesi da confermare':'Hypotheses to review'));
    for(const row of data.candidates||[]){const card=el('section',undefined,'doc-row');card.append(el('p',row.statement),el('p',row.kind+' · '+(language==='it'?'Non verificato':'Unverified'),'muted'),el('blockquote',row.quote));for(const loc of row.locations||[])card.append(el('p',loc.path,'muted'));target.append(card);}
    target.append(el('p',(language==='it'?'Proposte escluse: ':'Rejected proposals: ')+(data.rejected_candidates||0)+' · '+(language==='it'?'Brani senza risposta valida: ':'Excerpts without a valid answer: ')+(data.failures?.length||0)));
    for(const failure of data.failures||[])target.append(el('p',failure.reason||String(failure),'warning'));
    if(!data.candidates?.length)target.append(el('p',language==='it'?'Nessuna proposta accettata. Il modello può non essere disponibile o adeguato; lo snapshot è conservato.':'No proposal accepted. The model may be unavailable or unsuitable; the snapshot is preserved.'));
  }
  if(report.action==='runtime-check'){
    for(const row of data.matches||[])target.append(el('p',row.method+' '+row.path+' · HTTP '+row.status+' · '+row.state));
    target.append(el('p',language==='it'?'Osservazioni importate: ASES non ha eseguito né verificato in modo indipendente queste richieste.':'Imported observations: ASES did not execute or independently verify these requests.'));
  }
  if(report.action==='clean'){
    target.append(el('p',data.target),el('p',(language==='it'?'Voci nell’output: ':'Output entries: ')+data.entries),badge(data.status));
    if(data.status==='AWAITING_CONFIRMATION'){
      target.append(el('p',language==='it'?'Controlla l’anteprima qui sotto. Il pulsante elimina definitivamente solo questa cartella di output riconosciuta. Non elimina i sorgenti.':'Check the preview below. The button permanently removes only this recognized output folder. It does not remove source files.'));
      target.append(button(language==='it'?'Conferma: elimina questo output':'Confirm: remove this output',async()=>{report=await json('remove-output',post('remove-output',{fingerprint:data.fingerprint}));renderReport();},'secondary'));
    }
  }
  const counts=[];
  if(report.action==='artifact')counts.push(['files',data.counts?.files??data.files?.length??0],['unknowns',data.counts?.unknowns??data.unknowns?.length??0]);
  if(report.action==='reconcile') {
    for(const name of ['source_matches','runtime_matches'])for(const state of ['matched','ambiguous','mismatch','unknown'])counts.push([name+' / '+state,data.match_summary?.[name]?.[state]??(data[name]||[]).filter(r=>r.status===state).length]);
  }
  if(report.action==='audit')counts.push(['status',data.status],['baseline_present',data.baseline_present],['source_fingerprint_changed',data.source_fingerprint_changed]);
  if(report.action==='compare'){
    if(data.engineering){
      const section=el('section',undefined,'engineering-change-summary'),d=data.engineering;
      section.append(el('h3',language==='it'?'Documenti da riesaminare':'Documents to review'),el('p',(d.sections_to_review||[]).join(' · ')||(language==='it'?'Nessuna sezione indicata dai campi confrontati; non è una prova di equivalenza.':'No section indicated by compared fields; this is not proof of equivalence.')));
      section.append(el('p',language==='it'?'Le corrispondenze proposte non trasferiscono le revisioni. Un’assenza non significa risolto.':'Suggested matches do not transfer reviews. Absence does not mean resolved.'));
      const reasons=language==='it'?{'same-id':'Identità conservata','candidate-same-declaration':'Corrispondenza da confermare','candidate-relocation':'Possibile spostamento','supported-content-changed':'Contenuto supportato modificato','signature-changed':'Firma modificata','requirement-scope-changed':'Ambito del requisito modificato','human-context-changed':'Contesto dell’utente modificato','statement-changed':'Testo modificato','supported-behavior-changed':'Comportamento supportato modificato','supported-content-unchanged; inspect-source-or-formatting':'Campi supportati invariati: controlla fonte e formattazione','source-position-or-path-changed':'Posizione o percorso modificati'}:{};
      for(const row of (d.record_changes||[]).slice(0,20))section.append(el('p',(row.name||'')+' · '+(reasons[row.basis]||row.basis)+' · '+row.reasons.map(r=>reasons[r]||r).join(' · '),'item-meta'));
      if((d.record_changes||[]).length>20)section.append(el('p',language==='it'?'Altri cambiamenti nel JSON completo.':'More changes in the complete JSON.'));
      target.append(section);
    }
    Object.entries(data.findings?.summary||{}).forEach(([key,value])=>{if(typeof value!=='object')counts.push([key,value]);});
    counts.push([language==='it'?'assenze incerte (finding)':'uncertain absences (findings)',data.findings?.unknown_count||0]);
    Object.entries(data.semantic?.summary||{}).forEach(([key,value])=>counts.push(['semantic / '+key,value]));
    counts.push([language==='it'?'differenze semantiche incerte':'uncertain semantic differences',data.semantic?.uncertain_count??data.semantic?.uncertain?.length??0]);
  }
  if(report.action==='accuracy'){
    const cases=Object.values(data.cases||{});
    counts.push([language==='it'?'casi superati':'cases passing',(data.case_summary?.passed??cases.filter(c=>c.passed).length)+' / '+(data.case_summary?.total??cases.length)]);
    for(const [family,values]of Object.entries(data.families||{}))for(const key of ['true_positive','false_positive','false_negative','precision','recall','f1'])counts.push([family+' / '+key,values[key]??'—']);
    target.append(el('p',data.label_review,'muted'));
  }
  if(report.action==='export')counts.push(['schema',data.schema],['entities',data.counts?.entities??data.counts?.components??data.entities?.length??data.components?.length??0]);
  if(data.delivery?.truncated)target.append(el('p',t('documentPreview'),'muted'));
  for(const [key,value]of counts){const row=el('div',undefined,'coverage-row');row.append(el('span',key.replaceAll('_',' ')),el('span',String(value??'UNKNOWN')));target.append(row);}
  target.append(rawDetails(data,t('json')));
}
function setupBrowser() {
  $('section-title').textContent=t(page);$('section-description').textContent=t(page+'Desc');
  const collections=page==='findings'?['review','findings','hints','suppressed']:page==='files'?['files','unknowns']:['entities','routes','observations','structural_relations','behaviors','controls','tests','external_systems'];
  const previous=$('collection').value;
  const labels=language==='it'?{entities:'Simboli e dichiarazioni',routes:'Route HTTP',review:'Proposte e contraddizioni',findings:'Tutti i risultati',files:'File analizzati'}:{entities:'Symbols and declarations',routes:'HTTP routes',review:'Suggestions and contradictions',findings:'All results',files:'Analyzed files'};
  $('collection').replaceChildren(...collections.map(key=>{const option=el('option',labels[key]||t(key));option.value=key;return option;}));
  if(collections.includes(previous))$('collection').value=previous;
  if(requestedCollection&&collections.includes(requestedCollection))$('collection').value=requestedCollection;
  requestedCollection=null;
  $('detail').replaceChildren(el('p',t('select'),'muted'));
  if(page==='files'){
    const note=el('div',undefined,'coverage-summary');
    for(const [key,counts]of Object.entries(report.relationship_coverage||{})){
      const row=el('div',undefined,'coverage-row');row.append(el('span',key),el('span',Object.entries(counts).map(([s,n])=>s+': '+n).join(' · ')));note.append(row);
    }
    $('detail').append(note,el('p',t('filesDesc'),'muted'));
    const excluded=report.source_scope?.excluded_directories||[];
    if(excluded.length){const section=el('details');section.append(el('summary',t('excluded')+' ('+excluded.length+')'),el('p',t('excludedHint')));excluded.slice(0,100).forEach(row=>section.append(el('p',row.path+' — '+row.reason,'item-meta')));if(excluded.length>100)section.append(el('p',t('documentPreview')));$('detail').append(section);}
  }
  loadItems().catch(showError);
}
async function loadItems() {
  const mine=++requestNumber,epoch=generation,collection=$('collection').value;
  const data=await json('items?'+new URLSearchParams({collection,q:$('search').value,offset}));
  if(mine!==requestNumber||epoch!==generation)return;
  const target=$('items');target.replaceChildren();
  if(!data.items.length)target.append(el('p',t('empty'),'empty'));
  data.items.forEach(item=>{
    const b=button('',()=>{selectedItem=item;target.querySelectorAll('button').forEach(n=>n.setAttribute('aria-pressed','false'));b.setAttribute('aria-pressed','true');renderDetail(item,collection);},'item');
    b.setAttribute('aria-pressed',selectedItem?.id===item.id?'true':'false');
    b.append(badge(item.status||item.state||item.kind||collection),el('span',item.design_review?.problem?.[language]||item.name||item.message||item.statement||item.reason||item.path||item.relation||item.id,'item-title'));
    const location=typeof item.location==='object'?item.location?.path:item.location;
    b.append(el('span',[item.kind,item.path||location||item.basis||item.subject].filter(Boolean).join(' · '),'item-meta'));
    target.append(b);
  });
  const paging=$('paging');paging.replaceChildren();
  const prev=button(t('previous'),()=>{offset=Math.max(0,offset-data.page_size);return loadItems();},'');
  const next=button(t('next'),()=>{offset+=data.page_size;return loadItems();},'');
  prev.disabled=offset===0;next.disabled=offset+data.items.length>=data.total;
  paging.append(prev,el('span',(data.total?offset+1:0)+'–'+(offset+data.items.length)+' / '+data.total+' '+t('results')),next);
}
function badge(value) {
  const review=['OPPORTUNITY','CONTRADICTED','PARTIAL'].includes(value),unknown=['UNKNOWN','HINT','SUPPRESSED','NOT_OBSERVED'].includes(value);
  const labels=language==='it'?{OBSERVED:'Osservato nel codice',INFERRED:'Ricostruzione statica',OPPORTUNITY:'Possibile miglioramento',CONTRADICTED:'Possibile contraddizione',UNKNOWN:'Non determinato',HINT:'Indizio debole',SUPPRESSED:'Soppresso da regola',ANALYZED:'Metodo applicato',PARTIAL:'Copertura parziale',NOT_OBSERVED:'Non osservato',NOT_APPLICABLE:'Non applicabile'}:{OBSERVED:'Observed in source',INFERRED:'Static reconstruction',OPPORTUNITY:'Possible improvement',CONTRADICTED:'Possible contradiction',UNKNOWN:'Unknown',HINT:'Weak hint',SUPPRESSED:'Suppressed by rule',ANALYZED:'Method applied',PARTIAL:'Partial coverage',NOT_OBSERVED:'Not observed',NOT_APPLICABLE:'Not applicable'};
  const node=el('span',labels[value]||String(value),'badge'+(review?' review':unknown?' unknown':''));node.title=String(value);return node;
}
function rawDetails(data, title=t('raw')) {
  const details=el('details'),pre=el('pre',JSON.stringify(data,null,2).slice(0,50000),'raw-data');
  details.append(el('summary',title),pre);
  if(JSON.stringify(data).length>50000)details.append(el('p',language==='it'?'Anteprima limitata. Scarica il rapporto per il JSON completo.':'Preview limited. Download the report for complete JSON.'));
  return details;
}
function locations(item) {
  if(item.locations?.length)return item.locations;
  const values=Array.isArray(item.evidence)?item.evidence:[];
  return values.map(value=>{
    if(typeof value==='object'&&value?.path)return value;
    if(typeof value!=='string')return null;
    const match=value.match(/^(.+):(\d+)$/);
    return match?{path:match[1],line:Number(match[2])}:{path:value,line:1};
  }).filter(Boolean);
}
function renderDetail(item,collection) {
  const target=$('detail');target.replaceChildren();
  target.append(badge(item.status||item.state||item.kind||collection),el('h2',item.name||item.pattern||item.path||item.reason||item.id));
  if(item.confidence)target.append(el('p',t('confidence')+': '+item.confidence,'muted'));
  const patternReading=language==='it'?{
    'opportunity.strategy_dispatch':item.status==='OPPORTUNITY'?'La stessa selezione di alternative compare in funzioni distinte. Potrebbe esserci una politica duplicata da separare, se le alternative cambiano indipendentemente. Prima verifica che i rami svolgano davvero lo stesso ruolo.':'Una selezione fra alternative è un indizio strutturale. Mancano prove sufficienti di una politica duplicata: mantenere lo switch può essere la scelta migliore.',
    'opportunity.state_dispatch':item.status==='OPPORTUNITY'?'La stessa selezione basata sullo stato compare in funzioni distinte. Verifica se rappresenta davvero transizioni e comportamenti di uno stesso oggetto prima di considerare State.':'Il nome del selettore richiama uno stato, ma da solo non dimostra che serva State.',
    'opportunity.command_dispatch':item.status==='OPPORTUNITY'?'La stessa selezione di azioni compare in funzioni distinte. Command può avere senso se le richieste devono essere trattate come oggetti; i nomi delle azioni non lo dimostrano.':'La selezione di azioni resta un indizio: non dimostra la necessità di Command.',
    'opportunity.observer_fanout':'Il modulo contiene chiamate a più destinatari con indizi di notifica. Verifica i tipi reali, l’ordine e la gestione degli errori. Observer può aiutare se i destinatari variano indipendentemente; le normali modifiche a dizionari non bastano.'
  }[item.rule_id]:null;
  if(item.design_review){const labels=language==='it'?{problem:'Il problema da verificare',expected_benefit:'Cosa potrebbe migliorare',existing_solution:'Cosa esiste già',simpler_alternative:'La soluzione più semplice',when_not_to_apply:'Quando lasciar perdere',questions:'Cosa manca per decidere'}:{problem:'Problem to verify',expected_benefit:'Expected benefit',existing_solution:'Existing solution',simpler_alternative:'Simplest alternative',when_not_to_apply:'When to leave it alone',questions:'What is missing to decide'};target.append(el('p',item.design_review.verdict==='REUSE_EXISTING'?(language==='it'?'Soluzione già presente: valuta prima il riuso.':'Existing solution: consider reuse first.'):(language==='it'?'Ipotesi da approfondire: non è una raccomandazione confermata.':'Hypothesis to investigate: not a confirmed recommendation.')));for(const [key,label]of Object.entries(labels)){const text=item.design_review[key]?.[language];if(text)target.append(el('h3',label),el('p',text));}}
  else if(patternReading)target.append(el('p',patternReading));else if(item.message||item.statement||item.reason)target.append(el('p',item.message||item.statement||item.reason));
  if(item.group_count>1)target.append(el('p',language==='it'?'Questa è una voce rappresentativa della famiglia: '+item.group_count+' voci complessive. L’elenco completo resta consultabile nei risultati.':'This is one representative of a family containing '+item.group_count+' records. The complete list remains available in results.','muted'));
  if(item.counter_evidence?.some(reason=>reason.includes('auxiliary/experimental')))target.append(el('p',language==='it'?'Fonte in un’area di benchmark o esperimenti: la pertinenza per il codice applicativo è da confermare.':'Benchmark or experimental source: applicability to application code requires confirmation.','warning'));
  for(const [key,label]of [['guidance','guidance'],['assumptions','assumptions'],['counter_evidence','counter'],['limitations','unknownLabel']]){
    if(item.design_review&&['guidance','counter_evidence'].includes(key))continue;
    const values=Array.isArray(item[key])?item[key]:item[key]?[item[key]]:[];
    if(values.length){target.append(el('h3',t(label)));const ul=el('ul');values.forEach(v=>ul.append(el('li',typeof v==='string'?v:JSON.stringify(v))));target.append(ul);}
  }
  const locs=locations(item);
  target.append(el('h3',t('evidence')));
  if(!locs.length)target.append(el('p',t('missingEvidence'),'muted'));
  locs.forEach(loc=>target.append(button(loc.path+(loc.line?':'+loc.line:''),()=>showSource(loc,target),'evidence')));
  if(['entities','routes'].includes(collection)){
    const actions=el('div',undefined,'trace-actions');
    actions.append(button(t('forward'),()=>showTrace(item.id,'forward',target)),button(t('backward'),()=>showTrace(item.id,'backward',target)));target.append(actions);
  }
  target.append(rawDetails(item));
  if(matchMedia('(max-width:800px)').matches)target.scrollIntoView({block:'start'});
  if(locs.length)showSource(locs[0],target).catch(error=>{const p=el('p',error.message,'muted');target.append(p);});
}
async function showSource(location,target) {
  const epoch=generation,item=selectedItem,mine=++sourceRequest;
  let data;
  try{data=await json('source?'+new URLSearchParams({path:location.path,line:location.line||1}));}
  catch(error){if(epoch!==generation||mine!==sourceRequest)return;target.querySelector('.source-block')?.remove();const problem=el('div',undefined,'source-block');problem.append(el('p',language==='it'?'Non riesco ad aprire questa anteprima. Il risultato dell’analisi resta disponibile.':'This preview could not be opened. The analysis remains available.'),el('p',error.message,'muted'));target.append(problem);return;}
  if(epoch!==generation||item!==selectedItem||mine!==sourceRequest)return;
  target.querySelector('.source-block')?.remove();
  const block=el('div',undefined,'source-block'),code=el('div',undefined,'source');
  code.tabIndex=0;code.setAttribute('aria-label',data.path);
  block.append(el('h3',data.path+':'+data.line,'source-head'));
  data.lines.forEach((text,index)=>{
    const line=data.start+index,row=el('div',undefined,'source-line'+(line===data.line?' selected':''));
    row.append(el('span',String(line),'line-number'),el('code',text));code.append(row);
  });
  block.append(code);target.append(block);
  if(data.lines_truncated)block.append(el('p',language==='it'?'Le righe molto lunghe sono accorciate a 2.000 caratteri. Il file completo è stato verificato contro lo snapshot.':'Very long lines are shortened to 2,000 characters. The full file was verified against the snapshot.','muted'));
}
async function showTrace(id,direction,target) {
  const epoch=generation,item=selectedItem;
  const data=await json('trace?'+new URLSearchParams({id,direction}));
  if(epoch!==generation||item!==selectedItem)return;
  target.querySelector('.trace')?.remove();
  const trace=el('section',undefined,'trace');
  trace.append(el('h3',t('trace')),badge(data.coverage.status),el('p',t('traceLimit'),'muted'));
  if(data.coverage.truncated)trace.append(el('p',language==='it'?'Espansione troncata: scarica lo snapshot e usa la CLI per un limite maggiore.':'Expansion truncated: download the snapshot and use the CLI for a larger limit.'));
  const entities=new Map(data.entities.map(entity=>[entity.id,entity]));
  const observations=new Map(data.observations.map(o=>[o.id,o]));
  function openEntity(entity) {
    entity={...entity,locations:entity.observation_refs.flatMap(ref=>observations.get(ref)?.locations||[])};
    selectedItem=entity;renderDetail(entity,'entities');
  }
  if(!data.relations.length)trace.append(el('p',t('noLinks')));
  data.relations.forEach(relation=>{
    const from=entities.get(relation.from),to=entities.get(relation.to),row=el('div',undefined,'trace-row');
    row.append(button(from?.name||relation.from,()=>openEntity(from)),el('span','— '+relation.relation+' →'),button(to?.name||relation.to,()=>openEntity(to)),badge(relation.state||'INFERRED'));
    trace.append(row);
  });
  trace.append(rawDetails({coverage:data.coverage,residual_unknowns:data.residual_unknowns,limitations:data.limitations}));
  target.append(trace);
}
function renderDocuments() {
  const target=$('documents');target.replaceChildren(el('h2',t('docsTitle')),el('p',t('docsText')));
  const engineering=el('section',undefined,'engineering-desk');target.append(engineering);
  renderEngineering(engineering).catch(showError);
  const descriptions={'SUMMARY.md':'docSummary','SYSTEM-OVERVIEW.md':'docOverview','QUALITY.md':'docQuality','RAD.md':'docRad','SDD.md':'docSdd','ODD.md':'docOdd','TESTING.md':'docTesting'};
  const titles=language==='it'?{'SUMMARY.md':'Da dove cominciare','SYSTEM-OVERVIEW.md':'Panoramica del sistema','QUALITY.md':'Qualità e copertura','RAD.md':'Requisiti e analisi','SDD.md':'Architettura e decisioni','ODD.md':'Interfacce, firme e contratti','TESTING.md':'Il quadro dei test','TP.md':'Piano dei test','TCS.md':'Specifiche dei test','TIR.md':'Incidenti importati','TSR.md':'Risultati importati','GUIDE.md':'Uso e installazione','DOCUMENT-QUALITY.md':'Fonti lette e punti da chiarire','TRACEABILITY.yaml':'Collegamenti di tracciabilità','CONTROLS.yaml':'Controlli osservati'}:{'SUMMARY.md':'Where to begin','SYSTEM-OVERVIEW.md':'System overview','QUALITY.md':'Quality and coverage','RAD.md':'Requirements and analysis','SDD.md':'Architecture and decisions','ODD.md':'Interfaces, signatures and contracts','TESTING.md':'The test picture','TP.md':'Test plan','TCS.md':'Test specifications','TIR.md':'Imported incidents','TSR.md':'Imported results','GUIDE.md':'Usage and installation','DOCUMENT-QUALITY.md':'Sources read and open questions','TRACEABILITY.yaml':'Traceability links','CONTROLS.yaml':'Observed controls'};
  titles['OVERVIEW.md']=language==='it'?'Il progetto in breve':'The project at a glance';titles['TRACEABILITY.md']=language==='it'?'Collegamenti nei due sensi':'Links in both directions';
  const preferred=report.documents.includes('OVERVIEW.md')?'OVERVIEW.md':language==='it'?'REPORT.it.md':'REPORT.md';
  titles['REPORT.it.md']='Il rapporto da leggere';titles['REPORT.md']='Your readable report';
  const names=report.documents.filter(name=>name!==(language==='it'?'REPORT.md':'REPORT.it.md')).sort((a,b)=>(a===preferred?-1:b===preferred?1:a==='SUMMARY.md'?-1:b==='SUMMARY.md'?1:0));
  const groups={};
  for(const [key,label] of [['project',language==='it'?'Requisiti, architettura e interfacce':'Requirements, architecture and interfaces'],['tests',language==='it'?'Test e istruzioni d’uso':'Tests and usage instructions'],['evidence',language==='it'?'Copertura e dati delle prove':'Coverage and evidence data']]){
    const group=el('details',undefined,'document-group');group.append(el('summary',label));target.append(group);groups[key]=group;
  }
  names.forEach(name=>{
    const row=el('div',undefined,'doc-row');
    row.dataset.document=name;
    row.append(el('h3',titles[name]||name),el('span',name,'item-meta'),el('p',t(descriptions[name]||'docOther')),button(t('openDoc'),async()=>{
      const epoch=generation,data=await json('document?'+new URLSearchParams({name}));
      if(epoch!==generation)return;
      row.querySelector('.document-text')?.remove();
      const text=el('div',undefined,'document-text');
      text.append(button(t('closeDoc'),()=>text.remove()),name.endsWith('.md')?markdown(data.text):el('pre',data.text,'raw-data'));if(data.truncated)text.append(el('p',t('documentPreview'),'muted'));row.append(text);
    }));
    const group=['RAD.md','SDD.md','ODD.md','SYSTEM-OVERVIEW.md'].includes(name)?groups.project:['TESTING.md','TP.md','TCS.md','TIR.md','TSR.md','GUIDE.md'].includes(name)?groups.tests:groups.evidence;
    if(name===preferred||name==='SUMMARY.md')target.insertBefore(row,groups.project);else group.append(row);
  });
  const identity=el('p',t('snapshot')+': '+report.snapshot_id,'snapshot');target.append(identity);
}
async function renderEngineering(target,collection=null,query='',offset=0,record=null) {
  const epoch=generation,it=language==='it';
  const initial=!collection;collection=collection||'requirements';
  const args={collection,query,offset,lang:language};if(record)args.record=record;
  let data=await json('engineering?'+new URLSearchParams(args));
  if(epoch!==generation||!target.isConnected)return;
  target.replaceChildren(el('h3',it?'Dai requisiti alle prove':'From requirements to evidence'));
  if(!data.available){target.append(el('p',it?'Questa analisi non contiene il nuovo modello documentale. Esegui una nuova scansione.':data.reason));return;}
  if(initial&&data.counts.operations){return renderEngineering(target,'operations',query,offset,record);}
  if(initial&&!data.counts.requirements&&data.counts.recovered_requirements){return renderEngineering(target,'recovered_requirements',query,offset,record);}
  const storageKey='ases-engineering-review:'+data.review_key;
  let saved=null;try{saved=JSON.parse(localStorage.getItem(storageKey)||'null');}catch{}
  if(saved&&!data.review){
    await json('engineering-review',post('engineering-review',{review:saved,language}));
    data=await json('engineering?'+new URLSearchParams(args));
    if(epoch!==generation||!target.isConnected)return;
  }
  const labels=it?{requirements:'Dichiarazioni di requisito riconosciute',api:'Interfacce e firme',scenarios:'Scenari e casi d’uso',test_cases:'Casi di test documentati',test_results:'Risultati importati',issues:'Punti da chiarire',sources:'Fonti e lettura'}:{requirements:'Recognized requirement declarations',api:'Interfaces and signatures',scenarios:'Scenarios and use cases',test_cases:'Documented test cases',test_results:'Imported results',issues:'Questions to review',sources:'Sources and reading'};
  labels.recovered_requirements=it?'Comportamenti dal codice, da confermare':'Code behaviors, requiring confirmation';
  labels.operations=it?'Ingressi tecnici e domande':'Technical entries and questions';
  labels.user_requirements=it?'Requisiti inseriti o adottati':'Authored or adopted requirements';
  labels.diagrams=it?'Diagrammi statici':'Static diagrams';
  target.append(el('p',(it?'Gruppi tecnici di ingressi: ':'Technical entry groups: ')+(data.counts.operations||0)+' · '+(it?'Requisiti documentati riconosciuti: ':'Recognized documented requirements: ')+data.counts.requirements+' · '+(it?'tipo non dichiarato: ':'kind not declared: ')+(data.requirement_kinds?.unspecified??0)+' · '+(it?'Inseriti o adottati: ':'Authored or adopted: ')+(data.counts.user_requirements||0)));
  target.append(el('p',it?'Zero dichiarazioni riconosciute non significa zero requisiti del progetto: la prosa libera è interpretata solo in parte. I gruppi tecnici non contano le funzionalità dell’utente.':'Zero recognized declarations does not mean zero project requirements: free prose is interpreted only partially. Technical groups do not count user features.'));
  target.append(el('p',(it?'Definizioni di test riconosciute nel codice: ':'Test definitions recognized in source: ')+(data.source_test_definitions??'—')+(it?'. Nessun test eseguito da ASES.':'. No tests executed by ASES.')));
  if(data.entry_budget_reached)target.append(el('p',it?'Interpretazione incompleta: raggiunto il limite di 1.000 ingressi. Altri comportamenti, inclusi possibili ingressi della UI, possono restare fuori dalla ricostruzione.':'Incomplete interpretation: the 1,000-entry limit was reached. Additional behavior, including possible UI entries, can remain outside this reconstruction.','warning'));
  target.append(el('p',(it?'Comportamenti interpretati: ':'Interpreted behaviors: ')+(data.counts.recovered_requirements||0)+' · '+(it?'Interfacce: ':'Interfaces: ')+data.counts.api+' · '+(it?'Fonti documentali: ':'Document sources: ')+data.counts.sources,'muted'));
  target.append(el('p',it?'Un requisito scritto non è una funzione verificata. Apri una voce per leggere la fonte, seguire i riferimenti e annotare la tua revisione.':'A written requirement is not verified functionality. Open an item to read its source, follow references and record your review.','muted'));
  if(data.review){const status=el('p',(it?'Revisioni salvate: ':'Saved reviews: ')+data.review.operations.length+' · '+(it?'Incluse nel pacchetto completo; il rapporto ridotto le omette. Una copia resta in questo browser.':'Included in the complete package; the reduced report omits them. A copy stays in this browser.'));status.setAttribute('role','status');target.append(status);}
  if(data.review_state?.conflicts?.length)target.append(el('p',it?'Alcune revisioni riguardano fonti cambiate: sono conservate ma vanno ricontrollate.':'Some reviews refer to changed sources: retained, but they need review.','error'));
  const controls=el('div',undefined,'trace-actions'),select=el('select'),search=el('input');
  select.setAttribute('aria-label',it?'Tipo di informazione':'Information type');
  Object.keys(labels).forEach(k=>{const option=el('option',labels[k]+' ('+data.counts[k]+')');option.value=k;select.append(option);});select.value=collection;
  search.placeholder=it?'Cerca un ID, una firma, una parola…':'Find an ID, signature or word…';search.setAttribute('aria-label',search.placeholder);search.value=query;
  const apply=async event=>{
    const restore=event?.target===select?'select':event?.target===search?'input':'button',epoch=generation;
    try{await renderEngineering(target,select.value,search.value);if(epoch===generation&&target.isConnected)target.querySelector('.trace-actions '+restore)?.focus();}catch(error){showError(error);}
  };
  select.addEventListener('change',apply);search.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();apply(event);}});
  controls.append(select,search,button(it?'Cerca':'Search',apply));target.append(controls);
  const persist=async op=>{
    const review=structuredClone(data.review||{base_model_digest:data.model_digest,operations:[]});
    review.schema='ases-engineering-review/1.1';
    op.base_model_digest=data.model_digest;
    const family=action=>['annotate','confirm','reject'].includes(action)?'annotation':['add-requirement','adopt-requirement'].includes(action)?'requirement':action;
    review.operations=review.operations.filter(old=>old.record_id!==op.record_id||family(old.action)!==family(op.action));
    review.operations.push(op);
    await json('engineering-review',post('engineering-review',{review,language}));
    remember('localStorage',storageKey,JSON.stringify(review));
    await renderEngineering(target,collection,query,offset);
  };
  if(collection==='user_requirements'||collection==='operations')target.append(engineeringRequirementForm(null,persist));
  const list=el('div',undefined,'engineering-list');target.append(list);
  if(!data.items.length)list.append(el('p',it?'Nessuna voce recuperata per questa ricerca. Consulta Fonti e lettura per conoscere il perimetro.':'No records recovered for this search. Check Sources and reading for coverage.'));
  for(const item of data.items){
    const explicitProse=['explicit-prose/1','explicit-prose/2','explicit-prose/3'].includes(item.recognition),classification=item.classification||{};
    const details=el('details',undefined,'doc-row'),title=item.user_context?.title||item.declared_id||item.qualified_name||item.name||item.path||(explicitProse?(it?'Requisito senza ID dichiarato':'Requirement without a declared ID'):item.kind)||item.id;
    const summary=el('summary');summary.append(el('span',title,'engineering-id'));
    const preview=item.statement||item.behavior_summaries?.[0]?.[it?'statement_it':'statement_en']||item.signature||item.text;
    if(preview)summary.append(el('span',preview.replace(/\s+/g,' ').slice(0,220)+(preview.length>220?'…':''),'engineering-preview'));
    const authority=item.authority==='user-confirmation'?(it?'Fornito dall’utente — soddisfacimento non verificato':'User-provided — satisfaction unverified'):item.authority==='document-declaration'?(it?'Dichiarato nel documento':'Declared in document'):item.authority==='source-syntax'?(it?'Letto nel codice':'Read from source'):item.authority==='static-inference'?(it?'Ricostruito dal codice — da confermare':'Reconstructed from code — needs confirmation'):item.authority==='imported-result'?(it?'Risultato importato':'Imported result'):null;
    if(authority)summary.append(el('span',authority,'engineering-origin'));
    if(['lexical-local','package-local','implementation-local','conditional-local'].includes(item.entry_scope)||['local-callable','package-private'].includes(item.visibility))summary.append(el('span',it?'Funzione interna: analisi del solo corpo, ingresso pubblico non stabilito':'Local callable: own-body analysis, public entry not established','engineering-origin'));
    if(item.conditional_declaration)summary.append(el('span',it?'Dichiarazione condizionale: disponibilità durante l’esecuzione non stabilita':'Conditional declaration: runtime availability not established','engineering-origin'));
    if(explicitProse){
      const kind=classification.kind||item.kind;
      const kindLabel=kind==='functional'?(it?'Funzionale':'Functional'):kind==='nonfunctional'?(it?'Non funzionale':'Nonfunctional'):(it?'Tipo non specificato':'Unspecified type');
      const modalities={mandatory:it?'Obbligo dichiarato':'Stated obligation',recommendation:it?'Raccomandazione dichiarata':'Stated recommendation','stated-behavior':it?'Comportamento dichiarato':'Stated behavior',capability:it?'Capacità dichiarata':'Stated capability'};
      const modality=modalities[item.modality]||(it?'Modalità non specificata':'Unspecified modality');
      summary.append(el('span',kindLabel+' · '+modality,'engineering-origin'));
      const origins={'declared-section':it?'Tipo indicato dalla sezione della fonte':'Type stated by the source section','source-declared':it?'Tipo dichiarato nella fonte':'Type declared in source','text-heuristic':it?'Tipo suggerito da euristiche sul testo':'Type suggested by text heuristics','unspecified':it?'Tipo non determinato':'Type not determined'};
      summary.append(el('span',origins[classification.origin]||(it?'Origine della classificazione non disponibile':'Classification origin unavailable'),'engineering-origin'));
    }else if(item.kind==='unspecified')summary.append(el('span',it?'Tipo non dichiarato nella fonte':'Kind not declared in source','engineering-origin'));
    if(explicitProse&&typeof item.scope==='string'&&item.scope.startsWith('Source path suggests archived'))summary.append(el('span',it?'Fonte in archivio: validità per la versione attuale da confermare':'Archived source: confirm applicability to current release','warning'));
    if(item.user_context?.title)summary.append(el('span',it?'Nome fornito dall’utente':'Name supplied by user','engineering-origin'));
    if(item.locations?.[0])summary.append(el('span',item.locations[0].path+(item.locations[0].page?(it?' · pagina ':' · page ')+item.locations[0].page:''),'item-meta'));
    details.append(summary);
    details.addEventListener('toggle',()=>{if(!details.open||details.dataset.filled)return;details.dataset.filled='yes';
      if(collection!=='recovered_requirements'||!item.explanation?.clauses?.length)details.append(el('p',(collection==='operations'?preview:null)||item.statement||item.text||item.responsibility||item.meaning||(item.kind==='unspecified'?(it?'La fonte non contiene un enunciato testuale; i campi dichiarati sono conservati senza inventare una descrizione.':'The source contains no requirement statement; declared fields are retained without inventing a description.'):'')));
      if(explicitProse){
        const originText=classification.origin==='text-heuristic'?(it?'La categoria è suggerita da regole lessicali limitate, non dichiarata esplicitamente come tipo nella fonte.':'The category is suggested by bounded lexical rules; the source does not explicitly declare this type.'):
          classification.origin==='declared-section'?(it?'La categoria deriva dall’intestazione della sezione; è una classificazione della fonte, non una verifica del comportamento.':'The category comes from the section heading; it reflects the source, not verified behavior.'):
          classification.origin==='source-declared'?(it?'La fonte dichiara questa categoria; il comportamento resta non verificato.':'The source declares this category; behavior remains unverified.'):
          (it?'La fonte non specifica una categoria e ASES non ne assegna una.':'The source does not specify a category and ASES does not assign one.');
        details.append(el('p',originText,'muted'));
        if(classification.categories?.length){
          const labels=it?{performance:'prestazioni',availability:'disponibilità',security:'sicurezza',usability:'usabilità',appearance:'aspetto',maintainability:'manutenibilità',portability:'portabilità',reliability:'affidabilità',scalability:'scalabilità',capacity:'capacità e limiti di risorse',compliance:'conformità'}:{};
          details.append(el('p',(it?'Categorie suggerite: ':'Suggested categories: ')+classification.categories.map(value=>labels[value]||value).join(', '),'muted'));
        }
        if(classification.evidence?.length){const evidence=el('ul');for(const value of classification.evidence)evidence.append(el('li',value));details.append(evidence);}
      }
      if(item.subject_missing)details.append(el('p',it?'La fonte omette il soggetto: attore e applicabilità sono da chiarire.':'The source omits its subject: actor and applicability need clarification.','warning'));
      if(item.authority==='document-declaration'&&item.fields?.status)details.append(el('p',(it?'Stato riportato nella fonte: ':'Status reported by the source: ')+item.fields.status+(it?' · dichiarazione dell’autore; soddisfacimento non verificato.':' · author declaration; satisfaction unverified.'),'muted'));
      if(item.signature)details.append(el('pre',item.signature));
      if(collection==='diagrams')details.append(engineeringDiagram(item));
      if(collection==='operations'){
        details.append(el('p',it?'Ingressi con lo stesso insieme esplicito di handler. Il ruolo di business e l’ordine globale delle chiamate non sono stabiliti dal raggruppamento.':'Entries with the same explicit handler set. Business role and global call order are not established by grouping.','muted'));
        if(item.behavior_summaries?.length>1){const aliases=el('details');aliases.append(el('summary',it?'Altri ingressi dello stesso handler':'Other entries for the same handler'));for(const behavior of item.behavior_summaries.slice(1))aliases.append(el('p',behavior[it?'statement_it':'statement_en']));details.append(aliases);}
        const questions=el('ul');for(const question of item.questions||[])questions.append(el('li',question[it?'text_it':'text_en']+(item.user_context?.[question.id]?' '+(it?'Risposta dell’utente: ':'User answer: ')+item.user_context[question.id]:'')));details.append(questions);
        details.append(engineeringContextForm(item,persist),engineeringRequirementForm(item,persist));
        if(item.supported_steps?.length){const calls=el('details');calls.append(el('summary',it?'Chiamate collegate (ordine globale non verificato)':'Linked calls (global order unverified)'));for(const step of item.supported_steps)calls.append(el('p',step.callee+' · '+step.scope+' · '+(it?'riga ':'line ')+step.line));details.append(calls);}
      }
      if(collection==='user_requirements'){
        details.append(el('p',(it?'Autore: ':'Author: ')+item.author+' · '+(it?'Ambito: ':'Scope: ')+item.scope),el('p',(it?'Criterio di accettazione: ':'Acceptance criterion: ')+item.acceptance));
        if(item.support_state==='needs-review')details.append(el('p',it?'Il requisito è conservato, ma la fonte adottata è cambiata o assente. Ricontrolla il collegamento.':'The requirement is retained, but its adopted source changed or disappeared. Review the link.','error'));
        details.append(engineeringRequirementForm(item,persist));
      }
      if(collection==='recovered_requirements'){
        if(item.explanation?.clauses?.length){
          const explanation=el('div');explanation.append(el('h4',it?'Cosa significa':'What it means'));
          for(const clause of item.explanation.clauses){
            const line=el('p',clause[it?'text_it':'text_en']),proof=el('details');proof.append(el('summary',it?'Vedi la prova nel codice':'See the code evidence'));
            for(const ref of clause.fact_refs){const fact=item.facts?.find(f=>f.fact_id===ref),loc=item.locations?.find(l=>l.entity_ref===fact?.entity_ref);if(fact&&loc){proof.append(el('pre',(fact.expression||fact.callee||fact.kind)+(fact.conditions?.length?'\n'+fact.conditions.join('\n'):'')),button((it?'Apri sorgente · riga ':'Open source · line ')+fact.line,()=>showSource({...loc,line:fact.line},details),'evidence'));}}
            explanation.append(line,proof);
          }
          details.append(explanation);
        }
        const original=el('details');original.append(el('summary',it?'Espressioni originali e percorsi':'Original expressions and paths'));
        for(const [key,label] of [['conditions',it?'Condizioni lette':'Observed conditions'],['external_outcomes',it?'Risultati possibili':'Possible outcomes'],['errors',it?'Percorsi di errore':'Error paths'],['effects',it?'Chiamate con possibili effetti':'Calls with possible effects']]){
          const rows=item[key]||[];if(!rows.length)continue;original.append(el('h4',label));
          const list=el('ul');for(const fact of rows.slice(0,12)){const text=fact.expression||fact.callee;list.append(el('li',text+(fact.conditions?.length?' · '+(it?'nel percorso: ':'on path: ')+fact.conditions.join(' / '):'')));}original.append(list);
        }
        details.append(original,engineeringRequirementForm(item,persist));
        details.append(el('p',it?'Questa frase descrive una ricostruzione statica dell’implementazione. Ruolo di business, intenzione originale e correttezza runtime richiedono conferma.':'This sentence describes a static reconstruction of implementation. Business role, original intent and runtime correctness need confirmation.','muted'));
        if(item.flow_limits?.length){details.append(el('h4',it?'Limiti di questo flusso':'Limits of this flow'));const limits=el('ul');for(const reason of item.flow_limits.slice(0,10))limits.append(el('li',reason));details.append(limits);}
      }
      if(item.fields)details.append(el('p',(it?'Attore: ':'Actor: ')+(item.fields.actor||'—')+' · '+(it?'Priorità: ':'Priority: ')+(item.fields.priority||'—')+' · '+(it?'Soglie dichiarate: ':'Declared thresholds: ')+(item.fields.thresholds?.join(', ')||'—')));
      if(item.extraction)details.append(el('p',(it?'Lettura: ':'Reading: ')+item.extraction+' · '+item.units_read+' '+(it?'parti lette':'units read')+' · '+item.interpretation));
      if(item.review)details.append(el('p',(it?'La tua nota: ':'Your note: ')+item.review.note));
      if(item.alternative_declarations?.length){
        const variants=el('details');variants.append(el('summary',it?'Altre dichiarazioni con lo stesso ID':'Other declarations with the same ID'));
        variants.append(el('p',it?'Versioni, estratti o possibili divergenze: ASES conserva i testi senza decidere quale approvare.':'Versions, excerpts or possible differences: ASES retains the text without deciding which declaration to approve.'));
        for(const variant of item.alternative_declarations)variants.append(el('p',variant.statement),el('p',variant.locations.map(loc=>loc.path+(loc.page?' · '+loc.page:'')).join(', '),'muted'));
        details.append(variants);
      }
      const locs=[...(item.locations?.length?item.locations:item.path&&collection==='sources'?[{path:item.path}]:[]),...(item.entry_declaration_locations||[])];
      for(const loc of locs.slice(0,12)){
        const label=loc.path+' '+['page','sheet','cell','line','paragraph','element'].filter(k=>loc[k]).map(k=>k+': '+loc[k]).join(' · ');
        details.append(button(label,async()=>{
          details.querySelector('.engineering-source')?.remove();const block=el('div',undefined,'engineering-source');
          if(loc.entity_ref||item.authority==='source-syntax'||item.kind==='reconstructed-functional-requirement'||item.kind==='recovered-operation'){await showSource(loc,details);return;}
          const excerpt=await json('engineering-source?'+new URLSearchParams(loc));
          block.append(el('h4',excerpt.path),el('p',(it?'Estratto salvato dalla scansione. Stato: ':'Saved scan excerpt. Status: ')+excerpt.extraction));
          for(const unit of excerpt.units)block.append(el('pre',unit.text));
          if(excerpt.truncated)block.append(el('p',it?'Altre parti sono nel download completo.':'More units are available in the full download.'));
          details.append(block);
        },'evidence'));
      }
      for(const link of item.links||[]){
        const other=link.source===item.id?link.target:link.source;
        if(other&&other!==item.id){
          const relationNames=it?{'supported-by-interface-body':'Interfaccia collegata a questa lettura; esecuzione non verificata.','supported-by-behavior':'Ricostruzione collegata; ordine globale delle chiamate non verificato.','adopted-from-candidate':'Candidato adottato come punto di partenza; soddisfacimento non verificato.'}:{'supported-by-interface-body':'Interface linked to this reading; execution unverified.','supported-by-behavior':'Linked reconstruction; global call order unverified.','adopted-from-candidate':'Candidate adopted as a starting point; satisfaction unverified.'};
          const documentReference=link.relation==='declared-document-reference';
          const role=link.native_role&&!documentReference?(it?' · ruolo nella fonte: ':' · source role: ')+link.native_role:'';
          const documentText=it?'Nella fonte: '+link.source+' indica '+link.target+' come elemento '+(link.native_role==='parent'?'padre':'figlio')+'.':'In the source: '+link.source+' identifies '+link.target+' as a '+(link.native_role==='parent'?'parent':'child')+' item.';
          const relation=el('p',(documentReference?documentText:(relationNames[link.relation]||link.relation+' → '+other+' · '+link.status))+role,'muted');details.append(relation);
          if(link.resolved===false)details.append(el('p',documentReference?(it?'ID conservato; il documento indicato non è stato collegato con certezza. Confronta le fonti aprendo il riferimento.':'ID retained; the referenced document has not been matched with certainty. Open the reference to compare sources.'):(it?'Collegamento da ricontrollare: fonte assente o cambiata.':'Link needs review: source absent or changed.'),'error'));
          const candidate=documentReference?'requirements':other.startsWith('user-requirement:')?'user_requirements':other.startsWith('operation:')?'operations':other.startsWith('recovered-requirement:')?'recovered_requirements':/^(RF|RNF)[_-]/.test(other)?'requirements':link.target_collection&&link.target===other?link.target_collection:'api';
          details.append(button(it?'Apri riferimento':'Open reference',()=>renderEngineering(target,candidate,'',0,other)));
        }
      }
      if(item.record_digest){
        const form=el('div',undefined,'engineering-review'),label=el('label',it?'La tua revisione (non modifica la fonte)':'Your review (does not change the source)'),area=el('textarea'),choice=el('select');
        area.id='review-'+Math.random().toString(36).slice(2);label.htmlFor=area.id;area.rows=3;area.maxLength=10000;area.value=item.review?.note||'';
        [['annotate',it?'Annotazione':'Annotation'],['confirm',it?'Confermo questa lettura (non adotta un requisito)':'Confirm this reading (does not adopt a requirement)'],['reject',it?'Da correggere':'Needs correction']].forEach(([value,text])=>{const option=el('option',text);option.value=value;choice.append(option);});
        choice.value=item.review?.action||'annotate';
        choice.setAttribute('aria-label',it?'Esito revisione':'Review outcome');
        form.append(label,area,choice,button(it?'Salva e rigenera documenti':'Save and regenerate documents',async()=>{
          await persist({record_id:item.id,expected_digest:item.record_digest,action:choice.value,note:area.value});
        },'primary'));details.append(form);
      }
      details.append(rawDetails(item,it?'Dettagli e provenienza':'Details and provenance'));
    });list.append(details);
    if(record)details.open=true;
  }
  const paging=el('div',undefined,'trace-actions');
  if(offset>0)paging.append(button(it?'Precedenti':'Previous',()=>renderEngineering(target,collection,query,Math.max(0,offset-20))));
  if(offset+20<data.total)paging.append(button(it?'Successivi':'Next',()=>renderEngineering(target,collection,query,offset+20)));
  paging.append(el('span',Math.min(offset+data.items.length,data.total)+' / '+data.total));target.append(paging);
  if(data.review_state?.conflicts?.length)target.append(rawDetails(data.review_state.conflicts,it?'Annotazioni da ricontrollare':'Annotations needing review'));
}
function engineeringField(parent,title,value='',limit=4000,multiline=true){
  const label=el('label',title),input=el(multiline?'textarea':'input');
  input.id='engineering-'+crypto.randomUUID();input.value=value;input.maxLength=limit;
  if(multiline)input.rows=3;label.htmlFor=input.id;parent.append(label,input);return input;
}
function engineeringContextForm(item,persist){
  const it=language==='it',panel=el('details',undefined,'engineering-form');
  panel.append(el('summary',it?'Completa o correggi il contesto':'Complete or correct the context'));
  panel.append(el('p',it?'Queste risposte sono tue dichiarazioni: non cambiano i fatti estratti e non provano che il codice le soddisfi.':'These answers are your declarations: they do not change extracted facts or prove implementation satisfaction.','muted'));
  const fields={},context=item.user_context||{};
  fields.title=engineeringField(panel,it?'Nome leggibile dell’operazione':'Readable operation name',context.title||'',200,false);
  for(const question of item.questions||[])fields[question.id]=engineeringField(panel,question[it?'text_it':'text_en'],context[question.id]||'',question.id==='actor'?1000:4000);
  panel.append(button(it?'Salva il contesto':'Save context',async()=>{
    await persist({action:'set-operation-context',record_id:item.id,expected_digest:item.record_digest,
                   context:Object.fromEntries(Object.entries(fields).map(([key,input])=>[key,input.value]))});
  },'primary'));return panel;
}
function engineeringRequirementForm(item,persist){
  const it=language==='it',editing=item?.id?.startsWith('user-requirement:'),adopting=item&&!editing;
  const panel=el('details',undefined,'engineering-form');
  panel.append(el('summary',editing?(it?'Modifica il requisito fornito':'Edit supplied requirement'):adopting?(it?'Adotta esplicitamente come requisito…':'Explicitly adopt as a requirement…'):(it?'Scrivi un nuovo requisito…':'Write a new requirement…')));
  panel.append(el('p',it?'Stai dichiarando un bisogno e come verificarlo. Il soddisfacimento resta non verificato; una conferma della lettura è un’azione separata.':'You are declaring a need and how to verify it. Satisfaction remains unverified; confirming a reading is a separate action.','muted'));
  if(adopting)panel.append(el('p',(it?'Candidato di partenza: ':'Starting candidate: ')+(item.statement||item.behavior_summaries?.[0]?.[it?'statement_it':'statement_en']||item.name)));
  const data=editing?item:{},fields={};
  fields.declared_id=engineeringField(panel,it?'ID del requisito (univoco nel progetto)':'Requirement ID (unique in the project)',data.declared_id||'',80,false);
  const kindLabel=el('label',it?'Tipo di requisito':'Requirement type'),kind=el('select');kind.id='kind-'+crypto.randomUUID();kindLabel.htmlFor=kind.id;
  for(const [value,label]of [['functional',it?'Funzionale':'Functional'],['nonfunctional',it?'Non funzionale':'Nonfunctional']]){const option=el('option',label);option.value=value;kind.append(option);}kind.value=data.kind||'functional';panel.append(kindLabel,kind);
  fields.statement=engineeringField(panel,it?'Requisito: quale comportamento è richiesto?':'Requirement: which behavior is required?',data.statement||'',8000);
  fields.author=engineeringField(panel,it?'Autore o responsabile della dichiarazione':'Author or owner of the declaration',data.author||'',200,false);
  fields.scope=engineeringField(panel,it?'Ambito o versione cui si applica':'Applicable scope or version',data.scope||'',1000,false);
  fields.acceptance=engineeringField(panel,it?'Criterio di accettazione indipendente':'Independent acceptance criterion',data.acceptance||'',4000);
  for(const input of Object.values(fields))input.required=true;
  panel.append(button(editing?(it?'Salva il requisito':'Save requirement'):adopting?(it?'Adotta il requisito (non verificato)':'Adopt requirement (unverified)'):(it?'Aggiungi il requisito':'Add requirement'),async()=>{
    if(Object.values(fields).some(input=>!input.reportValidity()))return;
    const action=editing?data.origin.action:adopting?'adopt-requirement':'add-requirement';
    const op={action,record_id:editing?data.id:'user-requirement:'+crypto.randomUUID(),requirement:{kind:kind.value,...Object.fromEntries(Object.entries(fields).map(([key,input])=>[key,input.value.trim()]))}};
    if(action==='adopt-requirement'){op.source_record_id=editing?data.origin.source_record_id:item.id;op.expected_source_digest=editing?data.origin.expected_source_digest:item.record_digest;}
    await persist(op);
  },'primary'));return panel;
}
function engineeringDiagram(item){
  const block=el('div',undefined,'engineering-diagram'),ns='http://www.w3.org/2000/svg';
  const svg=document.createElementNS(ns,'svg'),nodes=item.nodes.slice(0,12),height=Math.ceil(nodes.length/2)*150+30;
  svg.setAttribute('viewBox','0 0 720 '+height);svg.setAttribute('role','img');svg.setAttribute('aria-label',item.name+' — static diagram');
  const coords=new Map(nodes.map((node,index)=>[node.id,{x:20+(index%2)*360,y:20+Math.floor(index/2)*150}]));
  const shape=(name,attrs,text)=>{const n=document.createElementNS(ns,name);for(const [k,v]of Object.entries(attrs))n.setAttribute(k,String(v));if(text!==undefined)n.textContent=text;svg.append(n);return n;};
  for(const edge of item.edges){const from=coords.get(edge.source),to=coords.get(edge.target);if(!from||!to)continue;shape('line',{x1:from.x+150,y1:from.y+50,x2:to.x+150,y2:to.y+50,stroke:'#73977c','stroke-width':2});}
  nodes.forEach(node=>{const {x,y}=coords.get(node.id);shape('rect',{x,y,width:320,height:120,rx:6,fill:'#eff5e9',stroke:'#65846b'});shape('text',{x:x+12,y:y+23,fill:'#163e2b','font-size':14},node.name.slice(0,39));shape('text',{x:x+12,y:y+43,fill:'#49674d','font-size':11},node.kind);node.members.slice(0,3).forEach((member,i)=>shape('text',{x:x+12,y:y+65+i*17,fill:'#264f34','font-size':10},member.replace(/\s+/g,' ').slice(0,49)));});
  block.append(svg,el('p',language==='it'?'Mappa statica di dichiarazioni e dipendenze. La scheda delle firme conserva il dettaglio; nessuna cardinalità o sequenza di esecuzione viene inventata.':'Static declarations and dependencies. Interface sheets retain the details; cardinalities and execution order are not invented.','muted'));
  if(item.nodes.length>12||item.omitted_types)block.append(el('p',language==='it'?'Anteprima limitata: il catalogo completo delle interfacce è nel rapporto.':'Preview limited: the full interface catalogue is in the report.'));
  return block;
}
function markdown(text){
  const target=el('article',undefined,'markdown'),lines=text.split(/\r?\n/);
  let index=0;
  function inline(parent,value){
    const pieces=value.split(/(\[[^\]\n]{1,400}\]\([A-Za-z0-9_.-]+\.md(?:#record-[a-f0-9]{24})?\)|`[^`]+`|\*\*[^*]+\*\*)/g);
    pieces.forEach(piece=>{
      const link=piece.match(/^\[([^\]]+)\]\(([A-Za-z0-9_.-]+\.md)(?:#(record-[a-f0-9]{24}))?\)$/);
      if(link&&report?.documents.includes(link[2])){
        const a=el('a',link[1]);a.href='#'+(link[3]||'documents');a.addEventListener('click',event=>{event.preventDefault();openGeneratedDocument(link[2],link[3]).catch(showError);});parent.append(a);
      }else if(piece.startsWith('`')&&piece.endsWith('`'))parent.append(el('code',piece.slice(1,-1)));else if(piece.startsWith('**')&&piece.endsWith('**'))parent.append(el('strong',piece.slice(2,-2)));else parent.append(document.createTextNode(piece));
    });
  }
  while(index<lines.length){
    const line=lines[index++];
    if(!line.trim()||/^<!-- ases:doc .* -->$/.test(line))continue;
    const anchor=line.match(/^<a id="(record-[a-f0-9]{24})"><\/a>$/);
    if(anchor){const span=el('span');span.id=anchor[1];target.append(span);continue;}
    if(line.startsWith('```')){const code=[];while(index<lines.length&&!lines[index].startsWith('```'))code.push(lines[index++]);index++;const proof=el('details');proof.append(el('summary',language==='it'?'Vedi il dettaglio tecnico':'See technical detail'),el('pre',code.join('\n')));target.append(proof);continue;}
    const heading=line.match(/^(#{1,6})\s+(.+)/);
    if(heading){const node=el('h'+Math.min(6,heading[1].length+1));inline(node,heading[2]);target.append(node);continue;}
    if(line.includes('|')&&index<lines.length&&/^\s*\|?[:\-\s|]+\|?\s*$/.test(lines[index])){
      const wrapper=el('div',undefined,'table-scroll'),table=el('table');
      const cells=value=>value.trim().replace(/^\||\|$/g,'').split('|').map(cell=>cell.trim());
      const row=el('tr');cells(line).forEach(cell=>{const th=el('th');inline(th,cell);row.append(th);});const head=el('thead');head.append(row);table.append(head);index++;
      const body=el('tbody');while(index<lines.length&&lines[index].includes('|')){const tr=el('tr');cells(lines[index++]).forEach(cell=>{const td=el('td');inline(td,cell);tr.append(td);});body.append(tr);}table.append(body);wrapper.append(table);target.append(wrapper);continue;
    }
    if(/^\s*[-*]\s+/.test(line)){
      const list=el('ul');let value=line;while(true){const li=el('li');inline(li,value.replace(/^\s*[-*]\s+/,''));list.append(li);if(index>=lines.length||!/^\s*[-*]\s+/.test(lines[index]))break;value=lines[index++];}target.append(list);continue;
    }
    const p=el('p');inline(p,line);target.append(p);
  }
  return target;
}
async function openGeneratedDocument(name,fragment){
  if(!report?.documents.includes(name))throw new Error(language==='it'?'Documento non disponibile in questa analisi.':'Document unavailable in this analysis.');
  if(page!=='documents')navigate('documents');
  const epoch=generation,data=await json('document?'+new URLSearchParams({name}));
  if(epoch!==generation||page!=='documents')return;
  const row=Array.from($('documents').querySelectorAll('[data-document]')).find(item=>item.dataset.document===name);
  if(!row)return;
  const group=row.closest('details');if(group)group.open=true;
  row.querySelector('.document-text')?.remove();
  const content=el('div',undefined,'document-text');content.append(button(t('closeDoc'),()=>content.remove()),markdown(data.text));row.append(content);
  if(data.truncated)content.append(el('p',t('documentPreview'),'muted'));
  const anchor=fragment?content.querySelector('[id="'+fragment+'"]'):null;
  const destination=anchor?.nextElementSibling||content;
  destination.tabIndex=-1;destination.focus();destination.scrollIntoView({block:'start'});
  if(fragment&&!anchor)content.append(el('p',language==='it'?'Il riferimento non è presente nell’anteprima limitata. Usa il pacchetto completo o la ricerca dei record.':'The reference is outside the bounded preview. Use the complete package or record search.','muted'));
}
async function downloadResponse(response,filename) {
  const blob=await response.blob(),url=URL.createObjectURL(blob),anchor=el('a');
  anchor.href=url;anchor.download=filename;document.body.append(anchor);anchor.click();anchor.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function loadKit() {
  if(!kitData)kitData=await json('kit');
  const target=$('kit');target.replaceChildren(el('h2',t('kitTitle')),el('p',t('kitText')));
  if(!kitData.available){target.append(el('p',t('kitMissing')));return;}
  const layout=el('div',undefined,'kit-layout'),menu=el('div'),editor=el('div');
  const label=el('label',t('kitLabel')),select=el('select');select.id='template';label.htmlFor=select.id;
  Object.keys(kitData.templates).forEach(name=>{const option=el('option',name);option.value=name;select.append(option);});
  if(!activeTemplate||!Object.hasOwn(kitData.templates,activeTemplate))activeTemplate=Object.keys(kitData.templates)[0];select.value=activeTemplate;
  const editorLabel=el('label',t('draft')),area=el('textarea');area.id='draft';area.spellcheck=false;editorLabel.htmlFor=area.id;area.value=drafts[activeTemplate]??kitData.templates[activeTemplate];
  area.addEventListener('input',()=>{drafts[activeTemplate]=area.value;remember('localStorage','ases-template-drafts',JSON.stringify(drafts));draftDirty=true;});
  select.addEventListener('change',()=>{activeTemplate=select.value;area.value=drafts[activeTemplate]??kitData.templates[activeTemplate];});
  const save=button(t('kitDownload'),async()=>{
    drafts[activeTemplate]=area.value;
    await downloadResponse(await api('kit-download',post('kit-download',{documents:drafts})),'ases-documents.zip');
    draftDirty=false;
  },'primary');
  menu.append(label,select,el('p',t('kitMemory'),'muted'),save);
  const guide=el('details');guide.append(el('summary',t('kitGuide')),markdown(kitData.guide));menu.append(guide);
  editor.append(editorLabel,area);layout.append(menu,editor);target.append(layout);
}
$('scan-form').addEventListener('submit',run);
$('new-project').addEventListener('click',()=>selectTask('scan'));
$('open-snapshot').addEventListener('click',()=>selectTask('open'));
$('open-kit').addEventListener('click',()=>selectTask('kit'));
$('open-tools').addEventListener('click',()=>{if(!busy){clearError();renderTools();showWorkspace('tools');}});
$('current-result').addEventListener('click',()=>{if(report){clearError();page='overview';renderReport();}});
$('current-docs').addEventListener('click',()=>{if(report){clearError();page='documents';renderReport();}});
$('retry').addEventListener('click',()=>{clearError();showWorkspace('form');$('source').focus();});
$('cancel').addEventListener('click',async()=>{try{$('cancel').disabled=true;$('cancel').textContent=t('cancelling');lastStatus=await json('cancel',post('cancel',{}));renderProgress(lastStatus);}catch(error){showError(error);$('cancel').disabled=false;}});
$('choose-folder').addEventListener('click',async()=>{try{$('choose-folder').disabled=true;const chosen=await json('choose-folder',post('choose-folder',{}));if(chosen.path)$('source').value=chosen.path;}catch(error){showError(error);}finally{$('choose-folder').disabled=false;}});
$('task').addEventListener('change',()=>{clearError();configureForm();});
$('language').addEventListener('click',()=>{
  language=language==='it'?'en':'it';remember('localStorage','ases-language',language);renderLanguage();
});
$('collection').addEventListener('change',()=>{offset=0;selectedItem=null;$('detail').replaceChildren(el('p',t('select'),'muted'));loadItems().catch(showError);});
let searchTimer;
$('search').addEventListener('input',()=>{clearTimeout(searchTimer);offset=0;requestNumber++;searchTimer=setTimeout(()=>loadItems().catch(showError),180);});
function renderExportNotice(){
  const full=$('export-mode').value==='full';
  $('download').textContent=language==='it'?(full?'Scarica pacchetto completo ↓':'Scarica rapporto ridotto ↓'):(full?'Download complete package ↓':'Download reduced report ↓');
  $('export-notice').textContent=language==='it'?(full?'Contiene documenti, percorsi, possibili frammenti e note. Permette di riaprire il lavoro: controllalo prima di condividerlo.':'Contiene solo conteggi e una lista delle omissioni. Non conserva revisioni e non si riapre come analisi.'):(full?'Contains documents, paths, possible fragments and notes. Reopens your work: inspect before sharing.':'Contains counts and an omissions list only. Does not retain reviews and cannot reopen as an analysis.');
}
$('export-mode').addEventListener('change',renderExportNotice);
async function apiResponse(){return api('download?'+new URLSearchParams({lang:language,mode:$('export-mode').value}));}
$('download').addEventListener('click',async()=>{try{$('download').disabled=true;$('download').textContent=t('downloadWorking');await downloadResponse(await apiResponse(),'ases-report.zip');}catch(error){showError(error);}finally{$('download').disabled=false;renderExportNotice();}});
$('clear').addEventListener('click',async()=>{
  try{
    await json('clear',post('clear',{}));generation++;requestNumber++;report=null;selectedItem=null;
    $('status').textContent='';clearError();renderLanguage();selectTask('scan');
  }catch(error){showError(error);}
});
renderLanguage();
showWorkspace('form');
window.addEventListener('beforeunload',event=>{if(draftDirty){event.preventDefault();event.returnValue='';}});
if(!token)showError(new Error(t('noSession')));
else json('config').then(config=>{$('source').value=config.source;return json('status');}).then(state=>{if(state.status!=='idle')return poll();}).catch(showError);
