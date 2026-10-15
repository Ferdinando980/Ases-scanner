# ASES Consumer Contracts — legacy 1.5 and structural 2.0

ASES remains standalone. External tools consume generic output; ASES core contains no consumer-specific logic.

## Primary files

- `scanner-findings.json` (`ases-scanner-findings/1.3`) — normalized scanner feed.
- `consumer-context.json` (`ases-consumer-context/1.5`) — full recovered semantic context.
- `consumer-context.v2.json` (`ases-consumer-context/2.0`) — optional normalized structural snapshot; query services prefer this saved sidecar.
- `semantic-model.yaml` — canonical ASES model.
- `findings-diff.json` (`ases-finding-diff/2.0` for current scoped feeds; 1.0 for legacy-only feeds) — optional baseline delta.

## ASES 1.9 compatibility and structural 2.0

The default 1.5 context and 1.3 scanner wire shapes remain available. Extractor improvements can change recovered facts and internal display IDs; historical JS/TS IDs are not promised stable across the parser replacement. The 2.0 sidecar is a new contract, not an additive identity/state change to 1.5. `export --schema 2.0` requires a saved 2.0 snapshot; default `export` stays 1.5. No consumer needs the raw graph.

| Public field | Meaning and consumer obligation |
|---|---|
| `entities` | Canonical ID, legacy ID, name/kind/path, normalized properties, scoped identity and observation references. Keys use module/owner/name/signature, omitting line/time. Duplicate keys remain ambiguous. |
| `observations` | Content-derived ID, subject/predicate, typed source locations and hashes/roles, extractor version/method, authority, state, confidence, source descriptor and limitations. Source is ASES's own project tool, not independent attestation. |
| `structural_relations` | ID, real `from`/`to` entity endpoints, relation, basis, `INFERRED` state and valid observation references. Symbolic unresolved markers are not public endpoints. Counts are derived from this collection. |
| `identity_mapping` | Explicit legacy-to-canonical IDs with unique/ambiguous state. Diff migration can additionally infer a unique family/name/source match for older contexts; ambiguous candidates remain visible. |
| `source_manifest`, `analysis_profile` | Analyzed source-byte hashes/roles, engine/parser versions, exclusions and source mode. A profile change prevents certifying one-sided presence as removal. |
| `coverage`, `analysis_unknowns` | Separate file, relationship-family, dimension and bounded-path coverage; parser/dispatch/resource residuals. Unknown omission counts are null. |
| `snapshot_id`, `validation`, `untrusted_content` | Deterministic hash of the saved JSON excluding generation time and snapshot ID; validation checks consistency. Neither authenticates the producer nor proves current source freshness. Treat content as untrusted data. |

Hash serialization uses sorted JSON keys, compact separators, UTF-8, finite JSON values; it is ASES's serialization, not RFC 8785 canonicalization. Schema checks and runtime validators complement referential/hash checks. Snapshots are read as bounded regular JSON files (64 MiB maximum); unknown schema versions and malformed/altered records fail explicitly.

Context readers admit 1.3, 1.4, 1.5 and 2.0. Older preserved YAML models can be exported to a descriptive 1.5 context; missing freshness/coverage remains unknown. A successful export does not reconstruct evidence absent from the historical model.

Public static paths are `INFERRED`, with entity/relationship/observation references, traversal basis, assumptions, limits and scoped coverage. Declarations may be analyzed while relationships stay partial. Source observation does not establish execution. A nominal test fallback becomes `candidate_test_link` / `test_candidate`; static test calls have explicit basis and `test_executed: false`. Legacy consumers must inspect the added basis even where the historical `verifies` label remains. Controls distinguish lexical handler scope, method decorator candidates and unresolved/heuristic scope; presence is not effectiveness.

The acceptance fixes use profiles `identity: source-symbol/2`, `relations: static/2`, `coverage: scoped/2`. HTTP callsite keys combine lexical owner, method, redacted literal endpoint and occurrence within that scope, independently of lines. Repeated requests remain distinct. An occurrence distinguishes repeated syntax; it does not establish equivalence after arbitrary statement reordering. Import aliases for axios/jquery and an imported Angular HttpClient type support admitted request receivers; ambient fetch is admitted only without a conflicting lexical binding. Local names, type-only executable imports, receiver mutation and rebound `this` do not establish client authority. Factory-created clients and compiler aliases outside these forms remain unresolved.

