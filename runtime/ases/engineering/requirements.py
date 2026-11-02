"""Literal requirement sentences and inspectable type suggestions, never satisfaction."""
from __future__ import annotations

import re

CLASSIFICATION_PROFILE = 'constraint-signals/5'

MODAL = re.compile(
    r"\b(?P<modal>shall|must|should|will|can|deve|devono|dovr[àa]|dovranno|dovrebbe|dovrebbero|"
    r"(?:is|are)\s+(?:expected|required|able|allowed|permitted)\s+to|has\s+to)\b", re.I)
NEGATIVE_CONTEXT = re.compile(r"^(?:(?:code|usage)\s+)?(?:examples?|esempi|tutorial|modelli di esempio)\b|^templates?$", re.I)
INSTRUCTION = re.compile(r"^(?:you|tu|voi)\b.*?\b(?:install\w*|run|execute|download|clone|activate|esegui\w*|installa\w*)\b", re.I)
FUNCTION = re.compile(
    r"\b(?:allow\w*|enabl\w*|permit\w*|provid\w*|display\w*|show\w*|creat\w*|add\w*|edit\w*|updat\w*|"
    r"delet\w*|remov\w*|sav\w*|stor\w*|send\w*|notif\w*|calculat\w*|return\w*|search\w*|quer\w*|"
    r"register\w*|authenticat\w*|verify|verifies|validat\w*|generat\w*|export\w*|import\w*|open\w*|clos\w*|"
    r"cancel\w*|book\w*|manag\w*|schedul\w*|associat\w*|specif\w*|select\w*|assign\w*|print\w*|copy|copi\w*|focus\w*|persist\w*|stream\w*|retriev\w*|"
    r"mov\w*|contain\w*|includ\w*|record\w*|receiv\w*|submit\w*|facilitat\w*|initiat\w*|determin\w*|"
    r"convert\w*|filter\w*|sort\w*|upload\w*|download\w*|check\w*|prevent\w*|conflict\w*|"
    r"consent\w*|permett\w*|visualizz\w*|mostr\w*|creare|crea|aggiung\w*|modific\w*|aggiorn\w*|elimin\w*|"
    r"rimuov\w*|salv\w*|memorizz\w*|invia\w*|notific\w*|calcol\w*|restitui\w*|cerc\w*|ricerc\w*|"
    r"registr\w*|autentic\w*|verific\w*|valid\w*|gener\w*|esport\w*|import\w*|annull\w*|prenot\w*|gest\w*|"
    r"offer\w*|paus\w*|resum\w*|locat\w*|merg\w*|reset\w*|hold\w*|consist\w*|represent\w*|retain\w*|"
    r"track\w*|acquir\w*|identif\w*|accept\w*|reject\w*|enforc\w*|replicat\w*|disconnect\w*)\b", re.I)

# These ordinary verbs are useful only as modal predicates. Several are also
# common nouns (e.g. review, request, change), so do not add them to FUNCTION's
# global search over the entire sentence.
MODAL_ACTION = re.compile(
    r"^\s*(?:(?:not|also|then)\s+)*(?:(?:be\s+(?:able|required|expected)\s+to)\s+)?"
    r"(?:(?:\w+ly)\s+){0,3}(?P<action>"
    r"review(?:s|ed|ing)?|request(?:s|ed|ing)?|enter(?:s|ed|ing)?|log(?:s|ged|ging)?|"
    r"suppl(?:y|ies|ied|ying)|insert(?:s|ed|ing)?|compil(?:e|es|ed|ing)|scor(?:e|es|ed|ing)|"
    r"maintain(?:s|ed|ing)?|defin(?:e|es|ed|ing)|mark(?:s|ed|ing)?|indicat(?:e|es|ed|ing)|"
    r"chang(?:e|es|ed|ing)|end(?:s|ed|ing)?|"
    r"revision(?:a|are|i|ano)|richied(?:e|ono|ere|erà|eranno)|inser(?:isce|iscono|ire|irà|iranno)|"
    r"registr(?:a|ano|are|erà|eranno)|forn(?:isce|iscono|ire|irà|iranno)|compil(?:a|ano|are|erà|eranno)|"
    r"valut(?:a|ano|are|erà|eranno)|puntegg(?:ia|iano|iare|erà|eranno)|"
    r"mantien(?:e|ono)|manten(?:ere|uto|uta)|manterr(?:à|anno)|defin(?:isce|iscono|ire|irà|iranno)|"
    r"segnal(?:a|ano|are|erà|eranno)|indic(?:a|ano|are|erà|eranno)|"
    r"cambi(?:a|ano|are|erà|eranno)|contrassegn(?:a|ano|are|erà|eranno)|"
    r"termin(?:a|ano|are|erà|eranno))\b", re.I)

