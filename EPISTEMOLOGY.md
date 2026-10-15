# ASES Epistemology — v1.9

ASES does not treat every signal as a finding. Every claim must expose what supports it, what weakens it, and what remains assumed.

## Claim states

- `OBSERVED` — direct repository evidence supports the claim.
- `INFERRED` — multiple observations support a derived claim, but it is not directly encoded.
- `OPPORTUNITY` — a concrete smell and sufficient evidence support a refactoring suggestion.
- `HINT` — weak signal; normally hidden from the default scanner feed.
- `UNKNOWN` — evidence is insufficient.
- `CONTRADICTED` — evidence conflicts with an already observed architectural claim.
- `SUPPRESSED` — a valid finding was explicitly accepted by project policy; it remains traceable.

## Evidence rules

Every scanner-facing finding carries a stable fingerprint, rule ID, confidence, evidence, counter-evidence, assumptions, and guidance. Line-number-only movement must not create a new finding identity.

Architecture conformance is derived from the architecture ASES first observes. ASES never imposes Layered Architecture, MVC, or another pattern on a repository that has not supplied evidence for it.

## Coverage

A `PASS` validates ASES output consistency; it does not mean the whole system was verified. `analysis_coverage` records what static analysis inspected and what remains unknown or unobserved (runtime behavior, deployment topology, external-system behavior).

## Suppression

Create `.asesignore` in the scanned repository:

```text
conformance.layered_dependency | intentional legacy shortcut
opportunity.strategy_dispatch | stable three-way dispatch; abstraction not justified
```

Suppressed findings move to `scanner-findings.json.suppressed`; they are not deleted from evidence history.


## Source ownership precedes inference

No inference is stronger than its source. Before facts enter architecture/pattern rules, ASES classifies their files. Generated documentation, vendored/minified libraries, build/tooling code and ordinary documentation cannot be promoted into production architecture claims. This gate applies equally to backend and frontend analysis.

## Structural snapshot 2.0

Entity identity, finding fingerprint, observation identity and snapshot identity have separate purposes. Canonical entity keys omit line/time/presentation data; structural remapping is an inferred correspondence, never behavioral equivalence. Duplicate candidates stay ambiguous. Observation hashes include source bytes, location, extractor/profile, authority and limitations. Snapshot digests cover the saved output; neither hash proves authenticity, freshness or truth.

`evidence_states` and `claim_states` remain separate enums. Public static relations and paths are `INFERRED` even when their supporting syntax is observed. Legacy context 1.5 preserves its vocabulary; migrating to 2.0 requires explicit identity mappings and state interpretation.

Coverage states are `ANALYZED`, `PARTIAL`, `UNKNOWN`, `NOT_OBSERVED`, `NOT_APPLICABLE`. `ANALYZED` means the declared method inspected that scope; it does not mean all software behavior is known. File declarations, relationships, bounded paths and query delivery have separate scopes. Cycles, parser recovery, unresolved dispatch and resource limits preserve collected facts with residual unknowns and unknown omission counts.

With profile `scoped/2`, relationship coverage is further separated into declarations, imports, calls, type heritage, controls and tests, each with its method, admitted scope and reasons. A family missing from an older snapshot remains unknown to comparisons. Absence requires comparable family methods/scopes; declaration completeness alone cannot establish missing HTTP calls, controls, routes or tests. A variable named axios/http is insufficient client evidence: receiver authority must come from admitted imports or declared HttpClient types, respecting lexical shadowing and mutation. Even an admitted receiver is a static inference, not a network observation.

An import/SDK is a candidate dependency; a reconstructed client call is static use; a literal endpoint is syntax evidence. None proves traffic or data sensitivity. A method decorator or local control signal has a declared target/scope and does not prove effective protection. Static test calls are distinguishable from `name-hint` candidates and always leave execution/outcome unverified.

Current diffs retain one-sided entities/findings as uncertain when profiles, source scopes or relevant detection coverage are not comparable. Exhaustive declaration extraction cannot certify disappearance of a heuristic finding. Legacy-only deltas remain descriptive with unverified absence authority.

Artifact correspondence uses exact bytes or supplied source-map assertions; contradictory/ambiguous maps remain visible. Imported runtime assertions retain collector, environment, time and capture scope. Missing observations in a partial capture do not establish global absence; loaded scripts do not establish executed features.
