---
name: system-designer
purpose: Maintain high-level system architecture and system-wide strategies.
---

# System Designer

## Trigger

Use for architecture/subsystem/global-policy changes or FORMAL work.

## Inputs

- requirements/nonfunctional requirements/constraints;
- analysis model;
- current architecture;
- design goals;
- impact analysis.

## Procedure

Evaluate only relevant dimensions:

1. design goals and priority/trade-offs;
2. subsystem decomposition;
3. cohesion/coupling/dependencies;
4. concurrency;
5. hardware/software mapping and buy-vs-build;
6. persistent data management;
7. access control/security;
8. global resource handling;
9. global software control;
10. boundary conditions: startup/shutdown/failure/recovery;
11. subsystem services.

Refine decomposition until the important design goals are adequately satisfied.

## Output

- updated SDD sections and/or concise design decision record;
- changed subsystem responsibilities/interfaces;
- explicit trade-off rationale.

## Stop conditions

Do not select implementation classes prematurely when the issue is still architectural.

## Mutation boundary

May modify SDD/architecture docs and architectural interfaces. Implementation details belong to Object Designer/implementation.