# These signals describe quality constraints; they are reasons, not calibrated probabilities.
QUALITY = {
    'performance': r'\b(?:response time|tempo di risposta|latenza|latency|throughput|processing time|wait time|peak load)\b|\b(?:within|less than|at most|no more than|no longer than|entro|inferiore a|al massimo)\b.{0,70}\b(?:milliseconds?|millisecondi|seconds?|secondi|minut\w*|hours?|ore|ms)\b',
    'availability': r'\b(?:availability|disponibilit[àa]|uptime|up time|downtime|down time|24x7|24/7|99\.9)\b|\b(?:system|service|application|product|sistema|servizio|applicazione)\b.{0,100}\b(?:be|remain|essere|rimanere)\s+(?:continuously\s+)?(?:available|disponibil\w*)\b',
    'security': r'\b(?:encrypt\w*|cifrat\w*|unauthori[sz]ed|malicious|virus protection|password policy|data integrity|access control|private information|privacy|personal information|protect.{0,35}identity)\b|\bonly\s+(?:authori[sz]ed|registered|company|management)\b|\b(?:solo|soltanto)\s+(?:gli\s+)?(?:utenti\s+)?autorizzat\w*\b',
    'usability': r'\b(?:usability|usabilit[àa]|intuitive|intuitiv\w*|self.explanatory|user.friendly|training|formazione|one click|single click|keyboard.operable|WCAG|screen reader|accessibil\w*)\b|\b(?:easy|easily|facile|facilmente)\b.{0,60}\b(?:use|learn|navigate|usare|imparare|navigar\w*)\b',
    'appearance': r'\b(?:look and feel|look of|font|colour|color.coded|color coded|color coding|verbiage|terminology|standard English|aesthetic\w*|layout)\b|\b(?:simulat\w*)\b.{0,45}\b(?:look|sound)\b|\bconsistent\b.{0,50}\b(?:screen|page|interface|format)\b',
    'maintainability': r'\b(?:maintainab\w*|manutenibil\w*|extensib\w*|estensib\w*|configurab\w*|modular\w*|coding best practices|design patterns|maintenance release|working days|software updates)\b',
    'portability': r'\b(?:portabil\w*|compatibil\w*|operating system|operating environment|hardware|web application server|browser|database management system|binary|ZIP file)\b|\b(?:run|runs|operate|operates|operare|funzionar\w*)\s+(?:on|within|su)\b|\binterface\s+with\b',
    'reliability': r'\b(?:reliab\w*|affidabil\w*|fault.toleran\w*|failover|crash\w*|recover\w*|ripristin\w*|correttezza|correctness|exception log|error log|uninterrupted)\b',
    'scalability': r'\b(?:scalab\w*|concurrent|simultaneous|simultanei|contemporanei)\b|\b\d[\d ,]*\s+(?:transactions|requests|transazioni|richieste)\s+(?:per|al|all[’\x27])\b',
    'compliance': r'\b(?:comply|compliance|conform\w*|regulation\w*|legal|licen[cs]\w*|audit trail|auditing|normativ\w*)\b',
}
# Match a constrained quantity, not an isolated unit name or an arbitrary number.
QUALITY['performance'] += (r'|\b(?:within|less than|at most|no more than|no longer than|longer than|entro|al massimo)\b'
                           r'.{0,90}?\b\d+(?:[.,]\d+)?\s*(?:ms|s|milliseconds?|seconds?|minutes?|secondi|minuti)\b')
