---
name: pattern-scout
purpose: Decide whether a design pattern is justified, and which one.
---

# Pattern Scout

## Trigger

Run only when the Simplicity Gate leaves a genuine recurring design problem or the task explicitly asks for pattern analysis.

## Inputs

- concrete problem/forces;
- relevant requirements/nonfunctional requirements;
- design goals;
- affected classes/subsystems;
- direct/simple alternative.

## Procedure

1. State the problem without a pattern name.
2. Identify evidence/change vector.
3. Consider at most 1–3 plausible candidates.
4. Compare each against the direct alternative.
5. Evaluate coupling, change isolation, duplication, responsibility clarity, testability, indirection, file/type count, runtime-flow complexity, wiring, maintenance load.
6. Decide `APPLY`, `NO PATTERN`, or `DEFER`.

## Course catalog

- Abstract Factory
- Builder
- Adapter
- Bridge
- Composite
- Facade
- Proxy
- Command
- Observer
- Strategy

External patterns may be considered when project policy allows; use Refactoring.Guru for intent/trade-offs, not as a reason to force a pattern.

## Useful clues, not proof

Examples from the course:

- product family / manufacturer independence → Abstract Factory candidate;
- existing incompatible object → Adapter candidate;
- abstraction and implementation may vary independently → Bridge candidate;
- complex subsystem façade → Facade candidate;
- location transparency/access indirection → Proxy candidate;
- extensible notifications → Observer candidate;
- policy independent from mechanism → Strategy candidate.

A clue starts analysis; it does not decide it.

## Output

```yaml
pattern_decision:
  problem: ...
  evidence: ...
  candidates: [Strategy]
  direct_alternative: ...
  decision: NO_PATTERN
  rationale: ...
  consequences: ...
  revisit_trigger: null
```

## Stop condition

If no concrete evidence for abstraction remains, stop with `NO_PATTERN`.

## Mutation boundary

Produces design decision. Object Designer applies it to class/interface design.
