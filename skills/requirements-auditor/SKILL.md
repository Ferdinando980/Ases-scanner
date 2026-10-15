---
name: requirements-auditor
purpose: Validate or refine change intent before design/implementation.
---

# Requirements Auditor

## Trigger

Use for new/changed behavior, ambiguous defect expectations, FORMAL work, or explicit requirements work.

## Inputs

- user request / stakeholder statement;
- existing requirements and constraints;
- relevant scenarios/use cases;
- acceptance criteria if present.

## Procedure

1. Separate functional requirement, nonfunctional requirement, and constraint.
2. Check correctness to stated stakeholder intent; do not infer missing business intent silently.
3. Check completeness for the requested slice, including important exceptional/limit conditions.
4. Check consistency with existing requirements.
5. Check clarity / single interpretation.
6. Check realism.
7. Check traceability.
8. Check testability.
9. Prefer `[Condition][Subject][Action][Object][Constraint]` for formal requirements.
10. Use `shall` for mandatory requirements, `should` for goals, `may` for permissions.

## Output

Either:

```yaml
status: PASS
requirements:
  - id: RF-...
    statement: ...
acceptance_oracles:
  - ...
```

or:

```yaml
status: NEEDS_CLARIFICATION
questions:
  - ...
why_it_matters: ...
```

## Stop conditions

Stop implementation when ambiguity would materially alter externally visible behavior, security, persistence, or architecture.

## Mutation boundary

May propose/update requirement artifacts. Must not redesign architecture unless routed to a design skill.