QUALITY['capacity'] = (r'\b\d+(?:[.,]\d+)?\s*(?:[KMGT]i?B|MBs|megabytes?|gigabytes?|kilobytes?)\b'
                       r'|\b(?:up to|at most|maximum of|fino a|al massimo)\s+[\d ,]+\s+(?:concurrent\s+|simultaneous\s+)?(?:objects|connections|requests|attachments|oggetti|connessioni|richieste)\b')
QUALITY['security'] += (
    r'|\b(?:injection attacks?|eval attacks?|sandbox\w*|digitally signed|sensitive data|sensitive information|insecure\s+(?:image|SVG|HTML)|executable\s+files?)\b'
    r'|\b(?:validat\w*|saniti[sz]\w*)\s+all\s+(?:inputs?|user.{0,15}inputs?)\b'
    r'|\b(?:saniti[sz]\w*|escap\w*)\b.{0,50}\b(?:HTML|XML|untrusted|user.provided|user.supplied)\b'
    r'|\b(?:only|solo|soltanto)\s+(?:[\w-]+\s+){0,10}(?:can|may|possono|può)\b'
    r'|\bcan\s+only\b'
    r'|\b(?:prevent|prohibit|forbid|impedire|vietare)\b.{0,70}\b(?:attach\w*|upload\w*|alleg\w*)\b.{0,50}\bexecutable\b')
QUALITY['maintainability'] += (
    r'|\bversion control\b|\b(?:build|builds|compilation|compilazione)\b.{0,45}\breproducib\w*\b'
    r'|\b(?:dependencies|dipendenze|unused\s+(?:features|configurations))\b.{0,130}\b(?:before|prima)\b.{0,30}\b(?:build\w*|compil\w*)\b')
QUALITY['performance'] += (
    r'|\b(?:every|no later(?: than)?|in under|faster than|ogni|non oltre)\s+\d+(?:[.,]\d+)?\s*(?:milliseconds?|seconds?|minutes?|hours?|ms|s|secondi|minuti|ore)\b'
    r'|\b(?:respond|response|search results?|processing|rispond\w*|elaborazion\w*)\b.{0,65}\b(?:fast|quickly|acceptable time|rapid\w*)\b')
QUALITY['availability'] += (
    r'|\b(?:available|disponibile)\b.{0,70}\b(?:\d+\s+hours?\s+per\s+day|\d+\s+days?\s+per\s+year|at any time|sempre)\b'
    r'|\b(?:system|service|website|sistema|servizio|sito)\b.{0,40}\b(?:is|be|remain|è|essere)\s+available\b'
    r'|\bat any time of (?:the day|day or night)\b')
QUALITY['security'] += (
    r'|\bonly\b.{0,80}\b(?:shall|must|may)\s+(?:have|be\s+given)\s+access\b'
    r'|\b(?:authenticated\s+and\s+authorized|autenticat\w*\s+e\s+autorizzat\w*)\b'
    r'|\bsecure\s+(?:image|environment|container|build)\b')
QUALITY['appearance'] += r'|\b(?:colou?rs?|fonts?|appearance|colour scheme|color scheme|aspetto|caratteri tipografici)\b|\bstandard\s+(?:menus?|buttons?)\b'
QUALITY['usability'] += (
    r'|\b(?:readable|understandable|untrained|leggibil\w*|comprensibil\w*)\b'
    r'|\b(?:without|senza)\b.{0,35}\b(?:instructions|istruzioni)\b')
QUALITY['scalability'] += (
    r'|\b(?:support|handle|handling|processing|gestire|supportare)\b.{0,60}\b(?:multiple|existing\s+\d+|\d+)\s+(?:remote\s+)?(?:users|connections|students|utenti|connessioni)\b')
QUALITY['reliability'] += (
    r'|\boffline\s+mode\b|\bin (?:the )?event of (?:a )?failure\b'
    r'|\b(?:restore\w*|recover\w*)\b.{0,90}\b(?:back online|after\s+(?:a\s+)?failure|after\s+(?:a\s+)?restart)\b'
    r'|\b(?:no interruption|without interruption|senza interruzion\w*)\b')
