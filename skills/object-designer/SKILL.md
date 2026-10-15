---
name: object-designer
purpose: Bridge analysis/system design to implementation-level classes, interfaces, and contracts.
---

# Object Designer

## Trigger

Use when class/interface responsibilities, subsystem APIs, contracts, reuse/adaptation, restructuring, or pattern participation change.

## Inputs

- analysis object/dynamic model;
- subsystem services/interfaces;
- design goals;
- reuse options;
- simplicity/pattern decisions.

## Procedure

1. Map required operations from functional/dynamic behavior to solution objects.
2. Reuse/adapt existing code/components first.
3. Specify subsystem/class interfaces:
   - operations;
   - arguments/types;
   - returns;
   - exceptions/error behavior.
4. Add preconditions/postconditions/invariants where they carry useful constraints.
5. Apply approved pattern decisions, if any.
6. Restructure only to satisfy concrete design goals/reuse/cohesion/coupling needs.
7. Optimize only with evidence or requirement.
8. Keep package/dependency direction coherent.

## ODD output

For each materially relevant class/interface:

```yaml
name: ...
responsibility: ...
subsystem: ...
operations: ...
contracts: ...
dependencies: ...
pattern_role: null
related_requirements: [...]
related_tests: [...]
source: path/...
```

## Anti-pattern rule

An ODD is not a pattern report. Pattern sections are only one part of Object Design.

## Mutation boundary

May update ODD and code-facing design structures. System-wide strategy remains System Designer scope.
