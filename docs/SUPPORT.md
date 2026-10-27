# Verified environments and experimental scope

ASES runtime 1.13.1 declares Python 3.11 and later in `runtime/pyproject.toml`.
That declaration is broader than the environments verified below. Independent
label review and a user-utility study have not been completed.

## Current experimental 1.13.1 checkpoint — 27 October 2026

Wheel SHA-256:
`f65f62235b649748b36e63136e92d9a9429509a3db7aa72087db28b022812de1`.
All 95 distributed runtime files match the source. Windows/Python 3.14.7 source
suite: **775 passed, 1 skipped, 0 failures/errors** (776 tests, 98.68 s). The
symlink case needs account permissions.

The installed-wheel four-runner private CI matrix passed **776 tests per runner,
0 skipped, 0 failures/errors**: Ubuntu and macOS, Python 3.11 and 3.14. Verified
interpreter patch versions: 3.11.9, 3.11.17 and 3.14.8. Every runner audited all
95 installed files and isolated import origins. Tests use importlib mode; frozen
fixtures/reference resources remain separate. The final 1.13.1 matrix is recorded separately from the preliminary 1.13.0 run. The first local suite retained one real conditional-unknown
regression and one outdated profile assertion; both were corrected with the
original oracle preserved. Source review additionally found dropped conditional ancestry; 1.13.1 propagates it through descendants, with a two-level nested-route counterexample.

Known-cohort recovery: 90/90 and 239/244 summaries, with five remaining bodies
explicitly inspected without admitted facts. All selected return/error/possible-
call facts match the frozen source labels; the all-entry denominator is preserved.
Literal documents remain complete; PROMISE classification rises to 537/625 and
ReqView remains 110/110. The PROMISE count includes 48 errors and 40 abstentions,
with 85 improvements and one regression against 1.12. These are repaired known
cases, not independent validation. [Accuracy and limits](ACCURACY.md).

Private, conditional and empty-body coverage do not imply public accessibility,
execution, absence of effects or recovered stakeholder intent. General beta stays
NO GO; user studies are outside this tranche. GLiNER2 remains an optional advisory
provider with its previously measured 44/80 result; it was not rerun here.
The checkpoints below are historical.

## Historical 1.12 checkpoint — 27 October 2026

Runtime 1.12.0 wheel SHA-256:
`6e522a95e09c285308a4ff392b3e1b03ad9db0f2e80a14708b50cfdf3b4926d9`.
All 95 distributed runtime files match the current source. Windows/Python 3.14.7
source suite: **729 passed, 1 skipped**, 0 failures/errors (730 tests, 101.69 s).
The skipped symlink case requires account permissions.

The same wheel passed an installed-library four-runner matrix in the authorized
private CI repository: **730 passed, 0 skipped, 0 failures/errors per runner**.
Ubuntu/Python 3.11.17 and 3.14.8; macOS/Python 3.11.9 and 3.14.9. Isolated imports
and all 95 installed hashes were audited before tests. Tests use importlib mode;
frozen test fixtures and reference resources are retained separately. Source
suite and installed-wheel checks have different scopes. The first 1.12 matrix
passed without changing product code, labels or thresholds.

Known-case document regression recovers PROMISE 625/625 and ReqView 110/110 exact
texts, with 453/625 and 110/110 correct categories on all labelled rows. Source-line
bindings: 73/90 and 222/244 code entries. The separate possible-call supplement
recovers 19/19 and three negative controls within its closed scope. These results
remain bounded and do not establish general semantic correctness or independent
acceptance. [Accuracy and full denominators](ACCURACY.md).

GLiNER2 was actually run offline: 44/80 classifications correct on a balanced
convenience sample, 25.62 s with warm disk cache, 2.71 GiB peak process RAM.
The source-snapshot backend check produced three exact cited hypotheses without
modifying that snapshot. The model remains optional and advisory. Human studies
are outside this tranche. The checkpoints below are historical.

## Historical experimental 1.11 checkpoint — 26 October 2026

Wheel SHA-256: `29c8683b539da2083757a88a70872617f8f67587bef9e0dcfddb89d18215637f`.
All 95 runtime files match the checkout. The installed wheel passed the four-runner
matrix with document/test extras and Node 24.22.1; each runner reported **678 passed,
0 skipped, 0 failures or errors**. Environments: Ubuntu/Python 3.11.17 and 3.14.8;
macOS/Python 3.11.9 and 3.14.9. Import and content audits verified installed
site-packages rather than relying on the checkout. Tests use importlib mode;
mirrored source/resources remain available for explicit fixture assertions.