`coverage.relationship_families[path]` contains exactly `declarations`, `imports`, `calls`, `type_heritage`, `controls`, `tests`. Each record has `status`, `method`, `scope: {path, admitted}`, `reasons`, and `omitted_count`. It is required for `scoped/2`; validators still accept saved `scoped/1` snapshots without it. The coarse legacy `files[path].relationships` remains available, but grants no absence authority. Calls, controls and test linking remain partial; unsupported methods are unknown and test-source methods can be not applicable. Imports and declared class heritage may be analyzed within their stated local/static scope. Literal export-star chains use explicit-export precedence, exclude inherited defaults, and retain ambiguous/unavailable destinations as unresolved. Cycles terminate; the binding-depth resource limit is included in the parser profile and emits `export_resolution_limit`.

Structural relation presence uses its source endpoint's relevant family, matching method/scope in comparable profiles. Missing family coverage, a partial method or an unrecognized relation stays uncertain. Request/route, control/session and test entities likewise cannot use declaration coverage to certify absence. Derived dimensions and rule findings still need their own coverage. Typed locations share the inventory's source-extension registry, including all admitted template suffixes; URL ports remain values. These profile/identity changes require explicit comparison handling rather than a promise that earlier experimental v2 IDs are unchanged. Older snapshots remain readable; profile differences prevent certain one-sided deltas. No previous-ID mapping is invented when historical callsites had already collided.

`external_systems` preserves import candidates and adds `usage_basis` (`import-candidate` or `static-client-call`) and supported `call_refs`. Literal endpoint calls also exist as normalized entities/relations. Imports, static client usage and observed traffic remain distinct; no jurisdiction, production deployment or personal-data conclusion is inferred.

Imported JS/TS module calls without admitted service-client authority are `library_call` entities with `calls` relations based on `imported-module-call`. An import alone does not make an outbound API boundary; these entities do not terminate sensitive paths. Known service-package roots and Node HTTP(S) `get`/`request` operations retain static client candidates; literal requests keep their existing extraction. `network_effect: unverified` does not establish execution or traffic. Unrecognized clients remain observable library calls, with remote effects unresolved rather than absent. The parser profile records `imported_calls: module-call/2`; comparing older classifications must preserve profile uncertainty. Wire versions remain 1.5/1.3/2.0 and readers must tolerate generic entity kinds.

## Snapshot services and artifact contracts

`inspect` returns `ases-analysis-view/1.0`; `trace` returns `ases-feature-trace/1.0`. Both carry `parent_snapshot_id`. Exact ID/name/path selectors return ambiguity rather than choose a candidate. Deterministic offset/limit pagination is delivery scope, not source completeness. Tracing reports its expansion cap and includes attached endpoints to preserve evidence references. Neither service rereads current source.

`scan-artifact` writes `ases-artifact-snapshot/1.0`: supplied-file hashes/roles, parsed function fingerprints/imports, source-map content hashes/assertions, selected package metadata, limits and unknowns. It does not export raw `sourcesContent`, run builds/targets or fetch maps. Every inventoried file remains `BUILD_ARTIFACT`.

`reconcile-artifact` writes `ases-artifact-reconciliation/1.0`: source/artifact parent snapshot IDs, `matched`/`ambiguous`/`mismatch`/`unknown` source correspondences, optional runtime correspondences, capture provenance and limitations. Exact bytes and source-map-content correspondence are distinct bases; neither establishes behavioral equivalence. Artifact fingerprints are exposed for inspection; this slice does not infer arbitrary minified/transformed symbol equivalence or decode source-map VLQ mappings.

