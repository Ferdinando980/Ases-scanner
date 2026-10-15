# ASES Runtime v1.9

```bash
python -m pip install -e .
ases scan <local-path-or-git-url>
ases scan-site https://example.org --max-pages 5
ases scan <project> --out current.ases --baseline previous.ases
ases semantic-diff previous.ases current.ases
```

`scan-site` fetches only public HTML pages from the same origin, obeys `robots.txt`, and never submits forms or executes JavaScript. It records sampled pages, form actions, script references, and cautious framework hints in `site-observations.json` and the existing semantic/consumer/scanner reports. For a trusted local test server, pass `--allow-local`. Source architecture, client-rendered routes, and frontend/backend contracts remain `NOT_OBSERVED` in this mode. Use `ases scan` on the repository to recover those.

Repeated scans refresh recognized generated output. An installed engineering kit in `.ases` is preserved: default source output then becomes `ases-scan.ases`. Explicit nonempty unrecognized destinations are refused. Cleanup requires `.ases-output` and refuses engineering/repository directories and links; a `.ases` name alone is insufficient. `ases clean --all` considers recognized direct outputs only. Use temporary directories for disposable trials and keep persistent output when it is a useful baseline.

When a baseline includes `consumer-context.json`, the scan also writes `semantic-diff.json`.
It reports changed recovered entities and paths, not security verdicts. `docs/SUMMARY.md` is a
short review aid; the detailed RAD/SDD/ODD remain evidence-based reconstructions. A document
fingerprint matches its scan manifest, but does not by itself prove the current source is unchanged.

Pattern analysis is precision-first. `scanner-findings.json.findings` contains observed/actionable pattern results; weak signals are isolated in `scanner-findings.json.hints`.

For a bounded, inspectable correctness measurement, run `python tools/evaluate_accuracy.py --out /local/accuracy.ases` from this directory with test dependencies installed. It generates offline HTML, Markdown and JSON with explicit source oracles, per-capability precision/recall/F1, false alarms, omissions and declared limits. The bundled 16-case corpus passes and exits 0; it is not a global accuracy estimate. See [the evaluation guide](../docs/ACCURACY.md) and [TESTING.md](../TESTING.md) for reproduction.

Generic imported JS/TS calls are retained as `library_call` entities, not automatically outbound boundaries. Known service-package roots and Node HTTP(S) request operations retain `external_api_call` candidates; static usage still does not prove traffic. Unrecognized clients remain unclassified library calls. Classification profile `imported_calls: module-call/2` prevents old/new classifications from granting certain absence in snapshot comparisons. Observer opportunities use per-call Node EventEmitter counterevidence and apply parser guards across all eight admitted JS/TS suffixes; custom buses, subclasses and arbitrary alias mutation remain partial.

## Structural snapshots and queries

Source scans write both legacy `consumer-context.json` (1.5, unchanged identity vocabulary) and `consumer-context.v2.json` (2.0, canonical identities, observations, relations and scoped coverage). `export` defaults to 1.5; request 2.0 explicitly. Exporting 2.0 requires a saved v2 snapshot and never silently rescans a bare YAML model.

```bash
ases export current.ases --schema 2.0 --out context-v2.json
ases inspect current.ases
ases inspect current.ases --collection structural_relations --offset 0 --limit 20
ases inspect current.ases --collection entities --select read --limit 20
ases trace current.ases "GET /users" --direction forward --max-nodes 1000
ases trace current.ases read --direction backward
ases semantic-diff previous.ases current.ases
```

Directories prefer their saved v2 sidecar for these services. Selectors exactly match ID, name or path; multiple matches are returned as ambiguous, without picking one. Pages sort deterministically, carry the parent snapshot ID and distinguish delivery pagination from source coverage. `max-nodes` (1–10,000) limits expanded trace entities; attached relation endpoints remain represented to preserve referential integrity.

The supported parser admits `.js/.jsx/.mjs/.cjs/.ts/.tsx/.mts/.cts`, literal imports/re-exports/require, local declarations and selected framework forms. Type-only imports do not become runtime calls. Compiler path aliases, computed dispatch, framework-global middleware and embedded Vue/Svelte scripts are not exhaustively resolved. JS/TS declaration coverage may be `ANALYZED` while relationship coverage remains `PARTIAL`. Java/Python recovery retains its existing heuristic limits.

Literal export-star chains resolve unique local exports with explicit-export precedence, cycle handling and a profiled depth limit. HTTP sites use lexical scope and occurrence identities, independent of source lines; shared backend/frontend extraction avoids duplicate request entities. Imported axios/jquery aliases and typed Angular HttpClient receivers are admitted; matching a local variable's name alone is insufficient. `coverage.relationship_families` reports six independent methods/scopes under profile `scoped/2`. Comparisons retain uncertainty for missing/partial family coverage or changed methods, including older saved v2 profiles. See the [consumer contract](../integrations/CONSUMER-CONTRACT.md) for exact compatibility rules.

## Scoped route and test recovery

Python recovery admits directly imported `Flask`/`Blueprint` constructors (including import aliases), literal `.route` rules and method lists, and direct method decorators. Functions and handlers nested directly in factories retain lexical owners and scope-based identities; local parameters/reassignments cannot authorize a call to a same-named outer helper. Blueprint constructor prefixes and literal local `register_blueprint` overrides/multiple mounts are composed statically. Dynamic prefixes, method lists and arbitrary registration options remain unknown. Conditional declarations, nested classes/blueprints, cross-module registration overrides and implicit HEAD/OPTIONS expansion are not fully resolved. Route metadata marks declarations as `declared-static`; it does not certify runtime registration or reachability.

Express-like route calls require a path plus a handler argument. One-argument `app.get(setting)` is a configuration read and does not become an endpoint. An explicit handler argument that cannot be resolved retains a partial route with an unknown reason.

Java recovery also admits annotated package-private `void` test methods for `Test`, `ParameterizedTest` and `RepeatedTest`, including qualified annotation names. Comments and string literals do not authorize those declarations. Java extraction remains heuristic, custom/meta-annotations and arbitrary method grammar are not exhaustive, and test declarations never imply execution or assertion coverage.

## Supplied artifacts and imported observations

```bash
ases scan-artifact supplied-dist --out artifact.ases
ases reconcile-artifact current.ases artifact.ases/artifact-snapshot.json --out reconciliation.json
ases reconcile-artifact current.ases artifact.ases/artifact-snapshot.json --runtime runtime.json \
  --mapping '{"runtime_prefix":"https://example.org/assets/","artifact_prefix":""}'
```

Only supplied files are read: no target import, build, bundle execution, map fetch or runtime collection. Bounds: 2,000 artifact files, 5 MiB per file, 64 MiB total bytes; source parsing also limits AST traversal to 200,000 named nodes. Symlinks/junctions and escaping paths are excluded. Limits and parser recovery remain explicit unknowns. Unsupported source-map forms stay unknown; v3 `sourcesContent` is hashed and never exported verbatim. Selected `package.json` fields are `name`, `version`, `type`, `main`; scripts/configuration/secrets are not extracted.

Runtime JSON follows `ases-runtime-observations/1.0`, requiring collector, environment, timezone-bearing `captured_at`, capture coverage and script `location`/`loaded` assertions with optional byte digests. See the [schemas](../schemas/runtime-observations.schema.json) and [contract](../integrations/CONSUMER-CONTRACT.md). Explicit location mappings cannot override a digest mismatch. A loaded script does not establish resident modules, executed features or deployment truth. Snapshot readers reject unsupported schemas, malformed records and altered hashes; digests do not authenticate a producer.
