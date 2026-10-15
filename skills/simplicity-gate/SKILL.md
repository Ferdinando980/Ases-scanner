---
name: simplicity-gate
purpose: Prevent over-engineering while preserving correctness and safety.
---

# Simplicity Gate

## Trigger

Always before adding non-trivial code, abstraction, dependency, framework, or pattern.

## Preconditions

The real flow must already be understood. Minimalism without comprehension is not acceptable.

## Ladder

Stop at the first rung that fully satisfies the requirements/design goals:

1. Does this need to exist? Speculative need → skip.
2. Already in codebase? Reuse.
3. Standard library? Use it.
4. Native platform/framework capability? Use it.
5. Already-installed dependency? Reuse it.
6. Existing design can absorb it locally and clearly? Do that.
7. Only then add the minimum new code/abstraction.

## New-abstraction evidence

Require at least one:

- multiple real variants;
- explicit replaceability/portability;
- external/unstable dependency isolation;
- actual behavior variation;
- harmful duplication;
- test/security boundary;
- stated design goal;
- known planned change;
- framework requirement;
- measured performance/resource need.

## Protected concerns

Never remove/simplify away:

- input validation at trust boundaries;
- authorization/security;
- data-loss prevention;
- necessary error handling;
- accessibility basics;
- explicit requirements;
- known edge-case correctness.

## Output

```yaml
simplicity_decision:
  rung: 2
  action: reuse
  evidence: existing helper X already implements required behavior
  rejected:
    - new dependency Y
    - new wrapper Z
```

## Mutation boundary

May reject planned complexity. Does not itself choose a design pattern.