Windows/Python 3.14.7: **677 passed, 1 skipped**, 0 failures/errors, 79.34 s.
The skipped symlink test requires account permissions. The first restricted-environment
run and a rejected CI workflow configuration are retained separately; no runtime,
labels or thresholds were changed to bypass platform checks. The workflow fix moved
runner temporary paths into the test step.

Regression after repair uses unchanged external labels: PROMISE text recovery
613/625 and classification 389/625; ReqView 110/110 and 87/110 respectively.
Native ReqView preserves all 110 labelled SRS records plus 278 unlabelled ASVS
records; native ARFF retains 625 rows and raw type fields; published HTML retains
86/86 statements and IDs. These are known regression cases, not a new independent
holdout. See [accuracy](ACCURACY.md). At the 1.11 checkpoint optional GLiNER2 live inference was refused
by its memory guard; the later 1.12 live evaluation is reported above.

## Previous version 1.10 checkpoints — historical

| Evidence | Environment | Result | Limit |
|---|---|---|---|
| Current full source suite, 25 October 2026 | Windows, Python 3.14.7 | 632 passed, 1 skipped; 0 failures or errors (633 tests, 80.48 s) | Checkout source with installed editable ASES for isolated workers |
| Current full test run against installed library, 25 October 2026 | Windows, Python 3.11.16; dedicated private environment | 630 passed, 3 skipped; 0 failures or errors (633 tests, 77.29 s); import origin checked after collection and during setup | Tests/fixtures and some resource assertions read the checkout; not a self-contained portable test distribution. Two PDF cases skipped because optional pdfplumber is absent |
| Current retained wheel, 25 October 2026 | Windows, Python 3.11.16 | SHA-256 `7ed3931544e148431d39645613e7b0ab14839789fa1d77a1be953c298b89aa13`; all 91 distributed runtime files match source and installed files | Dependency versions were reused offline; the environment was reused across recorded setup attempts |
| Installed CLI and documents, 25 October 2026 | Dedicated Python 3.11.16 environment, isolated imports | Version, scan and inspect passed; 259 authored HTML UID records retained as kind unspecified and satisfaction unverified; document regeneration passed | Captured public-document inputs only; no target code or tests executed |
| Browser check, 25 October 2026 | Windows, in-app browser, source Desk Python 3.14.7 | Saved reopening, IT/EN counts, source status distinct from satisfaction, generic-UID reference navigation, new UI scan and overview total 259 passed; screenshots retained locally | Bounded author check against source matching the wheel; no independent user study or installed-wheel browser claim |
| External HTML recovery after repair | Two captured projects, four published HTML files | IDs 259/259, complete statements 257/257, declared directed links 419/419; original field labels 750/751, separately corrected title labels 751/751 | Known regression after the initial 0/259 result. One reference-reader title error was adjudicated separately. RF/RNF classification and independent human approval remain unmeasured |
| New external text-only classification, 25 October 2026 | PROMISE 625 rows; ReqView SRS 110 rows; original author labels hidden from ASES | Exact text recovered 94/625 and 76/110; correct classes among recovered texts 50/94 and 62/76 | No engine tuning on these results. Recovery and classification fail broad acceptance; supplied-label import is a different measurement. See [accuracy](ACCURACY.md) |
| Current installed-library Linux/WSL suites, 25 October 2026 | Ubuntu 26.04 under WSL2; Python 3.11.17 and 3.14.4 | Each full suite: 633 passed, 0 skipped, 0 failures or errors; 110.92 s and 56.96 s | Same 7ed393… wheel, all 91 runtime file hashes verified; task-owned environments with pdfplumber 0.11.10 and Node 24.22.1. Frozen checkout tests/fixtures and reference files; not native Linux or macOS |
| Previous document checkpoint, 24 October 2026 | Windows Python 3.14.7 and 3.11.16 | Source suite 623 passed/1 skipped; mixed checkout/worker suite 621 passed/3 skipped; wheel SHA-256 `841b5822f2f7acb6799c4afb2fbad64d44e2b6f1233db6821ba7b470355ca856` | Document profile 6, before explicit HTML UID recovery |
| Earlier WSL2 checks, 23 October 2026 | Ubuntu 26.04 under WSL2, Python 3.11.17 and 3.14.4 | Each source suite: 614 passed, 4 skipped; selected installed-wheel checks also passed | Earlier checkpoint and wheel; not native Linux runs or current profile 7 verification |
| Current remote Linux matrix, 25 October 2026 | GitHub runner Ubuntu 24.04 x64; Python 3.11.17 and 3.14.8 | Each full suite: 633 passed, 0 skipped, 0 failures or errors | Frozen installed 7ed393… wheel with documents/test extras and Node 24.22.1; all 91 runtime files matched. Tests/fixtures/reference files came from the separately frozen bundle |
| Current remote macOS matrix, 25 October 2026 | GitHub runner macOS 26 arm64; Python 3.11.9 and 3.14.8 | Each full suite: 633 passed, 0 skipped, 0 failures or errors | Same wheel and test bundle; `TMPDIR` points to the physical runner temporary directory. The first run retained two symlink-ancestor output-path refusals per macOS job |