QUALITY['maintainability'] += r'|\b(?:scheduled maintenance|during upgrade|product.{0,3}lifecycle)\b'
QUALITY['compliance'] += r'|\b(?:adhere|meet|follow)\b.{0,75}\b(?:standards?|guidelines?|norme|linee guida)\b'
QUALITY['portability'] += (
    r'|\b(?:support|compatible|run|operate)\b.{0,45}\b(?:Windows|Linux|macOS|Android|iOS|Firefox|Chrome|Safari|Internet Explorer)\b')
# Constraint forms rather than project names or benchmark sentence templates.
QUALITY['performance'] += (
    r'|\b(?:acceptable time|timely manner|tempo accettabile|tempi ragionevoli)\b'
    r'|\b(?:within|no more than|less than|in under|completed in|entro|non oltre)\s+\d+(?:[.,]\d+)?\s*(?:min|mins|minutes?|us|microseconds?|ms|seconds?|s)\b'
    r'|\bevery\s+(?:hour|day|minute|second)\b'
    r'|\b(?:provide|implement|use|support)\b.{0,35}\b(?:asynchronous messaging|multi.threading|load balancing|parallel processing)\b'
    r'|\b(?:reduce|minimi[sz]e)\b.{0,40}\b(?:overhead|latency|processing time)\b')
QUALITY['availability'] += (
    r'|\b(?:phone|technical|customer|telephone)\s+support\b.{0,90}\b(?:hours?|am|pm|available)\b'
    r'|\b(?:available|disponibile)\b.{0,60}\b(?:phone|technical|customer|telephone)\s+support\b'
    r'|\b\d+\s+hour\b.{0,35}\b(?:support|toll.free)\b')
QUALITY['reliability'] += (
    r'|\b(?:robust|robustness|fault avoidance|fault isolation|redundan\w*)\b'
    r'|\bcontinue\s+(?:to\s+)?(?:operate|work|function)\b.{0,100}\b(?:down|fail\w*|outage)\b'
    r'|\bprevent\b.{0,60}\b(?:incorrect|invalid|corrupt\w*)\s+data\b')
QUALITY['security'] += (
    r'|\bonly\b.{0,100}\b(?:shall|must|allowed|permitted|able)\b'
    r'|\b(?:without|not have|no|deny|restrict\w*)\b.{0,40}\b(?:access|permission)\b'
    r'|\b(?:access|permissions?)\s+(?:level|rights?|control)\b'
    r'|\b(?:users?|accounts?)\b.{0,55}\bauthenticated\b'
    r'|\b(?:free of|free from|free of all|free of any|free of computer|free of known)\b.{0,20}\bviruses\b'
    r'|\bmaintain\b.{0,30}\bsecurity\b'
    r'|\b(?:user|users|passwords?|permissions?)\b.{0,55}\b(?:access|changes?)\b.{0,60}\b(?:recorded|logged|audit)\b'
    r'|\bshall not\b.{0,55}\banother\b.{0,45}\bdata\b')
QUALITY['scalability'] += (
    r'|\b(?:support\w*|handl\w*|process\w*|maximum of|minimum of)\b.{0,55}\b[\d][\d ,.]*\s+(?:(?:million|thousand)\s+)?(?:customers|users|transactions|games|movies|requests|utenti|transazioni)\b'
    r'|\b(?:users?|games?|connections?|utenti|connessioni)\b.{0,45}\b(?:at the same time|simultaneously|contemporaneamente)\b'
    r'|\bnumber of\b.{0,40}\brecords\s+per\s+(?:day|hour|minute)\b'
    r'|\b(?:operat\w*|manag\w*|process\w*)\b.{0,100}\b(?:next|at least|minimum of)\s+\d+\s+years?\b'
    r'|\bhandl\w*\s+all\b.{0,40}\b(?:requests|usage|traffic)\b')
QUALITY['maintainability'] += (
    r'|\b(?:system|software|product|application)\s+(?:version\s+)?(?:releases?|updates?|installations?|upgrades?)\b'
    r'|\b(?:regular basis|maintenance windows?|quarterly maintenance)\b'
    r'|\b(?:changes?|updates?|additions?)\b.{0,110}\b(?:guides?|documentation|documentazione)\b'
    r'|\b(?:new technology|new technologies)\b.{0,70}\b(?:architecture|architectural|architettura)\b')
