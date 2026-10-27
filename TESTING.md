# Testing ASES

These checks verify the scanner, its public outputs and the engineering-kit companion. To scan your own project, start with the [README](README.md); test dependencies are optional for normal scanner use.

## Current experimental 1.13.1 checkpoint — 27 October 2026

Windows/Python 3.14.7: **775 passed, 1 skipped, 0 failures/errors**, 776 tests in
98.68 s. Ubuntu/macOS with Python 3.11/3.14: **776 passed and zero skipped/errors
per runner**, installed-wheel hashes and isolated imports audited. All 95 runtime
files match wheel `f65f62235b649748b36e63136e92d9a9429509a3db7aa72087db28b022812de1`.

New checks cover private own-body scope, primary-entry budget priority,
conditional declaration identities and uncertainty, conditional rebinding,
position-bound empty-body coverage, document review after context changes,
quality-constraint forms and feature/metric counterexamples. Original frozen
external manifests/labels remain unchanged. Known-case accuracy: [ACCURACY](docs/ACCURACY.md).
Exact environments and first-run incidents: [SUPPORT](docs/SUPPORT.md).
The checkpoints below are historical.

## Historical 1.12 checkpoint — 27 October 2026

Runtime 1.12.0: Windows/Python 3.14.7 full source suite **729 passed, 1 skipped,
0 failures or errors**, 730 tests in 101.69 s. The skipped symlink case requires
account permissions. All 95 runtime file hashes match the retained wheel
`6e522a95e09c285308a4ff392b3e1b03ad9db0f2e80a14708b50cfdf3b4926d9`.
The current installed-package platform matrix is recorded in [SUPPORT.md](docs/SUPPORT.md).

External known-case regression now recovers 625/625 PROMISE and 110/110 ReqView
sentences, with 453/625 and 110/110 correct categories on all labelled rows.
The separate frozen possible-call supplement scores 19/19 and three negative
controls with unique source-line binding; name/path-only binding remains ambiguous.
The real optional GLiNER2 comparison scores 44/80 on a balanced convenience sample.
Neither regression nor schema validity establishes general semantic correctness.
See [accuracy and denominators](docs/ACCURACY.md). The checkpoints below are historical.

## Install and run

From the repository root, in an active virtual environment:

~~~sh
python -m pip install -e "./runtime[test]"
python -I -c "import ases; print(ases.__file__)"
python -m pytest -q runtime/tests
~~~

Use the same active environment for installation and tests. Desk tests start an isolated Python child with `-I`, which ignores `PYTHONPATH`. The import check above must pass before running them; pointing `PYTHONPATH` at the source alone does not install ASES for that child.

The historical 25 October 2026 profile-7 checkpoint ran all 633 tests on Windows. Python 3.14.7 used checkout source: **632 passed, 1 skipped, 0 failures or errors** (80.48 seconds). Python 3.11.16 imported the installed ASES library from a dedicated private environment: **630 passed, 3 skipped, 0 failures or errors** (77.29 seconds). The latter checked import origin after collection and during setup; isolated workers used that environment. Tests/fixtures and some direct resource assertions still came from the checkout. Two optional PDF cases were skipped in that environment. This is not a self-contained portable test distribution or independent correctness study.

At that checkpoint installed-library suites also ran under Ubuntu 26.04/WSL2 on Python 3.11.17
and Python 3.14.4: **633 passed, 0 skipped, 0 failures or errors in each run**
(110.92 and 56.96 seconds). All 91 wheel runtime files and isolated worker imports
were checked. These runs use frozen checkout tests, fixture data and reference
schemas/templates. They verify Linux under WSL2, not native Linux or macOS.
The initial 627-pass/6-skip runs remain separate; installing the optional document
reader and a task-local Node runtime enabled the missing six tests, which passed
before the final complete runs. For this fuller test environment, install
`./runtime[documents,test]` and make Node available on `PATH`; Node is needed by
the renderer tests, not by normal Python scanner use.

A separate private remote matrix then verified the same frozen wheel on Ubuntu
24.04 x64 (Python 3.11.17 and 3.14.8) and macOS 26 arm64 (Python 3.11.9 and 3.14.8).
All four full suites recorded **633 passed, 0 skipped, 0 failures or errors**.
Each job verified all 91 installed runtime file hashes and isolated worker imports.
The first macOS run failed two tests per interpreter because the temporary
workspace used a symlink ancestor. Setting `TMPDIR` to the physical runner temporary
directory fixed the environment without changing product code or tests; the first
reports are preserved. The local CI workflow uses that setup and installs the
documents extra and Node for the complete suite.

