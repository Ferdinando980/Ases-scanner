# ASES Changelog

## 1.9.0
- Added inert Tree-sitter extraction for all eight JS/TS suffixes, with lexical bindings, CommonJS, re-exports, callbacks, supported routes and safer root-directory module resolution.
- Extended Python recovery to factory-local functions and handlers, literal Flask/Blueprint methods/prefixes and local mounts; dynamic and conditional forms retain explicit unknowns.
- Added package-private and qualified JUnit test annotations while excluding comment/string lookalikes and helper methods.
- Separated imported-library calls from admitted API-client candidates; preserved Node HTTP(S) requests and added classification profile module-call/2.
- Qualified Observer opportunities with per-call EventEmitter counterevidence and comment/string negatives, without suppressing unrelated direct notifications.
- Added consumer context 2.0 with canonical identities, observations, structural relations, mappings and independent coverage for six relationship families. Legacy context 1.5 and scanner feed 1.3 remain available.
- Added saved-snapshot queries, bounded forward/backward traces and scoped semantic/finding diffs with explicit uncertainty for unsupported absence and profile changes.
- Added bounded supplied-artifact inspection and source/runtime reconciliation without target execution, builds, runtime collection or remote source-map fetching.
- Protected engineering kits and user material from output replacement/cleanup, separated generated output from source inventory and kept test sources out of production findings.
- Expanded frontend-template scope and source provenance, corrected CRLF control attribution and kept request-site identities independent of source lines.
- Added an inspectable accuracy corpus and offline HTML/Markdown/JSON reporting with precision, recall, F1, false positives/negatives and declared limits.
- Documented scanner setup, output interpretation and engineering-kit adoption.

## 1.8.0
- Added bounded `ases scan-site` observation of public HTML pages with robots rules, same-origin crawl limits, forms, script references, and qualified framework hints.
- Kept published-site evidence in the existing consumer/scanner contracts while marking source-level dimensions `NOT_OBSERVED`.
- Corrected Angular source classification, component/template/service and route-declaration detection, and false Express routes from frontend tests.
- Downgraded Proxy suggestions around native `HttpClient` to hints.

## 1.7.2
- Added `ases --version`: the CLI had no version flag at all, so any consumer trying to detect
  the installed version got nothing.
- Fixed `runtime/pyproject.toml`'s own version, which had not followed the 1.7.1 bump.
- 37 tests pass.

## 1.7.1
- Regenerable docs (SYSTEM-OVERVIEW.md, RAD.md, SDD.md, ODD.md, TESTING.md) now carry an
  `<!-- ases:doc fingerprint=... ases_version=... -->` signature so an external consumer
  can tell whether a doc still matches the current project state, without guessing from a
  file's mtime. Data files (TRACEABILITY.yaml, CONTROLS.yaml, QUALITY.md) stay unsigned.
- 37 tests pass.

## 1.7.0
- Added source-role classification before analysis: OWNED_SOURCE, TEST, GENERATED, VENDORED, TOOLING, DOCUMENTATION, BUILD_ARTIFACT.
- Generated JaCoCo/Javadoc output, minified/vendor libraries and wrapper/tooling code no longer drive findings.
- Tightened Factory to branch-local alternative-product selection and Facade to repeated active subsystem calls.
- Added DAO/ServiceImpl architecture recovery and observed external Adapter detection.
- Added frontend component/template/API-service/store recovery and frontend conformance.
- Added conservative frontend↔backend route-contract correlation.
- Scanner contract 1.3 adds surface, actionability, entity, source_role and source classification for downstream consumers.
- Consumer contract 1.3 adds source classification, frontend inventory/findings and cross-boundary findings.
- 34 tests pass.

## 1.6.0
- Added unified claim states: OBSERVED, INFERRED, OPPORTUNITY, HINT, UNKNOWN, CONTRADICTED, and SUPPRESSED.
- Added stable semantic fingerprints for scanner findings.
- Added counter-evidence, assumptions, evidence-strength metadata, and explicit analysis coverage.
- Added architecture conformance/erosion findings derived only from already-observed architecture.
- Added conceptual pattern levels: ARCHITECTURE, APPLICATION_PATTERN, GOF, and FRAMEWORK_IDIOM.
- Added `.asesignore` rule suppression while preserving suppressed findings in scanner output.
- Added `ases diff` and `ases scan --baseline` with NEW/RESOLVED/CHANGED/UNCHANGED semantics.
- Upgraded scanner contract to 1.2 and consumer contract to 1.2.
- Expanded regression suite for fingerprints, suppression, diffing, and architecture conformance.

## 1.5.0
- Rebuilt pattern analysis around explicit evidence rules and `OBSERVED / OPPORTUNITY / HINT` states.
- Added architectural observations for Layered Architecture, MVC, Repository, and Service Layer.
- Added precision-first rules for Factory, State, Strategy, Command, Observer, Chain of Responsibility, Template Method, Adapter, Facade, Decorator, and Proxy.
- Excluded test code from pattern opportunities.
- Filtered Factory noise from exceptions, DTO/request/response/value types and common stdlib/framework wrappers.
- Replaced receiver-count Facade detection with project-level dependency overlap.
- Split weak hints from actionable scanner findings for downstream consumers.
- Added rule IDs, positive/negative signals, scope, evidence, confidence, and guardrails to pattern findings.
- Updated scanner/consumer contracts to v1.1.
- Fixed Java field scanning for one-character type names.

## 1.4.1
- Scan outputs are refreshed in place instead of accumulating stale generated files.
- Added `ases clean <path>` and `ases clean --all` for safe removal of generated ASES output directories.
- Added `.ases-output` marker to custom output directories so cleanup never targets arbitrary folders.
- Fixed package `__version__` consistency.

# Changelog

## 1.3.0 — Self-Hosted Benchmark Release
- Developed through ASES requirements/impact/simplicity/pattern/test flow.
- Separated raw fact graph from semantic traceability.
- Fixed test-to-self traceability.
- Fixed route `//` normalization.
- Added discovery of PDF/DOCX/XLSX/diagram documentation.
- Excluded test classes from production component model.
- Added conservative DTO/factory/state/application/domain classification.
- Added control enforcement layers.
- Added session-operation recovery and conservative actor refinement.
- Added persistence logical boundary.
- Added State-specific and Simple Factory/Factory-idiom candidates.
- Added semantic quality metrics and quality report.
- Added real-benchmark-derived regression fixture.

## 1.2.0
- Added direct Git URL scanning.
