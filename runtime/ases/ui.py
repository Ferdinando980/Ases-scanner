"""A temporary, loopback-only desk over the existing scanner and snapshot queries."""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO, IncrementalNewlineDecoder
import codecs
import json
from pathlib import Path
import secrets
import os
import signal
import subprocess
import sys
import tempfile
import threading
from time import monotonic
from urllib.parse import parse_qs, urlsplit
import webbrowser
import zipfile

MAX_EXPORT_BYTES = 128 * 1024 * 1024
MAX_EXPORT_INPUT_BYTES = 512 * 1024 * 1024


class _ExportBuffer(BytesIO):
    """Stop compression before the in-memory ZIP can exceed its delivery bound."""
    def write(self, data):
        if self.tell() + len(data) > MAX_EXPORT_BYTES:
            raise ValueError("Full export exceeds the 128 MiB compressed limit; the reduced export remains available.")
        return super().write(data)

from .snapshot import trace_snapshot
from .ui_operations import DOCUMENTS, clean_preview, load_context

ASSETS = Path(__file__).with_name("ui_assets")
PAGE_SIZE = 40
SOURCE_LIMIT = 128 * 1024 * 1024


def source_window(path, requested, expected):
    """Hash the entire bounded source, retaining only a short line window."""
    decoder = IncrementalNewlineDecoder(codecs.getincrementaldecoder('utf-8')('replace'), translate=True)
    digest, size, number, prefix, rows = sha256(), 0, 1, '', []
    start, end, truncated = max(1, requested-8), requested+24, False
    def consume(text):
        nonlocal number, prefix, truncated
        parts = text.split('\n')
        for index, part in enumerate(parts):
            if start <= number <= end:
                truncated |= len(prefix)+len(part)>2000
                prefix=(prefix+part)[:2000]
            elif index==len(parts)-1 and part:
                prefix='x'  # Only whether the last line exists matters.
            if index < len(parts)-1:
                if start <= number <= end: rows.append(prefix)
                number += 1
                prefix=''
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            size += len(chunk)
            if size > SOURCE_LIMIT:
                raise ValueError('Source preview exceeds the 128 MiB verification budget; the saved analysis remains available.')
            digest.update(chunk)
            consume(decoder.decode(chunk))
    consume(decoder.decode(b'', final=True))
    total=number if prefix else number-1
    if prefix and start<=number<=end: rows.append(prefix)
    if digest.hexdigest()!=expected:
        raise ValueError('The source changed after this analysis. Scan again to see current evidence.')
    if not 1<=requested<=max(1,total):
        raise ValueError('The requested line does not exist.')
    return {'start':start,'total_lines':total,'lines':rows,'lines_truncated':truncated,'verified_bytes':size}
KIT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ("SOW.md", "RAD.md", "SDD.md", "ODD.md", "DDR.md", "TP.md", "TCS.md", "TIR.md", "TSR.md", "TESTING-BASELINE.md", "RECOVERED-SYSTEM-OVERVIEW.md", "RECOVERED-RAD.md", "RECOVERED-SDD.md", "RECOVERED-ODD.md")


def choose_folder():
    if sys.platform == "darwin":
        raise ValueError("The folder picker is unavailable in this server. Paste the project path instead.")
    try:
        import tkinter
        from tkinter.filedialog import askdirectory
    except ImportError as exc:
        raise ValueError("The folder picker is unavailable. Paste the project path instead.") from exc
    root = None
    try:
        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        return askdirectory(parent=root, title="ASES — Select project folder", mustexist=True)
    except tkinter.TclError as exc:
        raise ValueError("The folder picker is unavailable. Paste the project path instead.") from exc
    finally:
        if root is not None:
            root.destroy()


def kit_catalog():
    available = (KIT_ROOT / "STANDARD.md").is_file() and (KIT_ROOT / "templates").is_dir()
    if available:
        return {"available": True,
                "templates": {name: (KIT_ROOT / "templates" / name).read_text(encoding="utf-8") for name in TEMPLATES},
                "guide": (KIT_ROOT / "docs" / "ENGINEERING-WORKFLOW.md").read_text(encoding="utf-8")}
    from importlib.resources import files
    resource = files("ases.engineering").joinpath("resources")
    return {"available": True,
            "templates": {name: resource.joinpath("templates/" + name).read_text(encoding="utf-8") for name in TEMPLATES},
            "guide": resource.joinpath("guide.md").read_text(encoding="utf-8")}


def kit_download(documents):
    if not isinstance(documents, dict) or not documents or any(name not in TEMPLATES or not isinstance(value, str) or len(value) > 100000 for name, value in documents.items()):
        raise ValueError("Select known document templates and bounded text.")
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, value in documents.items():
            archive.writestr(name, value)
    return buffer.getvalue()