QUALITY['portability'] += (
    r'|\b(?:database management systems?|application servers?|programming language|programming libraries|computer equipment)\b'
    r'|\b(?:operat\w*|work|installed|installable|used)\b.{0,65}\b(?:platforms?|environments?|computers?|office environments?|noisy conditions|dirty conditions)\b'
    r'|\b(?:encoded|streamed)\b.{0,45}\b(?:Media Player|\d+k\s+(?:and\s+\d+k\s+)?streams?)\b'
    r'|\b(?:developed|implemented|written)\s+(?:with|in|using)\b.{0,45}\b(?:libraries|language|framework|runtime)\b'
    r'|\b(?:technical|corporate)\s+support\s+cent(?:er|re)\b')
QUALITY['usability'] += (
    r'|\b(?:satisfied|satisfaction|productivity|familiar|mistakes|user help|locali[sz]ation)\b'
    r'|\b(?:maximum of|under|at most|no more than|less than|al massimo)\s+\d+\s+(?:clicks?|pages?|steps?|clic|pagine|passaggi)\b'
    r'|\b(?:users?|respondents?|surveyed|participants?|utenti)\b.{0,120}\b(?:\d+(?:[.,]\d+)?%|survey|surveyed|feel|find that)\b'
    r'|\b\d+\s+out of\s+\d+\b.{0,100}\b(?:use|complete|learn)\b'
    r'|\b(?:date|time|language)\b.{0,60}\b(?:locale|target market|countries)\b')
QUALITY['appearance'] += (
    r'|\b(?:branding|nomenclature|pixel resolution|\d+\s+by\s+\d+\s+pixel)\b'
    r'|\b(?:page|website|interface)\b.{0,45}\b(?:modern|clean|concise|appealing|similar format)\b'
    r'|\b(?:religious|ethnic|cultural)\b.{0,45}\b(?:offensive|alienate|appropriate)\b'
    r'|\b(?:offensive|alienate)\b.{0,45}\b(?:religious|ethnic|cultural)\b')
# Explicit obligations, not isolated subject-matter words. Keep display/export
# features distinct from the quality imposed on the system or its use.
QUALITY['security'] += (
    r'|\bprotect\w*\b.{0,45}\b(?:from|against)\b.{0,35}\b(?:abuse|attacks?|intrusion)\b'
    r'|\baccessible\s+only\s+to\s+authori[sz]ed\b'
    r'|\baccess\b.{0,30}\b(?:limited|restricted)\b.{0,55}\b(?:permissions?|roles?|privileges?)\b'
    r'|\b(?:require|provide|have)\s+(?:both\s+)?authentication\s*(?:,?\s*and\s+|&\s*)authorization\b'
    r'|\b(?:use|require)\s+(?:a\s+)?username\s+and\s+(?:a\s+)?password\b.{0,65}\bauthenticat\w*\b'
    r'|\b(?:users?|operators?)\s+(?:must|shall|will)\s+provide\s+(?:a\s+)?username\s+and\s+(?:a\s+)?password\b'
    r'|\bauthentication\s+and\s+authorization\s+are\s+required\b'
    r'|\b(?:protegger\w*|protegge)\b.{0,45}\b(?:da|dai|dagli|contro)\b.{0,35}\b(?:abusi|attacchi|intrusioni)\b'
    r'|\baccessibili\s+solo\s+al\s+personale\s+autorizzato\b'
    r'|\baccesso\b.{0,60}\b(?:limitato|ristretto)\b.{0,45}\b(?:permessi|ruoli|privilegi)\b'
    r'|\b(?:utenti|operatori)\s+devono\s+inserire\s+un\s+nome\s+utente\s+e\s+una\s+password\b'
    r'|\bautenticazione\s+e\s+autorizzazione\s+sono\s+richieste\b')