Optional runtime input is `ases-runtime-observations/1.0`, with collector name/version, environment, timezone-bearing capture time, capture coverage and script location/loaded assertions with optional SHA-256. Explicit prefix mappings are consumer-supplied. Digest disagreement remains mismatch even if locations match; absence in a partial capture remains unknown. Loaded script, resident module, executed feature and deployed application are distinct conclusions; this slice correlates supplied script observations only. ASES acquires none of them.

## v1.5 changes (additive over v1.4)

`external_systems` is now real, not the always-empty placeholder v1.4 deliberately left out of
the contract. `recover_external_systems` (`runtime/ases/recovery/semantic.py`) matches each
node's raw import strings (`node.metadata["imports"]`, already collected by the Java/
TypeScript/Python scanners) against a **fixed allowlist** of well-known third-party API/service
clients (OpenAI, Anthropic, Stripe, AWS SDK, Supabase, Twilio, SendGrid, Firebase). Every entry
is `provenance.state: "INFERRED"`, never `"OBSERVED"`: an import proves the client/SDK is
present in the code, not that it is actually called, which endpoint it hits, or what data it
sends — `provenance.assumptions` says this explicitly on every entry.

Generic database drivers (`pg`, `mongodb`, JDBC drivers, ...) are **not** in the allowlist on
purpose: they would overlap with `data_stores` (recovered separately from `entity` nodes),
which already covers "the app's own data", a different concept from "a third-party system".

This is a starting allowlist, not exhaustive — a client library not on the list simply produces
no `external_systems` entry for it; that is "not detected", never "confirmed absent".

## v1.4 changes (additive over v1.3)

`consumer-context.json` gained four top-level keys. A v1.3-only consumer can ignore all of
them and keep working unmodified; nothing from v1.3 was removed or reshaped.

- `ases_version` — the ASES release that produced this file (`ases.__version__`), so a
  consumer can tell which behavior/bug set generated the data without shelling out to
  `ases --version`.
- `generated_at` — ISO 8601 UTC timestamp of this export.
- `project_fingerprint` — the same fingerprint as `manifest.json`, when a manifest was
  available at export time (the full pipeline always produces one; a standalone `ases export`
  run against a bare `semantic-model.yaml` may not, in which case this is `null` — a consumer
  must treat `null` as "freshness unknown", never as "unchanged" or "stale").
- `data_stores` — entities ASES's graph classified as data-holding (`kind: "entity"`),
  excluding test code. Same shape as `components`/`interfaces` (`id`, `name`, `kind`,
  `description`, `provenance`). This says an entity exists and how it was found — it is not a
  personal-data or sensitivity classification; a consumer must not infer GDPR/PII status from
  presence alone.

## Scanner feed

`findings[]` contains normal actionable/observed results. `hints[]` contains weak evidence. `suppressed[]` contains explicit accepted exceptions.

Each finding exposes:

- stable `fingerprint` and `id`;
- `rule_id`, `type`, `category`, `level`, and optional `pattern`/`subject`;
- epistemic `status` and `confidence`;
- `evidence`, `evidence_strength`, `counter_evidence`, and `assumptions`;
- location, message, signals, and guidance;
- `surface` (`backend`, `frontend`, `cross_boundary`, `project`), `actionability`, normalized `entity`, and `source_role`.

Consumers should key history on `fingerprint`, not line number or display ID.

## Baseline/diff semantics

`ases diff` and `scan --baseline` classify findings as:

- `new`
- `resolved`
- `changed`
- `unchanged`
- `unknown` for disappearance without comparable rule-specific coverage in current feeds

A line-number-only move remains the same fingerprint and does not count as a semantic change.

`ases semantic-diff <before.ases> <after.ases>` (also emitted by `scan --baseline` when the
baseline contains `consumer-context.json`) writes `ases-semantic-diff/1.0`. It reports added,
removed, and changed evidence-bearing entities by stable id/fingerprint across behaviors,
components, interfaces, stores, external systems, boundaries, controls, sessions, sensitive paths, frontend
findings, cross-boundary findings, and claims. Line-number-only evidence moves are ignored.
This is an inventory delta, **not** a security verdict. A baseline consisting only of
`scanner-findings.json` still produces only the original findings diff.

