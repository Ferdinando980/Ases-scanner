# Testing ASES

These checks verify the scanner, its public outputs and the engineering-kit companion. To scan your own project, start with the [README](README.md); test dependencies are optional for normal scanner use.

## Install and run

From the repository root, in an active virtual environment:

~~~sh
python -m pip install -e "./runtime[test]"
python -m pytest -q runtime/tests
~~~

The last full verification on 15 October 2026 recorded **241 passed, 1 skipped** on Windows/Python 3.14.7. The skipped case requires symbolic-link permissions. This records the tested environment, not certification of every supported Python/operating-system combination. Some integration tests start loopback HTTP servers. If the system temporary directory is unavailable, select a new writable pytest base directory with --basetemp.

## What the suite covers

| Area | Checks |
|---|---|
| Source handling | Owned/test/generated roles, exclusions, source limits, malformed syntax and inert parsing |
| JavaScript / TypeScript | Eight source suffixes, lexical imports/aliases, shadowing, mutations, re-exports, CommonJS, HTTP and service-client authority |
| Python / Java | Supported Flask/Blueprint and factory declarations, conservative unknowns, JUnit annotation/visibility variants and comment/string negatives |
| Pattern qualification | Positive cases, close negatives, existing EventEmitter counterevidence, test-source isolation and weak signals kept as hints |
| Saved outputs | Schema/reference validation, canonical identities, formatting stability, snapshot queries, pagination, trace bounds and uncertain diffs |
| Other input modes | Bounded supplied artifacts, source-map/runtime reconciliation and passive HTML observation |
| Output safety | Marked output only, engineering-kit protection, refused user material/links and temporary cleanup |

The fixtures are test inputs, not sample production applications. Keep tests, fixture data, schemas and evaluation tools in the repository: they make the checks reproducible.

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