QUALITY['usability'] += (
    r'|\b(?:\d+(?:[.,]\d+)?%\s+of\s+)?(?:novice|untrained)\s+users\b.{0,60}\b(?:use|operate|complete)\b'
    r'|\b(?:\d+(?:[.,]\d+)?%\s+of\s+)(?:customers?|users?|participants?)\b.{0,50}\bcomfortable\b'
    r'|\b(?:activated|selected|operated|accessible)\b.{0,70}\b(?:mouse|keyboard)\b'
    r'|\bcomplete\b.{0,40}\busing\s+a\s+mouse\s+or\s+keyboard\b'
    r'|\b(?:attivat\w*|selezionat\w*|utilizzabil\w*)\b.{0,60}\b(?:mouse|tastiera)\b'
    r'|\bcompletare\b.{0,40}\busando\s+il\s+mouse\s+o\s+la\s+tastiera\b'
    r'|\b\d+(?:[.,]\d+)?%\s+degli\s+utenti\s+principianti\b.{0,50}\busare\b'
    r'|\bhelp\s+section\s+(?:shall|must)\s+explain\b.{0,100}\bdifficulty\s+using\b'
    r'|\bsezione\s+di\s+aiuto\s+deve\s+spiegare\b.{0,100}\bdifficolt[àa]\b')
QUALITY['portability'] += r'|\bplatform\s+independent\b|\bindipendente\s+dalla\s+piattaforma\b'
QUALITY['performance'] += (
    r'|\b(?:updates?|upgrades?)\b.{0,45}\b(?:take|within)\s+(?:a|one|\d+)\s+(?:day|days|week|weeks|hours?)\b'
    r'|\b(?:queries|refresh|polling)\b.{0,90}\bonce\s+(?:a|per)\s+(?:day|week|hour|minute)\b'
    r'|\baggiornamento\b.{0,45}\brichiedere\s+(?:un|\d+)\s+(?:giorno|giorni|ore)\b'
    r'|\binterrogazioni\b.{0,60}\buna\s+volta\s+alla\s+settimana\b')
QUALITY = {key: re.compile(value, re.I) for key, value in QUALITY.items()}

# Declarative descriptions qualify only for bounded observable output/rate forms.
# General project prose ("the team is working...") stays outside this recognizer.
OUTPUT_ASSERTION = re.compile(
    r'\b(?:data|values?|results?|records?|information|dati|valori|risultati)\b.{0,180}'
    r'\b(?:displayed|shown|returned|stored|visualizzati|restituiti|memorizzati)\b.{0,200}'
    r'\b(?:is|are|sono|è)\b\s+\S.{5,}', re.I)
RATE_ASSERTION = re.compile(
    r'\b(?:out of|su)\s+\d+\b.{0,120}\b(?:system|service|application|sistema|servizio)\b'
    r'.{0,40}\b(?:is|è)\s+(?:available|disponibile)\b.{0,60}\b\d+\s+(?:times|volte)\b', re.I)

METRIC_ACTION = re.compile(
    r'\b(?:shall|must|should|will|deve|dovrebbe)\s+(?:display|show|export|generate|record|plot|calculate|list|'
    r'mostrare|visualizzare|esportare|registrare|calcolare)\b[^.;\n]{0,220}$', re.I)
QUALITY_TOPICS = frozenset({'response time', 'latency', 'throughput', 'availability', 'uptime', 'downtime',
                          'satisfaction', 'productivity', 'mistakes', 'font', 'colour', 'nomenclature',
                          'hardware', 'browser', 'operating system', 'database management system',
                          'database management systems', 'load balancing', 'robustness',
                          'password policy', 'platform independent', 'indipendente dalla piattaforma'})
REPORTING_SUBJECT = re.compile(
    r'\b(?:system|application|dashboard|report|interface|page|tool|product|'
    r'cruscotto|rapporto|sistema|applicazione|pagina)\b', re.I)


def quality_signals(text):
    for category, pattern in QUALITY.items():
        for match in pattern.finditer(text):
            # Exposing a metric/topic is a feature. A separate bound (e.g. within
            # 200 ms) is still retained by its own match; do not erase the clause.
            if match.group().casefold() in QUALITY_TOPICS and METRIC_ACTION.search(text[:match.start()]):
                continue
            if ((match.group().lower().startswith(('novice users', 'untrained users', 'protect'))
                 or re.match(r'\d+(?:[.,]\d+)?%\s+(?:of|degli)\b', match.group()))
                    and (reporting := METRIC_ACTION.search(text[:match.start()]))):
                # A survey's expected success rate is a quality target, whereas
                # a dashboard displaying that rate is a reporting feature.
                subject = re.split(r'[.;\n]', text[:reporting.start()])[-1]
                if REPORTING_SUBJECT.search(subject):
                    continue
            yield category, match.group()
            break