The preceding 1.0 behavior describes legacy-only comparison, with `absence_authority: unverified-legacy`. Comparing structural 2.0 snapshots (or migrating between versions) produces `ases-semantic-diff/2.0`, adding tests, trace links, normalized entities/relations, uncertainty, inferred identity remappings/candidates, profile change and evidence change. Only method-complete comparable scopes certify one-sided presence. Derived detection requires its own coverage; declaration coverage alone cannot certify missing paths, controls or architecture. Changed source hashes/positions can change evidence without changing meaning. URLs retain port/path meaning.

Current finding feeds produce `ases-finding-diff/2.0`. Disappeared findings require complete coverage for their rule and file; the present heuristic finding methods do not claim exhaustive coverage, so disappearance normally stays unknown. This is a deliberate semantic change, separately versioned. Legacy-only finding diffs keep 1.0 descriptive categories with unverified resolution authority.

`docs/SUMMARY.md` is a generated review aid, separate from RAD/SDD/ODD. Like the other signed
documents, it belongs to a scan snapshot; its signature alone does not prove the current source
tree still matches that snapshot.

## Two distinct epistemic vocabularies — do not conflate them

ASES uses two separate state enums; a consumer that merges them into one "confidence level"
will misread the model.

- `evidence_states` (`CONFIRMED`, `OBSERVED`, `INFERRED`, `UNKNOWN`, `CONFLICTING`) — attached
  to individual pieces of provenance (a node/behavior's evidence), i.e. "how was this single
  fact established".
- `claim_states` (`OBSERVED`, `INFERRED`, `OPPORTUNITY`, `HINT`, `UNKNOWN`, `CONTRADICTED`,
  `SUPPRESSED`) — the `status` on `claims`, `pattern_findings`, `conformance_findings`,
  `frontend_findings`, `cross_boundary_findings`, i.e. "what ASES concludes about a pattern or
  architectural expectation, and how it stands relative to counter-evidence".

They overlap in name (`OBSERVED`, `INFERRED`, `UNKNOWN`) but are not the same axis: a finding
can be `claim_states: CONTRADICTED` while every individual piece of evidence behind it is
`evidence_states: CONFIRMED` (the evidence is solid, the architectural expectation it
contradicts is what's in question) — collapsing the two into one scale loses that distinction.

## Architecture conformance

`CONTRADICTED` findings mean code evidence conflicts with an architecture ASES first observed from the same project. They are not universal style rules. This distinction should remain visible in every consumer.

## Coverage

`coverage` explicitly records analysis limitations. A validation `PASS` is schema/model consistency, not proof that runtime behavior, deployment, or external systems were verified.


## Source ownership and frontend

`source_classification` reports repository roles before inference. `GENERATED`, `VENDORED`, `TOOLING`, `DOCUMENTATION`, and `BUILD_ARTIFACT` files do not drive production design-pattern opportunities.

`frontend` in consumer context contains recovered owned components, templates, API/service modules, stores, and literal API calls. `frontend_findings` and `cross_boundary_findings` use the same epistemic states/fingerprints as backend findings, so consumers should ingest them through the same pipeline rather than a frontend-specific parser.

For Angular source, `frontend.routes` contains route declarations as written in `*.routes.ts`; nested paths are not flattened into externally reachable URLs without more context.

## Published-site input (ASES 1.8)

`ases scan-site <url>` writes the same `ases-consumer-context/1.5` and `ases-scanner-findings/1.3` schemas. `project.entry_mode` and `project.source_mode` are `LIVE_SITE`. The additive `site_observations` object contains sampled public HTML pages, their titles and hashes, forms, referenced scripts, and framework hints. `frontend.pages` is an additive list of delivered pages; it is not source templates. `frontend_findings` contains an informational `site.published_frontend_surface` observation.

Consumers must read `semantic_quality.analysis_coverage`: source structure, architecture, design patterns, frontend component structure and frontend/backend contracts are `NOT_OBSERVED` for a site scan. A `validation: PASS` checks output consistency, not site completeness or behavior. Live mode does not execute JavaScript, submit forms, fetch authenticated pages, or infer component architecture from compiled bundles.
