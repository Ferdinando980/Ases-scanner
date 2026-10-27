# The local ASES desk

English · [Italiano](DESK.it.md)

## Start here

From the full checkout, using Python 3.11 or later:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "./runtime[documents]"
.\.venv\Scripts\ases.exe ui
```

On macOS/Linux use `python3 -m venv .venv`, `.venv/bin/python -m pip install -e "./runtime[documents]"`, then `.venv/bin/ases ui`. With an activated environment, `ases ui` is enough. Git is required for repository URLs. The `documents` extra enables PDF reading. Without it, other readers work and PDFs report an unsupported capability. Templates and the section specification also ship in the installable package.

The browser opens automatically. Otherwise use `ases ui --no-browser` and open the printed session link. Keep that link to reopen the local session. `ases ui /path/to/project` prefills the field without starting an analysis. `--port` selects a particular port; the address always stays local.

## Analyze, then read

In **New analysis**, choose a folder or paste its path. If the Python installation lacks a working system folder picker, the path field remains available. You can also supply a public HTTPS Git URL without credentials; its checkout is temporary. ASES neither installs target dependencies nor executes project code.

**Options** holds a previous `.ases` baseline and additional exclusion patterns, one per line. For example, `experiments/**` excludes experiments for this scan without changing `.asesignore` or the project. Recognized Python environments with `pyvenv.cfg` or `conda-meta/history`, package directories and recognized generated outputs stay outside scope. ASES does not automatically adopt every `.gitignore` rule.

The running view shows the actual stage and elapsed time. **Stop analysis** terminates the isolated worker and removes its attempt files. The desk stays available. There is no pretend percentage to keep the progress bar entertained.

**Results** explains recovered structure, review suggestions and where to go next. Follow routes or open **Code map**, select a symbol and inspect its source evidence. **What it reaches** and **What calls it** navigate static links; these do not prove execution. **Coverage** separates partial methods, unknowns and excluded folders. No suggestions does not mean no problems, and consistency validation does not certify application correctness. Run the project tests separately. A changed source file is refused as evidence for an older snapshot: scan again instead.

## Documents and saving

**Documents** offers **The project at a glance** (`OVERVIEW.md`) first, alongside the readable English or Italian report (`REPORT.md` / `REPORT.it.md`). RAD, SDD, ODD, test documents, recovered instructions and reading quality follow. In **From requirements to evidence**, choose documented requirements, sentences reconstructed from code, interfaces, tests, diagrams or sources. Each record shows its text and origin; open it for conditions, references and page, cell or line locations. An ID should not be a guessing game.

The interface language localizes the reader navigation and explanations; saved Markdown documents keep their original language. To regenerate them in English from the snapshot without rescanning, see the `ases documents ... --language en` command in the [document guide](DOCUMENTS.md).

The RAD retains requirements declared in available specifications, including readable actors, priorities and thresholds. Without specifications, ASES interprets supported code paths and proposes separate sentences about inputs, conditions, returns, errors and calls with possible effects. Function names do not establish business goals or original intent. The ODD contains packages, signatures, declared types, comments, contracts and static diagrams, without demanding a design pattern to fill the page. See [the document guide](DOCUMENTS.md) for formats and limits.

Annotate, confirm or flag a record with **Save and regenerate documents**. Reviews remain separate from source, enter the ZIP and are saved in the browser for the same project. Reloading or scanning again recovers them; a changed record retains the review as a visible conflict. Browser storage depends on origin and port: download the report for durable storage. Long previews are shortened; the complete download retains complete files. Source HTML is never executed.

**Download complete package** produces a ZIP containing `START-HERE.md`, documents and JSON/YAML snapshots. It does not copy the whole repository, but its document model retains extracted text, cells, API comments and code fragments as well as project names, paths, evidence and metadata. Inspect the content before sharing it. Extract the ZIP into a folder before using **Open saved analysis**. Attach the source folder to preview evidence. The desk explorer requires v2 snapshots; historical snapshots remain readable with their CLI tools and documents, with no implicit conversion or rescan.

The desk adds no `.ases` folder to the project. It keeps one completed analysis and one active attempt. A failed or stopped attempt preserves the previous result, labeled as the last completed analysis. A successful new analysis replaces it. **Clear session** removes the temporary result. Ctrl+C in the terminal stops the service and cleans the session; closing the tab alone does not. A forced operating-system shutdown may leave files in the system temporary directory.

## Other tools

| Tool | What it returns |
|---|---|
| Compare | Finding and semantic differences between two extracted `.ases` directories, with uncertainty retained |
| Public website | Sample of 1–10 pages, forms and scripts; no backend access or JavaScript execution |
| Artifact | Static inventory of a local artifact and its source maps |
| Reconcile | Correspondences between source snapshot, artifact and optional imported runtime observations |
| Audit | Drift against the baseline stored in the project folder, including an absent-baseline result |
| Export | JSON using consumer contract 1.5 or 2.0 |
| ASES capabilities | Static capability recognition; does not execute the test suite |
| Accuracy | Evaluation on the included corpus (`bundled`) or a supplied labeled JSON corpus; not universal accuracy |
| Cleanup | Preview and explicit confirmation for recognized ASES output removal; rejects kits, projects and linked entries |

Operation previews may shorten long lists. Their counts use complete results; downloads retain original data. **Method & templates** is separate: choose a SOW, RAD, SDD, ODD or test document, edit and download it. Drafts are stored in the browser for this project and origin; download Markdown copies to keep them elsewhere. Approved requirements and documentation recovered from code have different authority. The kit guides engineering work; a button cannot supply missing design decisions.

## Practical limits and local-service contract

The desk allows 5,000 source files, 128 MiB total source and 2 MiB per source file. Its snapshot reader permits 256 MiB. An operation is limited to five minutes; remote cloning to two minutes. Narrow the source scope or use the CLI for larger intentional scans. These bounds do not guarantee constant memory use for every input.

Code lists deliver 40 rows per page; document lists deliver 20. Trace expansion is bounded to 64 nodes; read its coverage state and use the CLI for different limits. Source context previews permit files up to 1 MiB. Document previews stop at 120,000 characters or 1,500 lines. Delivery bounds do not redefine scanner coverage.

This is a single-user local tool. Do not expose it through a proxy or tunnel. It binds only to `127.0.0.1`, validates host and origin and requires a per-session capability for APIs. Project text is rendered as data. Source previews require an evidence reference, a path inside the selected root and bytes matching the saved hash. Scans execute in a separate process so cancellation or worker failure does not end the web service. Completed results swap only after a successful attempt. Windows progress-file replacement tolerates transient reader contention; progress refresh failure does not fail the analysis.

The UI uses no external generation service, telemetry, remote fonts or CDN. See [TESTING.md](../TESTING.md) for boundary, recovery and regression checks.

## Choose what to download

**What would you like to keep?** defaults to **Complete package**, preserving the
work for reopening after extracting the ZIP. The **Reduced report** contains aggregate
counts and explicit omissions only, without source text, paths or notes. It is not a
reopenable snapshot; counts can still reveal project characteristics.
`EXPORT-CONTENTS.json` describes either package. Nothing is automatically uploaded.

Complete export accepts up to 512 MiB of uncompressed input and a 128 MiB compressed
ZIP. Files are streamed into a buffer that stops writes at the compressed limit;
an export failure preserves the completed analysis. Exceeding the
limit retains the analysis: choose reduced export or narrow a new scan. Browser
storage should not be the only copy of reviews.

Main controls are keyboard-operable with visible focus. Filters retain focus after
updating lists. Document links open the target record or explain that it is outside
the shortened preview. Narrow-screen checks are layout evidence, not accessibility
certification. See the [verification matrix](SUPPORT.md) for tested environments
and remaining limits.