def prose_requirement(text, section=''):
    """Recognize a source assertion with a stated subject/modality, not a command."""
    if not 20 <= len(text) <= 12000 or NEGATIVE_CONTEXT.search(section):
        return None
    if text.startswith(('`', '{', '<')) or text.rstrip().endswith('?') or INSTRUCTION.search(text[:250]):
        return None
    match = MODAL.search(text[:600])
    if not match:
        if not (OUTPUT_ASSERTION.search(text) or RATE_ASSERTION.search(text)):
            return None
        return {'modality': 'stated-behavior', 'modal_text': '', 'subject_missing': False,
                'assertion_form': 'observable-description', 'classification': classify_statement(text, section)}
    subject, predicate = text[:match.start()].strip(), text[match.end():].strip()
    subject_missing = not subject and match['modal'].casefold() in {'shall', 'must', 'deve', 'devono'}
    if subject_missing and re.match(r'^(?:install\w*|run|execute|download|clone|activate|esegui\w*|installa\w*)\b', predicate, re.I):
        return None
    if ((not subject_missing and (not 2 <= len(subject) <= 400 or not re.search(r'[A-Za-zÀ-ÿ]', subject))) or len(predicate) < 8):
        return None
    # Code expressions, headings and unbound quoted modal examples are not source obligations.
    if any(token in subject for token in ('```', '=>', ' = ', '"', '`')):
        return None
    modal = match['modal'].casefold()
    if modal == 'can' and not (re.match(r'^only\b', text, re.I) or re.match(r'^only\b', predicate, re.I)):
        return None
    modality = ('recommendation' if modal in {'should', 'dovrebbe', 'dovrebbero'} else
                'stated-behavior' if modal == 'will' or 'expected' in modal else
                'capability' if modal == 'can' or any(word in modal for word in ('able', 'allowed', 'permitted')) else 'mandatory')
    classification = classify_statement(text, section)
    return {'modality': modality, 'modal_text': match['modal'], 'subject_missing': subject_missing,
            'assertion_form': 'restricted-capability' if modal == 'can' else 'modal-assertion',
            'classification': classification}


def classify_statement(text, section=''):
    """Keep declared section types distinct from reasoned, explicitly weak suggestions."""
    if re.search(r'\b(?:non[- ]?functional requirements?|requisiti non funzionali)\b', section, re.I):
        return {'kind': 'nonfunctional', 'origin': 'declared-section', 'categories': [], 'evidence': [section], 'profile': CLASSIFICATION_PROFILE}
    if re.search(r'\b(?:functional requirements?|requisiti funzionali)\b', section, re.I):
        return {'kind': 'functional', 'origin': 'declared-section', 'categories': [], 'evidence': [section], 'profile': CLASSIFICATION_PROFILE}
    signals = list(quality_signals(text))
    action = None
    modal = MODAL.search(text[:600])
    if modal:
        action = MODAL_ACTION.search(text[modal.end():])
    if action is None:
        action = FUNCTION.search(text)
    action_text = (action.group('action') if action and action.re is MODAL_ACTION else
                   action.group() if action else None)
    if signals:
        return {'kind': 'nonfunctional', 'origin': 'text-heuristic', 'categories': [k for k, _ in signals],
                'evidence': [value for _, value in signals], 'profile': CLASSIFICATION_PROFILE,
                'functional_evidence': [action_text] if action_text else [],
                'scope': 'quality/constraint signals; source intent and satisfaction not verified'}
    return {'kind': 'functional' if action else 'unspecified',
            'origin': 'text-heuristic' if action else 'unspecified', 'categories': [],
            'evidence': [action_text] if action_text else [], 'profile': CLASSIFICATION_PROFILE}
