"""Portable, offline report: every judgement can be inspected against its source."""
from html import escape
from pathlib import Path


def percent(value):
    return "—" if value is None else f"{value:.1%}"


def write_report(result, output: Path):
    rows, sections, markdown = [], [], [
        "# ASES — accuratezza misurata", "",
        "Corpus sintetico annotato; non è una stima dell'accuratezza su qualsiasi repository.",
        f"Revisione etichette: {result['label_review']}", "",
        "| Capacità | Casi | Etichette | TP | FP | FN | TN | Precisione | Richiamo | F1 | Non valutati |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, row in result["families"].items():
        cells = [name, row["case_count"], row["labels"], row["true_positive"], row["false_positive"],
                 row["false_negative"], row["true_negative"], percent(row["precision"]),
                 percent(row["recall"]), percent(row["f1"]), row["unassessed"]]
        rows.append("<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in cells) + "</tr>")
        markdown.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in cells) + " |")
    markdown += ["", "TP: trovato correttamente; FP: falso allarme; FN: omissione; TN: negativo rispettato.",
                 "Precisione = TP/(TP+FP). Richiamo = TP/(TP+FN). — indica denominatore nullo, non 100%.",
                 "Le predizioni non annotate restano non valutate, salvo completezza esplicita nel solo ambito selezionato.", ""]
    for name, row in result["cases"].items():
        case = row["case"]
        status = "PASS" if row["passed"] else "FAIL"
        label = "ok" if row["passed"] else "bad"
        claims = []
        markdown += [f"## {name} — {status}", "", case["rationale"], "",
                     f"Ambito: {case['scope']}", ""]
        for field, title in (("true_positive", "TP · corretto"), ("false_positive", "FP · falso allarme"),
                             ("false_negative", "FN · omissione"), ("true_negative", "TN · negativo rispettato"),
                             ("unassessed_findings", "Non valutato")):
            for item in row[field]:
                claims.append(f"<tr><td>{escape(title)}</td><td><code>{escape(item)}</code></td></tr>")
                markdown.append(f"- {title}: {item}")
        diagnostics = {
            "Schemi validi": row["schema_valid"], "Unknown osservati": row["unknowns"],
            "Unknown obbligatori mancanti": row["missing_unknowns"],
            "Predizioni collassate dalla proiezione": row["collapsed_predictions"],
            "Stabilità dopo righe/commenti aggiunti": row.get("metamorphic", "non richiesta"),
            "Fuori capacità dichiarata": row["unsupported_claims"],
        }
        diagnostic_html = "".join(f"<li><strong>{escape(key)}:</strong> {escape(str(value))}</li>"
                                  for key, value in diagnostics.items())
        sources = "".join(f"<h4>{escape(path)}</h4><pre>{escape(source)}</pre>" for path, source in case["files"].items())
        sections.append(f"""<details class="case" data-status="{label}" data-family="{escape(case['family'], quote=True)}">
<summary><span class="badge {label}">{status}</span> {escape(name)} <span class="muted">· {escape(case['language'])}</span></summary>
<p>{escape(case['rationale'])}</p><p><strong>Ambito:</strong> {escape(str(case['scope']))}</p>
<div class="scroll"><table><thead><tr><th>Esito</th><th>Affermazione</th></tr></thead><tbody>{''.join(claims)}</tbody></table></div>
<ul>{diagnostic_html}</ul><h3>Sorgente del caso</h3>{sources}</details>""")
        markdown += [""] + [f"- {key}: {value}" for key, value in diagnostics.items()] + [""]
    limitations = "".join(f"<li>{escape(item)}</li>" for item in result["limitations"])
    families = "".join(f'<option value="{escape(name, quote=True)}">{escape(name)}</option>' for name in result["families"])
    passed = sum(row["passed"] for row in result["cases"].values())
    total = len(result["cases"])
    title = f"{passed}/{total} casi superati"
    markdown += ["## Limiti", ""] + [f"- {item}" for item in result["limitations"]]
    markdown += ["", f"Corpus SHA-256: {result['corpus_sha256']}",
                 f"Scanner/evaluator SHA-256: {result['evaluator_and_scanner_sha256']}",
                 f"Ambiente: {result['environment']}",
                 f"Generato UTC: {result['generated_utc']}", ""]
    (output / "REPORT.md").write_text("\n".join(markdown), encoding="utf-8")
    document = """<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'">
<title>ASES · accuratezza misurata</title><style>
:root{color-scheme:light dark;--bg:#f4f6fa;--fg:#19243a;--panel:#fff;--line:#d6deea;--muted:#536079}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,sans-serif}
main{max-width:1200px;margin:auto;padding:36px 24px 70px}h1{font-size:clamp(28px,4vw,44px);line-height:1.15;margin:12px 0}
h2{margin-top:32px}p{max-width:900px}.eyebrow{font-weight:750;letter-spacing:.1em;color:var(--muted)}
.panel,.case{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px;margin:14px 0}
.scroll{overflow-x:auto}table{border-collapse:collapse;min-width:680px;width:100%;font-size:14px}
td,th{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}
th{white-space:nowrap}.muted{color:var(--muted)}summary{cursor:pointer;font-weight:650}
.badge{display:inline-block;border-radius:6px;padding:2px 9px;font:700 12px/1.7 system-ui;margin-right:10px}
.ok{background:#d6f5e5;color:#115334}.bad{background:#ffe0df;color:#7c2020}
.filters{display:flex;flex-wrap:wrap;gap:16px;align-items:end;margin:20px 0}
label{display:flex;flex-direction:column;gap:5px;font-size:14px}input,select,button{font:inherit;padding:8px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--fg)}
label.check{flex-direction:row;align-items:center;padding:8px}button{cursor:pointer}
pre{overflow:auto;padding:14px;border:1px solid var(--line);border-radius:6px;font-size:13px}
code{overflow-wrap:anywhere}footer{font-size:13px;overflow-wrap:anywhere;margin-top:30px}
[hidden]{display:none!important}
@media(prefers-color-scheme:dark){:root{--bg:#101623;--fg:#e5ecf6;--panel:#192333;--line:#34445c;--muted:#afbdd2}}
</style></head><body><main>
<div class="eyebrow">ASES / VERIFICHE SEMANTICHE</div><h1>Quanto ci prende, davvero?</h1>
<p>Qui il verde va guadagnato. Ogni caso contiene sorgenti, risposte attese e risultati effettivi.
È un piccolo corpus sintetico: un termometro per capacità precise, non un voto universale al progetto.</p>
<section class="panel"><h2>TITLE</h2><p>REVIEW</p>
<p>Un caso passa se non ha falsi allarmi o omissioni e rispetta schemi, unknown richiesti, unicità della proiezione e controlli di stabilità richiesti.
Un caso fuori capacità può passare il controllo di prudenza senza contribuire ai positivi recuperati.</p>
<p><strong>Precisione:</strong> quante risposte valutate sono giuste. <strong>Richiamo:</strong> quante risposte attese sono state trovate.
F1 combina le due. «—» significa non misurabile. I negativi non gonfiano questi valori.</p>
<div class="scroll"><table><thead><tr><th>Capacità</th><th>Casi</th><th>Etichette</th><th>TP</th><th>FP</th><th>FN</th><th>TN</th><th>Precisione</th><th>Richiamo</th><th>F1</th><th>Non valutati</th></tr></thead><tbody>ROWS</tbody></table></div>
<p class="muted">TP = corretto · FP = falso allarme · FN = omissione · TN = negativo rispettato.
I risultati fuori dai selettori del caso non sono valutati: il rapporto non misura tutta la scansione.</p></section>
<h2>Guarda le prove</h2><div class="filters">
<label>Capacità<select id="family"><option value="">Tutte</option>FAMILIES</select></label>
<label>Cerca<input type="search" id="search" placeholder="es. flask, factory, observer"></label>
<label class="check"><input type="checkbox" id="errors">Solo casi non superati</label>
<button id="expand" type="button">Apri i casi visibili</button></div>
<p id="count" aria-live="polite"></p>SECTIONS
<section class="panel"><h2>Come leggere questi numeri</h2><ul>LIMITATIONS</ul>
<p>Le etichette sono verificabili nei sorgenti di ciascun caso. Nei casi dichiarati completi, ogni risposta extra
nel solo ambito selezionato è un falso allarme. Negli altri, ciò che non è annotato resta non valutato.
Un unknown non vale come risposta corretta a una domanda che ASES non sa risolvere.</p></section>
<footer>Generato: GENERATED<br>Ambiente: ENVIRONMENT<br>Corpus SHA-256: CORPUS<br>Scanner/evaluator SHA-256: CODE<br>
Report autonomo: nessuna richiesta di rete, nessun sorgente eseguito.</footer>
</main><script>
const cases=[...document.querySelectorAll('.case')],family=document.getElementById('family'),
search=document.getElementById('search'),errors=document.getElementById('errors');
function filter(){let visible=0;for(const item of cases){
item.hidden=Boolean((family.value&&item.dataset.family!==family.value)||(errors.checked&&item.dataset.status!=='bad')||
!item.textContent.toLowerCase().includes(search.value.toLowerCase()));if(!item.hidden)visible++}
document.getElementById('count').textContent=visible+' casi visibili su '+cases.length}
for(const element of [family,search,errors])element.addEventListener('input',filter);
document.getElementById('expand').addEventListener('click',()=>{for(const item of cases)if(!item.hidden)item.open=true});
filter();
</script></body></html>"""
    replacements = {"TITLE": escape(title), "REVIEW": escape(result["label_review"]),
                    "ROWS": "".join(rows), "FAMILIES": families, "SECTIONS": "".join(sections),
                    "LIMITATIONS": limitations, "GENERATED": escape(result["generated_utc"]),
                    "CORPUS": result["corpus_sha256"], "CODE": result["evaluator_and_scanner_sha256"],
                    "ENVIRONMENT": escape(str(result["environment"]))}
    # Substitute once: source text containing a placeholder must remain source text.
    import re
    document = re.sub("|".join(replacements), lambda match: replacements[match.group()], document)
    (output / "report.html").write_text(document, encoding="utf-8")
