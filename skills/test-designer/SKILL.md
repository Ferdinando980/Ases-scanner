---
name: test-designer
purpose: Select the right testing level, design cases/oracles, and preserve regression coverage.
---

# Test Designer

## Trigger

Use for every non-trivial behavior change and explicit testing work.

## Inputs

- requirement/use case or defect expectation;
- object/system design as relevant;
- existing tests/infrastructure;
- changed code paths.

## Select level

- unit/component: implementation vs Object Design;
- integration/structural: components/subsystems/interfaces vs System Design;
- functional/system: behavior vs use cases/functional requirements;
- performance: measured behavior vs nonfunctional requirements.

## Procedure

1. State what is being verified.
2. Define oracle before execution when practical.
3. Cover representative normal behavior.
4. Cover important boundaries/errors.
5. Use existing test infrastructure; do not add a framework unnecessarily.
6. For systematic input spaces, use Category Partition:
   - functional unit;
   - parameters/environment;
   - categories;
   - choices;
   - constraints/properties/selectors;
   - test frames;
   - concrete cases.
7. Remove duplicate/redundant cases.
8. For integration, choose strategy based on component dependency graph and isolation needs.
9. After fixes, run relevant regression tests.

## Incident discipline

A failed test is an incident. Investigate whether cause is product code, wrong oracle, wrong test setup, or inconsistent requirement before labeling a product fault.

## Output

- tests and/or TP/TCS/TIR/TSR updates as required;
- commands run;
- pass/fail/incident summary.

## Mutation boundary

May modify tests and testing docs. Do not change product requirements merely to make a failing test pass.
