---
name: traceability-keeper
purpose: Maintain bidirectional trace links across requirements, design, code, and tests.
---

# Traceability Keeper

## Trigger

Use when the project maintains traceability and any linked artifact changes; mandatory for STANDARD/FORMAL when traceability exists.

## Canonical chain

`need → requirement → analysis → system design → design decision/object design → code → test → result`

Reverse links must also be possible from code/test/design to reason/requirement.

## Procedure

1. Reuse stable IDs; do not renumber casually.
2. Add links only where meaningful.
3. Remove/mark stale links when artifacts disappear or split.
4. Flag:
   - orphan requirement;
   - orphan code;
   - orphan test;
   - testable requirement without test;
   - stale design/code mismatch;
   - pattern without rationale;
   - abstraction without evidence.
5. Do not force every private helper to have its own requirement ID. Trace at the useful responsibility/change level.

## Output

Update `schemas/traceability.yaml`-compatible project data or the project's equivalent matrix.

## Mutation boundary

May edit traceability records. Must not invent missing artifacts to fill cells.