def brief(report, language="it"):
    """Describe measured counts without promoting coverage to a correctness score."""
    c = report["counts"]
    languages = ", ".join(report["languages"]) or ("non riconosciuti" if language == "it" else "unrecognized")
    if language == "it":
        return [
            f"Ho inventariato {c['files']} file sorgente e ricostruito {c['entities']} elementi strutturali. Linguaggi inventariati: {languages}.",
            f"Route ricostruite: {c['routes']}. Proposte o contraddizioni da rivedere: {c['review']}. Sono candidati alla revisione, non difetti confermati.",
            f"Restano {c['unknowns']} incertezze esplicite; {c['incomplete_files']} file hanno copertura strutturale parziale o sconosciuta. I collegamenti statici richiedono verifica umana.",
            "Il progetto non è stato eseguito. Nessun risultato, da solo, certifica qualità, sicurezza o test superati.",
        ]
    return [
        f"Inventoried {c['files']} files and recovered {c['entities']} structural elements. Inventoried languages: {languages}.",
        f"Recovered {c['routes']} routes and {c['review']} suggestions or contradictions to review. These are review candidates, not confirmed defects.",
        f"{c['unknowns']} explicit unknowns remain; {c['incomplete_files']} files have partial or unknown structural coverage. Static links need human verification.",
        "The project was not executed. No result alone certifies quality, security, or passing tests.",
    ]


def review_highlights(rows):
    """One representative per family; preserve all underlying findings in the feed."""
    relevant=[r for r in rows if r.get('status') in {'CONTRADICTED','OPPORTUNITY'}] or rows
    ordered=sorted(relevant,key=lambda row: ({'CONTRADICTED':0,'OPPORTUNITY':1}.get(row.get('status'),2),
        {'strong':0,'direct':1}.get(row.get('evidence_strength'),2),row['id']))
    groups={}
    for row in ordered:groups.setdefault(row.get('pattern') or row.get('rule_id') or row['id'],[]).append(row)
    return [{**group[0],'group_count':len(group),
             'group_files':len({r.get('location',{}).get('path') for r in group if r.get('location',{}).get('path')})}
            for group in list(groups.values())[:5]]


def build_report(result, context, findings):
    from .recovery.patterns import PATTERN_RULES,PROFILE as pattern_profile
    entities = context["entities"]
    coverage = context["coverage"]
    files = coverage.get("files", {})
    rows = findings["findings"]
    review = sum(row.get("status") in {"CONTRADICTED", "OPPORTUNITY"} for row in rows)
    languages = result["inventory"].get("languages", [])
    report = {
        "project": context["project"],
        "snapshot_id": context["snapshot_id"],
        "languages": sorted(row["name"] if isinstance(row, dict) else row for row in languages),
        "counts": {
            "files": len(context["source_manifest"]), "entities": len(entities),
            "routes": sum(e["kind"] == "route" and not e.get("properties", {}).get("is_test_code") for e in entities),
            "findings": len(rows), "review": review,
            "unknowns": len(context.get("analysis_unknowns", [])) + len(context.get("unknowns", [])),
            "incomplete_files": sum(f.get("status") in {"PARTIAL", "UNKNOWN"} for f in files.values()),
            "relations": len(context["structural_relations"]),
        },
        "file_coverage": dict(Counter(f.get("status", "UNKNOWN") for f in files.values())),
        "structure": dict(sorted(Counter(e["kind"] for e in entities if not e.get("properties", {}).get("is_test_code")).items())),
        "relationship_coverage": {
            family: dict(Counter(families.get(family, {}).get("status", "UNKNOWN") for families in coverage.get("relationship_families", {}).values()))
            for family in ("declarations", "imports", "calls", "controls", "tests", "type_heritage")
        },
        "documents": sorted(p.name for p in (Path(result["output"]) / "docs").glob("*") if p.is_file()),
        "validation": result["validation"]["status"],
        "source_scope": context.get("source_scope", {}),
        "custom_http_routing_unresolved": any(row.get("reason") in {"python_custom_http_routing_not_reconstructed", "python_custom_http_routing_partial"}
                                              for row in context.get("analysis_unknowns", []) + context.get("unknowns", [])),
        "highlights": review_highlights(rows),
        "pattern_catalog": {'rules':len(PATTERN_RULES),'families':sorted({v[1] for v in PATTERN_RULES.values()}),
                            'method':pattern_profile,'snapshot_method':context.get('analysis_profile',{}).get('parser',{}).get('patterns')},
        "weak_pattern_hints": len(findings.get('hints',[])),
        "design_reviews": [row for row in rows + findings.get('hints',[]) if row.get('design_review')],
        "design_review_coverage": ({'counts':dict(Counter(r['status'] for r in findings['design_review_coverage'])),
                                    'files':findings['design_review_coverage']}
                                   if 'design_review_coverage' in findings else None),
        "route_preview": [{"name": e["name"], "path": e.get("path")} for e in entities if e["kind"] == "route" and not e.get("properties", {}).get("is_test_code")][:10],
    }
    report["brief"] = {lang: brief(report, lang) for lang in ("it", "en")}
    return report