The retained wheel SHA-256 is `7ed3931544e148431d39645613e7b0ab14839789fa1d77a1be953c298b89aa13`. All 91 distributed runtime files match source and installed files. Compared with the preceding `841b…` wheel, changes are limited to the HTML reader, document model/views and Desk presentation. Isolated CLI scan/inspect and document regeneration also passed. The current in-app-browser author check covered a new document scan, IT/EN unknown-kind totals, source status, reference navigation and the generated overview. It used source matching the wheel; it was not an installed-wheel browser matrix or human study.

The initial environment-restricted package run retained six failures. Later host runs retained one wording assertion that expected the old Italian explanation; aligning that phrase preserved the same absence-interpretation check. The final complete runs above passed all non-skipped tests. Select a writable pytest base directory with `--basetemp` if necessary. See [verified environments](docs/SUPPORT.md) for exact scope and historical results.

The 24 October profile-6 checkpoint is historical: Windows/Python 3.14.7 recorded 623 passed and 1 skipped; Python 3.11.16 recorded 621 passed and 3 skipped with checkout imports in the pytest process and installed imports in isolated workers. Its wheel was `841b5822f2f7acb6799c4afb2fbad64d44e2b6f1233db6821ba7b470355ca856`. The earlier saved-open progress wheel `15a28…` and its 617/3 source suite are also historical. They are distinct from the current Linux/macOS matrix above.

The 23 October 2026 WSL2 checks on Ubuntu 26.04 recorded **614 passed, 4 skipped** with Python 3.11.17 and separately Python 3.14.4. They belong to the prior checkpoint before the saved-open progress fix: their source suites used checkout source, while isolated Desk workers used the previous wheel, SHA-256 `63cda93afaca9f6a02146c49b73bf1e7889ca3e6b5880f18ddae37bf3632d692`. CLI, synthetic scan and inspection, and seven selected document/review/source-protection tests passed from that installed package in each environment. These were not full installed-wheel suites or native Linux runs. Existing local dependencies were reused; skipped checks were not counted as passes.

Earlier results from 21 October 2026 are historical: Windows/Python 3.14.7 recorded **484 passed, 1 skipped**; Windows/Python 3.11.16 recorded **482 passed, 3 skipped**; Ubuntu under WSL/Python 3.14.4 and 3.11.17 each recorded **483 passed, 2 skipped**. These runs used the checkout source; their separate installed-package checks belong to the previous checkpoint wheel, SHA-256 `8e47af7bfdae089c7946712560b2b10ccb619b29ad1625cea3090c8c2191fbe9`. They do not verify the current checkout or current retained wheel.

## What the suite covers

Suite success and accuracy on new projects answer different questions. The initial
label-blind external document tests retained only 94/625 PROMISE sentences and
76/110 ReqView sentences exactly, with 50/94 and 62/76 correct categories among
the recovered texts. The [accuracy guide](docs/ACCURACY.md) reports the full
denominators, original-format limits, controlled supplied-label imports and source
label contradictions. These are frozen first measurements, not the synthetic
regression percentages below.

| Area | Checks |
|---|---|
| Source handling | Owned/test/generated roles, exclusions, source limits, malformed syntax and inert parsing |
| JavaScript / TypeScript | Eight source suffixes, lexical imports/aliases, shadowing, mutations, re-exports, CommonJS, HTTP and service-client authority |
| Python / Java | Supported Flask/Blueprint and factory declarations, conservative unknowns, JUnit annotation/visibility variants and comment/string negatives |
| Pattern qualification | Positive cases, close negatives, existing EventEmitter counterevidence, test-source isolation and weak signals kept as hints |
| Saved outputs | Schema/reference validation, canonical identities, formatting stability, snapshot queries, pagination, trace bounds and uncertain diffs |
| Engineering documents | Explicit requirements and fields; page/cell provenance; continued tables; malformed/encrypted inputs; formula/cache separation; imported results; API contracts; bounded code-to-sentence interpretation; review conflicts and manual-edit protection |
| Other input modes | Bounded supplied artifacts, source-map/runtime reconciliation and passive HTML observation |
| Output safety | Marked output only, engineering-kit protection, refused user material/links and temporary cleanup |
| Local desk | Real subprocess scans, cancellation, retained last result, HTTP capability/origin/host checks, source freshness, recoverable size limits and bounded document delivery |

