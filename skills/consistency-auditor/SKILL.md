---
name: consistency-auditor
purpose: Final cross-artifact verification before completion.
---

# Consistency Auditor

## Trigger

Run at the end of every non-trivial task; broader scope for FORMAL work.

## Checks

1. Requirement vs implemented behavior.
2. Analysis/use case vs externally visible flow.
3. System Design vs subsystem/dependency reality.
4. Object Design/interface contracts vs code.
5. Pattern decision vs actual structure.
6. Abstraction evidence vs actual need.
7. Tests/oracles vs requirement/design.
8. Traceability links vs current artifact names/paths.
9. Documentation for stale contradictions.
10. Relevant regression test status.

## Output

If clean:

```text
CONSISTENT — no material contradiction found in impacted scope.
```

Otherwise list only actionable mismatches with location and required correction.

## Mutation boundary

Audit first. May fix trivial stale references; substantive corrections should route back to the owning skill.