def readable_report(report, language="it"):
    it = language == "it"
    def line(value):
        return str(value).replace("\r", " ").replace("\n", " ")
    c = report["counts"]
    if report["action"] == "site":
        data = report.get("data") or {}
        counts = data.get("counts", {})
        lines = ["# Osservazione del sito pubblico" if it else "# Public website observation", "",
                 line(report["project"].get("source_uri", report["project"].get("name", "site"))), "",
                 ("Pagine osservate: " if it else "Observed pages: ") + str(counts.get("pages", len(data.get("pages", [])))),
                 ("Form osservati: " if it else "Observed forms: ") + str(counts.get("forms", 0)), "",
                 "HTML pubblico osservato senza eseguire JavaScript. Il codice backend e il comportamento runtime non sono stati verificati." if it else "Public HTML observed without executing JavaScript. Backend source and runtime behavior were not verified.", ""]
        lines.extend("- " + line(value) for value in data.get("limits", []))
        return "\n".join(lines) + "\n"
    title = "Analisi del progetto" if it else "Project analysis"
    lines = [f"# {title} — {line(report['project'].get('name', 'project'))}", "",
             "## Il quadro" if it else "## The picture", "", *report["brief"][language][:2], "",
             "## Struttura ricostruita" if it else "## Recovered structure", ""]
    for kind, count in report["structure"].items():
        lines.append(f"- {kind}: {count}")
    lines += ["", "## Route riconosciute" if it else "## Recognized routes", ""]
    for route in report["route_preview"]:
        lines.append(f"- {line(route['name'])} — {line(route['path'])}")
    if not c["routes"]:
        lines.append("Nessuna route ricostruita nelle forme supportate. Questo non prova che il progetto non esponga endpoint." if it else "No routes recovered in supported forms. This does not prove that the project has no endpoints.")
    if c["routes"] > len(report["route_preview"]):
        lines.append("Anteprima di 10 route; la UI e lo snapshot conservano le altre." if it else "Preview of 10 routes; the desk and snapshot retain the others.")
    lines += ["", "## Da verificare" if it else "## To check", ""]
    candidates = [row for row in report["highlights"] if row.get("status") in {"OPPORTUNITY", "CONTRADICTED"}]
    if not candidates:
        lines.append("Le regole applicate non hanno prodotto proposte di modifica o contraddizioni. Non è una certificazione di assenza di problemi." if it else "The applied rules recovered no change suggestions or contradictions. This does not certify absence of problems.")
    for row in candidates:
        lines += [f"### {line(row.get('pattern') or row['id'])}", "", f"{row['status']} — {line(row.get('message', ''))}", ""]
        lines.extend(f"- {line(e)}" for e in row.get("evidence", [])[:3])
    if c["review"] > len(candidates):
        lines.append("Altre proposte sono disponibili nella UI e nel feed completo; questa è una prima lettura." if it else "More suggestions are available in the desk and full findings feed; this is a first reading.")
    lines += ["", "## Dove l’analisi si ferma" if it else "## Where analysis stops", "", report["brief"][language][2], "", report["brief"][language][3], "",
              "Le directory escluse sono fuori perimetro. I loro contenuti non sono stati valutati. I collegamenti ai test non ne dimostrano esecuzione o successo." if it else "Excluded directories are outside scope. Their contents were not assessed. Test links do not establish execution or success.", "",
              "## Il prossimo passo" if it else "## Next step", "",
              "Apri le prove di un risultato o segui una route nella Mappa del codice. Verifica i sorgenti e poi esegui i test del progetto prima di decidere una modifica." if it else "Open a result's evidence or follow a route in Code map. Check the source and run the project tests before deciding a change.", "",
              "La documentazione recuperata descrive l’implementazione. Requisiti e decisioni originali vanno confermati con le persone coinvolte." if it else "Recovered documentation describes implementation. Original requirements and decisions need confirmation from the people involved.", "",
              "Snapshot: " + report["snapshot_id"], ""]
    return "\n".join(lines)