The fixtures are test inputs, not sample production applications. Keep tests, fixture data, schemas and evaluation tools in the repository: they make the checks reproducible.

The 35 cases in `test_product_documents.py` check controlled explanations, predicate provenance, explicit operation grouping, separate user requirements, legacy reviews and changed-source conflicts. Desk tests also exercise authoring, ZIP export and reopening. Passing these tests does not establish that recovered paths are correct for every language.

The controlled flow and corpus figures in this guide are saved measurements for named profiles, not results from the 23 October source suite or current wheel check. The frozen `runtime/tests/fixture_documents/product-corpus.json` contains 24 synthetic entries and 120 expected local-flow claims. The historical flow profile 5 result is **8/8 Python, 8/8 JavaScript and 8/8 Java cases**, with zero FP/FN in the selected scope: 72 outcomes, 24 explicit errors and 24 possible effects. The preserved R0–R2 baseline passed 16/24 cases; its eight Java cases failed with outcome TP 48 / FP 23 / FN 24 and error/effect counts each TP 16 / FP 9 / FN 8. Labels were not changed to obtain the improvement. The 30 Java-flow tests cover supported paths and close negatives, including explicit partial recovery for unsupported constructs. Read [flow coverage](docs/FLOW-COVERAGE.md) before interpreting these results. Labels were prepared in the same development session; independent review and human comprehension measurements are pending. Do not combine this result with the separate 16-case scanner benchmark below or present the unit-test pass count as semantic accuracy.

## Desk acceptance checks

The local HTTP/file boundary uses a single-user design; it is not a hosted multi-user service. The [desk guide](docs/DESK.md) states its contracts and limits. These tests connect the user workflows to their implementation boundaries:

| Behavior | Regression evidence |
|---|---|
| Scan, generated documents, ZIP and untouched input | `test_scan_brief_trace_source_and_temporary_cleanup` in [test_ui.py](runtime/tests/test_ui.py) |
| Stop a real worker and preserve completed work after failure | `test_cancellation_stops_isolated_worker_and_preserves_result`, `test_failure_preserves_the_last_completed_result` |
| Recover from an excessive scope without editing the project | `test_scope_limit_can_be_fixed_without_changing_the_project` |
| Reject foreign browser origins, wrong hosts, missing tokens and stale snapshot requests | `test_loopback_http_boundary_and_real_scan` |
| Refuse changed/unreferenced source and changed cleanup targets | `test_source_is_bound_to_observed_file_and_fresh_bytes`, `test_cleanup_requires_current_preview_and_rejects_changed_output` |
| Survive transient Windows progress replacement contention | `test_progress_retries_windows_reader_contention` |
| Never import an analyzed project's counterfeit ASES package from the working directory | `test_worker_does_not_import_project_modules_from_its_working_directory` |
| Preserve complete totals when shortening display lists | `test_previews_bound_delivery_without_changing_totals` |
| Recognize arbitrary environment names, refresh inventories and retain uncertainty after scope changes | [test_source_scope.py](runtime/tests/test_source_scope.py) |

For a browser smoke check, scan `runtime/tests/fixture_spring` from the full checkout. Read the summary, open a route in Code map, inspect its source and forward/backward links, read a generated document and download the ZIP. Switch language, resize the page, try a missing path and confirm the previous result stays accessible. Use only disposable generated fixtures when checking cleanup. Native folder-picker availability depends on the Python/desktop environment; the path field remains the fallback. Earlier 24 October attempts were blocked before a page opened; those records remain preserved. A later Chrome connector check on Windows/Python 3.14.7 reached the source Desk through a host loopback server. It verified a single saved-opening phase in IT/EN, elapsed time and stop control, source preview and return, separate coverage totals, ODD navigation, a legacy Python snapshot and cancellation followed by reopening the retained result from Results. Screenshots and visible-state records were retained locally. The 91 distributed runtime files matched the current wheel. This is a bounded author browser check, not an independent user study or a new full suite on Python 3.14.7. The 23 October browser observations remain historical evidence. Automated source checks recorded two red English/Italian open-progress regressions before the fix and six focused passes afterward; JavaScript progress assertions use the checkout copy, byte-identical to the wheel member. A separate installed-worker workflow passed using the current wheel under Python `-I`. The automated checks alone do not establish rendered behavior. The later browser check verifies the observed workflows; saved documents retain their original language, and independent human acceptance remains pending.