Before optional dependencies were installed, each current Linux/WSL suite passed
627 tests and skipped six: two PDF tests and four Node-based renderer tests. All
six then passed on both interpreters, followed by the fresh complete runs above.
The downloaded Linux Node archive matched its official SHA-256. Dependencies were
installed only in dedicated test environments; no shared environment was changed.

The remote matrix used a separate private CI repository, not the main checkout or
any scanned project's sources. Its first Linux jobs passed; the two macOS jobs
each failed two tests whose temporary workspace used the `/var` symlink alias.
ASES intentionally refuses output paths with symlink ancestors. Setting only the
workflow's `TMPDIR` to the physical runner temporary directory resolved those
environment failures without changing the runtime, tests or labels. The initial
and final JUnit reports and logs were retained separately. The tested bundle and
wheel were identical across the four final jobs. The local workflow includes the
same temporary-directory setup, Node and optional PDF test dependencies.

The initial private-environment suite had six environment-related failures under
loopback/process restrictions. Host runs retained one stale Italian wording
expectation; after aligning that assertion with the updated explanation, the full
runs above passed. Initial failures, the assertion change and all original
assessment results are retained locally. No field oracle was changed during the
first external run; the later title correction is explicitly separate.

## Historical platform checks

The 21 October 2026 checkout suites recorded Windows/Python 3.14.7 at 484 passed
and 1 skipped, Windows/Python 3.11.16 at 482 passed and 3 skipped, and Ubuntu under
WSL/Python 3.14.4 and 3.11.17 at 483 passed and 2 skipped each. These results belong
to that earlier source revision. The WSL runs were not a native Linux distribution
matrix and do not verify the current checkout or current wheel.

The separate four-environment installed-package checks from that checkpoint are also
historical. They matched 84 packaged resource/source files, included 14 templates,
and checked document regeneration, legacy adoption and protection of manual edits.
The checkpoint wheel was `8e47af7bfdae089c7946712560b2b10ccb619b29ad1625cea3090c8c2191fbe9`;
it is not the current retained wheel. None of those package checks was a full suite
run exclusively from the installed package.

Earlier local-browser smoke checks used an owned fixture and covered scan results,
source evidence, generated-document links, saved context, downloads and reopening,
Italian/English, keyboard navigation and a narrow layout. The bounded 23 October
observations predate the saved-open progress fix and remain historical evidence. Earlier
24 October attempts were blocked by browser availability, URL identification or
loopback isolation and are retained as failed setup attempts. A later Chrome connector
check reached a host loopback Desk and observed the older workflows before the matrix-recovery change.
Switching the UI language left saved Italian Markdown unchanged, as documented.
After cancellation, Results reopened the last completed snapshot. This check does
not measure byte-level preservation or cancellation latency.

Scans do not run target code or tests. Source inventory, schema validity, regression
tests and accuracy on labelled claims answer different questions. None establishes
a universal correctness percentage. Read [flow coverage](FLOW-COVERAGE.md) and
[testing](../TESTING.md) for the measured scope and reproducible checks.

Complex joins, dynamic binding, transitive effects, original business intent and
runtime satisfaction remain partial or unassessed. The Java grammar improves local
body structure; declaration discovery and overload/receiver binding remain heuristic.
PDF support requires the `documents` extra; raster diagrams and arbitrary free-prose
semantics are not fully recovered. Missing evidence remains visible.

The desk is a single-user loopback service. Complete packages can contain extracted
text, source fragments, paths and reviews. Reduced export intentionally omits these
and cannot restore an analysis. See the [desk guide](DESK.md) and its
[Italian version](DESK.it.md) before retaining or sharing results.

Human comprehension and independent review of the wording remain pending. Current
Linux and macOS CI results verify the frozen wheel and listed test bundle; they do
not establish accuracy on arbitrary projects. In the earlier WSL checkpoint, the
initial setup omitted the package needed by isolated workers; that failed attempt
was retained separately from the successful historical checks.