class Desk:
    """Own one scan at a time; discard its temporary output on replacement or exit."""

    def __init__(self, source=""):
        self.initial_source = source
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.state = {"status": "idle"}
        self.result = None
        self.worker = None
        self.temporary = None
        self.resolved = None
        self.pending = None
        self.process = None
        self.cancel_event = threading.Event()
        self.started = None

    def start(self, source, *, action="scan", options=None):
        if not isinstance(source, str) or not source.strip() or len(source) > 4096:
            raise ValueError("Enter a project path or URL.")
        if action not in {"scan", "site", "open", "artifact", "reconcile", "compare", "audit", "export", "selfcheck", "accuracy", "clean", "interpret", "runtime-check"}:
            raise ValueError("Unknown desk operation.")
        options = {**(options or {}), "source": source.strip()}
        with self.lock:
            if self.state["status"] in {"running", "cancelling"} or self.worker is not None and self.worker.is_alive():
                raise ValueError("An analysis is already running.")
            self.initial_source = source
            self.pending = tempfile.TemporaryDirectory(prefix="ases-desk-")
            workspace = Path(self.pending.name)
            (workspace / "request.json").write_text(json.dumps({"action": action, "options": options}), encoding="utf-8")
            self.cancel_event = threading.Event()
            self.started = monotonic()
            self.state = {"status": "running", "stage": "starting"}
            self.worker = threading.Thread(target=self._scan, args=(workspace, self.cancel_event))
            self.worker.start()

    @staticmethod
    def _stop_process(process):
        if process is None or process.poll() is not None:
            return
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True,
                           timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=10)

    def _scan(self, workspace, cancelled):
        try:
            with (workspace / "worker.log").open("wb") as log:
                self.process = subprocess.Popen([sys.executable, "-I", "-m", "ases.ui_worker", str(workspace)],
                                                stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                                                start_new_session=os.name != "nt")
                while self.process.poll() is None:
                    if cancelled.wait(0.2) or monotonic() - self.started > 300:
                        self._stop_process(self.process)
                        with self.lock:
                            self.state = {"status": "cancelled"} if cancelled.is_set() else {
                                "status": "failed", "code": "timeout", "error": "Analysis exceeded the five-minute desk limit. Narrow the source scope and try again."}
                        return
                if cancelled.is_set():
                    with self.lock:
                        self.state = {"status": "cancelled"}
                    return
                if self.process.returncode:
                    error_file = workspace / "error.json"
                    error = json.loads(error_file.read_text(encoding="utf-8")) if error_file.exists() else {
                        "code": "worker_stopped", "stage": "analysis", "detail": "The isolated scanner stopped unexpectedly. The desk is still available."}
                    with self.lock:
                        self.state = {"status": "failed", "error": error["detail"], "code": error["code"], "stage": error["stage"]}
                    return
            operation = json.loads((workspace / "result.json").read_text(encoding="utf-8"))
            output = workspace / "report.ases"
            result = {**operation, "root": Path(operation["root"]) if operation["root"] else None,
                      "output": output, "data": operation["report"].get("data")}
            if operation["report"]["kind"] == "scan":
                context = load_context(output)
                findings_path = output / "scanner-findings.json"
                findings = json.loads(findings_path.read_text(encoding="utf-8")) if findings_path.exists() else {"findings": [], "hints": [], "suppressed": []}
                observations = {o["id"]: o for o in context["observations"]}
                entities = [{**entity, "state": observations[entity["observation_refs"][0]]["state"] if entity["observation_refs"] else "UNKNOWN",
                             "locations": [loc for ref in entity["observation_refs"] for loc in observations[ref]["locations"]]}
                            for entity in context["entities"]]
                result.update({"context": context, "entities": entities, "findings": findings,
                               "sources": {s["path"]: s["sha256"] for s in context["source_manifest"]},
                               "locations": {loc["path"] for o in observations.values() for loc in o["locations"]}})
            with self.lock:
                if cancelled.is_set():
                    self.state = {"status": "cancelled"}
                    return
                self._discard()
                self.result = result
                self.temporary, self.pending = self.pending, None
                self.state = {"status": "complete"}
        except Exception as exc:
            with self.lock:
                self.state = {"status": "failed", "error": str(exc)[:1200]}
        finally:
            with self.lock:
                if self.pending is not None:
                    self.pending.cleanup()
                    self.pending = None
                self.state["elapsed"] = round(monotonic() - self.started, 1)

    def status(self):
        with self.lock:
            state = {**self.state, "has_result": self.result is not None}
            if self.started is not None and state["status"] in {"running", "cancelling"}:
                state["elapsed"] = round(monotonic() - self.started, 1)
            if self.pending is not None and state["status"] in {"running", "cancelling"}:
                try:
                    progress = json.loads((Path(self.pending.name) / "progress.json").read_text(encoding="utf-8"))
                    state["stage"] = progress["stage"]
                    self.state["stage"] = progress["stage"]
                except (OSError, ValueError):
                    pass
            return state

    def cancel(self):
        with self.lock:
            if self.state["status"] in {"running", "cancelling"}:
                self.cancel_event.set()
                self.state = {**self.state, "status": "cancelling"}
            return self.status()

    def _ready(self):
        if self.result is None:
            raise ValueError("No completed analysis is available.")
        return self.result

    def items(self, collection, query="", offset=0):
        current = self._ready()
        context = current.get("context")
        if context is None:
            raise ValueError("This operation does not contain a source snapshot.")
        if collection in {"entities", "routes"}:
            rows = sorted(current["entities"], key=lambda e: (e["kind"] != "route", e.get("path") or "", e["name"], e["id"]))
            if collection == "routes":
                rows = [e for e in rows if e["kind"] == "route" and not e.get("properties", {}).get("is_test_code")]
        elif collection in {"findings", "review"}:
            order = {"CONTRADICTED": 0, "OPPORTUNITY": 1, "OBSERVED": 2, "INFERRED": 3}
            rows = sorted(current["findings"]["findings"], key=lambda r: (order.get(r["status"], 9), r["id"]))
            if collection == "review":
                rows = [row for row in rows if row["status"] in {"CONTRADICTED", "OPPORTUNITY"}]
        elif collection in {"hints", "suppressed"}:
            rows = current["findings"].get(collection, [])
        elif collection == "unknowns":
            rows = context.get("analysis_unknowns", []) + context.get("unknowns", [])
        elif collection in {"observations", "behaviors", "controls", "tests", "external_systems", "structural_relations"}:
            rows = context.get(collection, [])
        elif collection == "files":
            rows = [{"path": p, **value} for p, value in sorted(context["coverage"].get("files", {}).items())]
        else:
            raise ValueError("Unknown collection.")
        if query:
            # Search human-readable fields, not opaque IDs, hashes, or nested snapshot metadata.
            rows = [r for r in rows if query.casefold() in " ".join(str(r.get(k, "")) for k in ("name", "path", "kind", "message", "status", "reason", "statement", "pattern")).casefold()]
        if offset < 0:
            raise ValueError("Invalid page.")
        return {"items": rows[offset:offset + PAGE_SIZE], "total": len(rows), "offset": offset, "page_size": PAGE_SIZE}

    def engineering(self, args):
        from .engineering.service import load_model, read_json, apply_review
        current = self._ready()
        if not (current["output"] / "engineering-model.json").is_file():
            return {"available": False, "reason": "This snapshot predates engineering document recovery. Scan again."}
        path = current["output"] / "engineering-model.json"
        stamp = (path.stat().st_mtime_ns, path.stat().st_size)
        if current.get("engineering_stamp") != stamp:
            current["engineering_model"] = load_model(current["output"])
            current["engineering_stamp"] = stamp
        model = current["engineering_model"]
        review_path = current["output"] / "engineering-review.json"
        review = read_json(review_path, 1024 * 1024) if review_path.is_file() else None
        model = apply_review(model, review)
        collections = ("requirements", "recovered_requirements", "operations", "user_requirements", "api", "scenarios", "test_cases", "test_results", "diagrams", "issues", "sources")
        key = args.get("collection", "requirements")
        if key not in collections:
            raise ValueError("Unknown engineering collection")
        rows = model.get(key, [])
        query = args.get("query", "").casefold()
        if query:
            rows = [r for r in rows if query in " ".join(str(r.get(k, "")) for k in ("id", "declared_id", "name", "path", "statement", "text")).casefold()]
        offset = int(args.get("offset", 0))
        if offset < 0:
            raise ValueError("Invalid engineering page")
        if args.get("record"):
            rows = [r for r in rows if r["id"] == args["record"]]
            offset = 0
        items = []
        for row in rows[offset:offset + 20]:
            # Full text is available in bounded source excerpts and the package download.
            item = {k: v for k, v in row.items() if k not in {"units", "declarations", "definition"}}
            if row.get("declarations"):
                variants = []
                seen = set()
                for declaration in row["declarations"]:
                    text = declaration["statement"].strip()
                    if text != row.get("statement", "").strip() and text not in seen:
                        variants.append({"statement": text[:2500], "locations": declaration["locations"], "role": declaration["role"]})
                        seen.add(text)
                item["alternative_declarations"] = variants[:5]
            if row.get("statement_en") and args.get("lang") == "en":
                item["statement"] = row["statement_en"]
            if key == "sources":
                item["units_read"] = len(row["units"])
            item["links"] = [l for l in model["links"] if l.get("source") == row["id"] or l.get("target") == row["id"]][:40]
            items.append(item)
        return {"available": True, "model_digest": model["model_digest"], "snapshot_id": model["snapshot_id"],
                "review_key": sha256(str(current.get("context", {}).get("project", {}).get("source_uri") or current.get("root") or current["report"].get("project", {})).encode()).hexdigest(),
                "counts": {k: len(model.get(k, [])) for k in collections}, "coverage": model["coverage"],
                "requirement_kinds": {kind: sum(row.get("kind") == kind for row in model.get("requirements", [])) for kind in ("functional", "nonfunctional", "unspecified")},
                "source_test_definitions": len(model.get("structure", {}).get("tests", [])),
                "entry_budget_reached": any(row.get("path") is None and "1000-entry interpretation limit" in row.get("reason", "")
                                            for row in model.get("behavior_coverage", [])),
                "review": review, "review_state": model.get("review_state"), "items": items, "total": len(rows), "offset": offset}

    def engineering_source(self, args):
        from .engineering.service import load_model
        model = load_model(self._ready()["output"])
        source = next((s for s in model["sources"] if s["path"] == args.get("path")), None)
        if not source:
            raise ValueError("Source not present in the saved engineering model")
        units = source["units"]
        for key in ("page", "sheet", "row", "line", "paragraph", "element"):
            if args.get(key):
                units = [u for u in units if str(u.get(key)) == str(args[key])]
        return {"path": source["path"], "sha256": source["sha256"], "extraction": source["extraction"],
                "limitations": source["limitations"], "units": units[:5], "truncated": len(units) > 5}

    def save_engineering_review(self, review, language="it"):
        from .engineering.service import load_model, apply_review, write_documents
        from .renderers.markdown import doc_signature
        current = self._ready()
        if not isinstance(review, dict) or not review:
            raise ValueError("Provide an explicit engineering review")
        if self.state["status"] in {"running", "cancelling"}:
            raise ValueError("Wait for the running analysis before reviewing documents")
        model = load_model(current["output"])
        applied = apply_review(model, review)
        if language not in {"it", "en"}:
            raise ValueError("Unknown document language")
        signature = doc_signature(json.loads((current["output"] / "manifest.json").read_text(encoding="utf-8")))
        write_documents(model, current["output"] / "docs", language, review, signature=signature)
        (current["output"] / "engineering-review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"saved": True, "review_state": applied["review_state"]}

    def source(self, relative, line=1):
        current = self._ready()
        if "sources" not in current:
            raise ValueError("This operation does not contain source evidence.")
        if relative not in current["sources"] or relative not in current["locations"]:
            raise ValueError("This file is not referenced by the saved evidence.")
        root = current["root"]
        if root is None:
            raise ValueError("No source folder is attached. Reopen the snapshot with its local source folder.")
        path = root / relative
        if not path.resolve(strict=True).is_relative_to(root):
            raise ValueError("The source leaves the selected project.")
        for part in (path, *path.parents):
            if part == root:
                break
            if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
                raise ValueError("Linked source paths are not available in this view.")
        return {"path": relative, "line": line, **source_window(path,line,current['sources'][relative]), "snapshot_id": current["context"]["snapshot_id"]}

    def download(self, language="it", mode="full"):
        current = self._ready()
        report = current["report"]
        if mode not in {"full", "reduced"}:
            raise ValueError("Unknown export mode.")
        if mode == "reduced":
            counts = {key: value for key, value in report.get("counts", {}).items()
                      if key in {"files", "entities", "routes", "findings", "review", "unknowns"}
                      and type(value) is int and value >= 0}
            policy = {"schema": "ases-reduced-report/1", "mode": "reduced", "counts": counts,
                      "target_tests_executed": 0, "reopenable_snapshot": False,
                      "omitted": ["project name", "source paths and fragments", "snapshot identifiers", "document text", "finding details", "user notes", "models and revisions"],
                      "limits": "Aggregates can still disclose project characteristics. Review before sharing. This is not a complete or reopenable analysis."}
            text = ("# ASES — rapporto ridotto\n\nSolo conteggi aggregati. Sorgenti, documenti, note e revisioni sono omessi. Non si può riaprire come analisi: conserva il pacchetto completo per riprendere il lavoro. Anche i conteggi possono rivelare caratteristiche del progetto; controllali prima di condividere. Nessun test del progetto eseguito.\n\n" if language == "it" else
                    "# ASES — reduced report\n\nAggregate counts only. Sources, documents, notes and reviews are omitted. This cannot be reopened as an analysis: keep the complete package to resume work. Counts can still reveal project characteristics; review before sharing. No target tests executed.\n\n")
            text += "\n".join("- " + key + ": " + str(value) for key, value in counts.items()) + "\n"
            buffer = BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("START-HERE.md", text)
                archive.writestr("EXPORT-CONTENTS.json", json.dumps(policy, ensure_ascii=False, indent=2))
            return buffer.getvalue()
        paths = [p for p in sorted(current["output"].rglob("*")) if p.is_file() and not p.is_symlink()]
        if sum(path.stat().st_size for path in paths) > MAX_EXPORT_INPUT_BYTES:
            raise ValueError("Full export exceeds 512 MiB of uncompressed input. Narrow the source scope or use the CLI; the reduced export remains available.")
        name = report.get("project", {}).get("name", report["action"])
        paragraphs = report.get("brief", {}).get(language, ["Operation: " + report["action"], "See operation-result.json for the measured result and its limits."])
        summary = readable_report(report, language) if report["kind"] == "scan" else "# ASES — " + name + "\n\n" + "\n\n".join(paragraphs)
        if "snapshot_id" in report:
            summary += "\n\nSnapshot: " + report["snapshot_id"] + "\n"
        summary += "\n" + ("I dettagli e le prove sono nella cartella docs e nei JSON allegati." if language == "it" else "Details and evidence are in docs and the attached JSON files.") + "\n"
        buffer = _ExportBuffer()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("START-HERE.md", summary)
            remaining = MAX_EXPORT_INPUT_BYTES
            for path in paths:
                with path.open('rb') as source, archive.open(path.relative_to(current["output"]).as_posix(), 'w') as destination:
                    while chunk := source.read(min(65536, remaining + 1)):
                        if len(chunk) > remaining:
                            raise ValueError("Full export exceeds 512 MiB of uncompressed input; the reduced export remains available.")
                        remaining -= len(chunk)
                        destination.write(chunk)
            archive.writestr("EXPORT-CONTENTS.json", json.dumps({"schema": "ases-full-report/1", "mode": "full",
                "files": archive.namelist() + ["EXPORT-CONTENTS.json"], "contains": ["source paths and possible fragments", "document text", "models", "saved user notes and revisions"],
                "limits": "Inspect before sharing. Full analysis may contain private information; sources themselves are not bundled as a separate checkout."}, indent=2))
        return buffer.getvalue()

    def clear(self):
        with self.lock:
            if self.state["status"] in {"running", "cancelling"}:
                raise ValueError("Wait for the running operation before clearing the session.")
            self._discard()
            self.state = {"status": "idle"}

    def remove_output(self, fingerprint):
        from .pipeline import clean_output
        with self.lock:
            current = self._ready()
            if current["action"] != "clean" or current["data"]["status"] != "AWAITING_CONFIRMATION":
                raise ValueError("Preview an output before removing it.")
            preview = current["data"]
            latest = clean_preview(preview["target"])
            if not isinstance(fingerprint, str) or fingerprint != preview["fingerprint"] or latest["fingerprint"] != fingerprint:
                raise ValueError("The output changed after the preview. Inspect it again.")
            clean_output(Path(preview["target"]))
            preview["status"] = "REMOVED"
            (current["output"] / "operation-result.json").write_text(json.dumps(preview, indent=2), encoding="utf-8")
            return current["report"]

    def _discard(self):
        self.result = None
        if self.resolved is not None:
            self.resolved.cleanup()
            self.resolved = None
        if self.temporary is not None:
            self.temporary.cleanup()
            self.temporary = None

    def close(self):
        self.cancel()
        if self.worker is not None:
            self.worker.join()
        with self.lock:
            self._discard()


def create_server(desk, port=0):
    if not 0 <= port <= 65535:
        raise ValueError("Port must be between 0 and 65535.")

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *args):
            pass  # No paths, capability tokens, or source details in access logs.

        def send(self, status, data, content_type="application/json; charset=utf-8", download=False):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
            if download:
                self.send_header("Content-Disposition", 'attachment; filename="ases-report.zip"')
            self.end_headers()
            self.wfile.write(data)

        def permitted(self):
            authority = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != authority:
                self.send(403, {"error": "Invalid local host."})
                return False
            origin = self.headers.get("Origin")
            if origin is not None and origin != "http://" + authority:
                self.send(403, {"error": "Foreign origins are not allowed."})
                return False
            if self.path.startswith("/api/") and not secrets.compare_digest(self.headers.get("X-ASES-Token", "").encode("utf-8"), desk.token.encode("utf-8")):
                self.send(403, {"error": "Open the session link printed by ases ui."})
                return False
            return True

        def do_GET(self):
            if not self.permitted():
                return
            target = urlsplit(self.path)
            args = {key: value[0] for key, value in parse_qs(target.query).items()}
            try:
                static = {"/": ("index.html", "text/html"), "/app.css": ("app.css", "text/css"), "/app.js": ("app.js", "text/javascript")}
                if target.path in static:
                    name, mime = static[target.path]
                    self.send(200, (ASSETS / name).read_bytes(), mime + "; charset=utf-8")
                    return
                with desk.lock:
                    if self.headers.get("X-ASES-Snapshot") and self.headers["X-ASES-Snapshot"] != desk._ready()["report"].get("snapshot_id"):
                        raise ValueError("The session changed. Open the current analysis again.")
                    if target.path == "/api/config":
                        payload = {"source": desk.initial_source}
                    elif target.path == "/api/kit":
                        payload = kit_catalog()
                    elif target.path == "/api/status":
                        payload = desk.status()
                    elif target.path == "/api/report":
                        payload = desk._ready()["report"]
                    elif target.path == "/api/items":
                        payload = desk.items(args.get("collection", "entities"), args.get("q", "")[:200], int(args.get("offset", "0")))
                    elif target.path == "/api/source":
                        payload = desk.source(args.get("path", ""), int(args.get("line", "1")))
                    elif target.path == "/api/trace":
                        current = desk._ready()
                        if "context" not in current:
                            raise ValueError("This operation does not contain a source snapshot.")
                        payload = trace_snapshot(current["context"], args.get("id", ""), direction=args.get("direction", "forward"), max_nodes=64)
                    elif target.path == "/api/document":
                        name = args.get("name", "")
                        if name not in DOCUMENTS:
                            raise ValueError("Unknown analysis document.")
                        with (desk._ready()["output"] / "docs" / name).open(encoding="utf-8") as stream:
                            text = stream.read(120001)
                        lines = text[:120000].splitlines()
                        payload = {"name": name, "text": "\n".join(lines[:1500]), "truncated": len(text) > 120000 or len(lines) > 1500}
                    elif target.path == "/api/engineering":
                        payload = desk.engineering(args)
                    elif target.path == "/api/engineering-source":
                        payload = desk.engineering_source(args)
                    elif target.path == "/api/download":
                        lang = args.get("lang", "it")
                        if lang not in {"it", "en"}:
                            raise ValueError("Unknown report language.")
                        self.send(200, desk.download(lang, args.get("mode", "full")), "application/zip", download=True)
                        return
                    else:
                        self.send(404, {"error": "Not found."})
                        return
                    self.send(200, payload)
            except (ValueError, OSError) as exc:
                self.send(400, {"error": str(exc)[:1200]})

        def do_POST(self):
            if not self.permitted():
                return
            if self.path not in {"/api/scan", "/api/clear", "/api/kit-download", "/api/remove-output", "/api/cancel", "/api/choose-folder", "/api/engineering-review"}:
                self.send(404, {"error": "Not found."})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                bound = 1024 * 1024 if self.path in {"/api/kit-download", "/api/engineering-review"} else 16384
                if not 0 < size <= bound or self.headers.get("Content-Type") != "application/json" or self.headers.get("Transfer-Encoding"):
                    raise ValueError("Expected a bounded JSON request.")
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise ValueError("Expected an object.")
                if self.path == "/api/engineering-review":
                    with desk.lock:
                        if self.headers.get("X-ASES-Snapshot") and self.headers["X-ASES-Snapshot"] != desk._ready()["report"].get("snapshot_id"):
                            raise ValueError("The session changed. Open the current analysis again.")
                        self.send(200, desk.save_engineering_review(body.get("review"), body.get("language", "it")))
                    return
                if self.path == "/api/cancel":
                    self.send(200, desk.cancel())
                    return
                if self.path == "/api/choose-folder":
                    self.send(200, {"path": choose_folder()})
                    return
                if self.path == "/api/clear":
                    desk.clear()
                    self.send(200, {"status": "idle"})
                    return
                if self.path == "/api/remove-output":
                    self.send(200, desk.remove_output(body.get("fingerprint")))
                    return
                if self.path == "/api/kit-download":
                    self.send(200, kit_download(body.get("documents")), "application/zip", download=True)
                    return
                options = body.get("options", {})
                if not isinstance(options, dict):
                    raise ValueError("Expected operation options.")
                desk.start(body.get("source"), action=body.get("action", "scan"), options=options)
                self.send(202, {"status": "running"})
            except (ValueError, OSError) as exc:
                self.send(400, {"error": str(exc)[:1200]})

    # Binding is intentionally not configurable: this is a local single-user tool.
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(source="", *, port=0, open_browser=True):
    desk = Desk(source)
    try:
        with create_server(desk, port) as server:
            url = f"http://127.0.0.1:{server.server_port}/#{desk.token}"
            print(f"ASES desk: {url}", flush=True)
            print("Temporary local session. Download the report to keep it. Ctrl+C to stop.", flush=True)
            if open_browser:
                webbrowser.open(url)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
    finally:
        desk.close()
    return 0