## Measure recovered facts against explicit expectations

From runtime/:

~~~sh
python tools/evaluate_accuracy.py --out ../accuracy-results.ases
python tools/evaluate_quality.py
python tools/evaluate_structure.py
~~~

The accuracy evaluator writes report.html, REPORT.md and results.json. Each case includes source, expected facts and rationale. The bundled corpus has **16 synthetic cases and 39 explicit labels**; its recorded result is **16/16 cases passing**, zero false positives/negatives and 16/16 position-change checks passing. Independent label review is pending. This is a regression measurement on selected cases, not a whole-project accuracy percentage.

Read [the evaluation guide](docs/ACCURACY.md) for precision, recall, F1, unassessed predictions and scope. The older quality/structure evaluators have separate, smaller oracles; their numbers should not be combined into one score. The structure tool accepts --project /path/to/repository for runtime, allocation and coverage measurements, which do not establish correctness without labels. Python allocation measurements exclude native parser memory.

Exit codes for evaluate_accuracy.py: 0 means all declared criteria pass; 1 means evaluation completed with discrepancies; 2 means invalid input or an intercepted operational error. Inspect discrepancies instead of changing labels merely to obtain a pass. Runtime tests and accuracy checks answer different questions; both should be reviewed.

## Evaluate document recovery separately

Install `python -m pip install -e "./runtime[test,documents]"` to include textual PDF tests. The synthetic encrypted PDF is an empty, locally generated fixture, not a project document.

```sh
ases documents-evaluate runtime/tests/fixture_documents/corpus.json --out document-evaluation
```

The document corpus contains **6 synthetic cases**: its recorded result is **4/4 labelled requirement IDs** (TP 4, FP 0, FN 0), **12/12 selected fields**, **2/2 links** and **2/2 quality checks**. One case interprets code without any labelled requirements. Read `document-accuracy.html`, `DOCUMENT-ACCURACY.md` and JSON: ID recovery does not measure sentence comprehension. Labels were reviewed in the same session; independent review is pending.

[test_behavior_interpretation.py](runtime/tests/test_behavior_interpretation.py) checks Python, JS/TS and bounded Java behavior, including branch conditions, errors, helper-return isolation, arrow expressions and string/comment negatives. Proposed characterization tests are not independent acceptance oracles. [test_engineering.py](runtime/tests/test_engineering.py) covers readers, declared API fields/contracts, historical results, duplicate sources, references, review conflicts, regeneration without sources and protection of manually edited outputs.

The additional `fixture_documents/behavior-corpus.json` contains 11 owned adversarial
local-flow cases, with oracles frozen before baseline evaluation. Run it through the
same `ases documents-evaluate` command. The recorded result is **15/15 outcome claims**,
**1/1 escaping-error claim** and **1/1 possible-effect claim**, with zero extra or missing
claims in this slice. The baseline exposed 6 extra/7 missing outcomes, 2 extra errors
and 4 extra/1 missing effects; keep both results when comparing versions. One positive
error and one positive effect are small denominators, not broad capability estimates.

[test_behavior_evaluation.py](runtime/tests/test_behavior_evaluation.py) injects reversed
conditions, false effects and omissions to verify that the scorer goes red; rejects
malformed/duplicated oracles before replacing output; checks caught errors, finally
cleanup, response-binding negatives and evidence stability between process hash seeds.
It also excludes dead helper edges while preserving reachable JS import aliases.
Transitive claims are displayed separately and are outside this local-body oracle.
Independent human label review remains pending.

For browser acceptance, scan an owned code fixture, open **Documents**, read a reconstructed sentence, follow its interface and source links, save a note, reload and rescan. Check retained notes and changed-source conflicts, static diagrams, English/Italian views and a narrow screen. Download the ZIP and inspect `engineering-model.json` and `engineering-review.json`. Automated desk tests separately exercise cancellation, failure recovery, HTTP boundaries and reopening saved reviews. This does not replace user testing with assistive technology.

Distribution verification builds a normal wheel, installs it with the document extra into a fresh environment outside the checkout, then scans and regenerates documents there with isolated Python. Check all 14 templates, section/schema resources, source-independent regeneration and installed module origin. Course slides, external study documents and local evaluation outputs do not belong in the wheel or repository.

Real-document and public-library results must name the exact source revision, labelled fields, TP/FP/FN and unread formats. Keep these local when their inputs or paths are private. A zero requirement denominator is unmeasured; never report it as perfect recall. See the [document guide](docs/DOCUMENTS.md) for extraction and interpretation limits.

The explicit HTML tests cover typed UID/statement rows, unknown kinds, missing
statements, author status/title, native references, nested blocks and inert code
within a statement. Close negatives cover navigation, examples, ambiguous fields
and script/style text. View tests keep unknown-kind records visible in both
languages; model tests separate exact local references from unresolved external
ones. Legacy structured-input defaults remain covered separately.

A local external-document comparison initially recovered 0/259 selected IDs.
After the bounded repair, those now-known inputs recover 259/259 IDs, 257/257
complete statements and 419/419 directed author references. Original field labels
score 750/751; a separately disclosed correction to one reference-reader title
scores 751/751 against the same predictions. Original sources, labels, failures
and the correction remain distinct. These figures are known regression results;
RF/RNF classification absent from the sources and independent human review are
not measured. They do not establish universal document comprehension.

## Check a real repository

~~~sh
ases scan /path/to/repository --out before.ases
ases inspect before.ases
# Review the source or make and test a deliberate change.
ases scan /path/to/repository --out after.ases --baseline before.ases
~~~

Open docs/SUMMARY.md and docs/QUALITY.md in each output. Review source evidence for both selected positive facts and close negatives; schema PASS alone does not measure recovery completeness. Keep before.ases and after.ases separate. Coverage/profile differences and unknowns must remain visible when interpreting a removed item.

For ASES's own source, run the optional self-check from the repository root:

~~~sh
ases selfcheck . --clean
~~~

Self-checking can reveal regressions but can share the scanner's blind spots; it does not replace explicit oracles or external-source review.

## Keep generated results separate

Keep reports when you need a baseline; use a temporary directory for disposable trials. Never commit scan outputs, caches, private source paths, credentials or local working notes. Persistent reports remain until explicitly cleaned:

~~~sh
ases clean before.ases
ases clean after.ases
ases clean accuracy-results.ases
~~~

Cleanup requires the ASES output marker. Never point test/evaluation output at a source directory or an engineering kit.

## Before a release

Run the relevant tests and the complete suite, inspect the accuracy report, verify public schemas and review links/commands in the affected guides. Preserve unresolved failures and unsupported scope in the release notes. A passed static test-link check does not mean the target project's tests were executed; a recovered control does not demonstrate effectiveness.

The worksheet regression suite checks Italian/English headers, sparse cells,
per-sheet state, duplicate columns and formula-cache boundaries. Matrix cases also
check explicit requirement headers, literal X/test-column associations, direct
internal references and unresolved parent test IDs. Computed/external/chained
references and formula-generated X markers are close negatives. Multiple marked
tests on one row must have distinct link IDs. The local object
shape suite checks initializer evidence, same-line bindings, partial keys and
close negatives for mutation, escape, shadowing and dynamic evaluation. These
fixtures test admitted behavior and deliberate abstention; they are not an
independent real-project accuracy study.

`test_claim_line_endings.py` checks physical CR/CRLF versus LF in both ordinary and
tagged JavaScript templates, while preserving explicit escapes and significant
spaces. Claim reports record the expression-comparison profile separately from
the flow and predicate methods. Selected callables with no reconstructed behavior
must remain visible as coverage misses; do not count their empty claim sets as
verified negatives.

`test_overload_body_mapping.py` checks that TypeScript overload signatures cannot
claim or suppress the unique implementation body, and that an unrelated interface
with the same method name remains unmapped. Java bare-call candidates retain guard
conditions and exclude unreachable calls; the profile is not expanded to bare
Python/JavaScript calls. No target code is executed by these checks.

Italian explanations are covered by `test_italian_prose.py` (22 cases): source-language parsing, comparisons and negations, literal result fields, duplicate/spread guards, explicit abstention, saved fact references and generated reading guides. They test bounded fidelity, not general human comprehension.

An earlier wording-only refinement was followed by 142 relevant explanation/document tests and a recheck of the then-delivered wheel. Those are historical checks. They do not replace the current source-suite result above or certify the current retained wheel.
