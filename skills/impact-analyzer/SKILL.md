---
name: impact-analyzer
purpose: Find the smallest complete set of affected artifacts and code.
---

# Impact Analyzer

## Trigger

Run for every code/documentation change except trivial text edits with no semantic impact.

## Inputs

- task/change intent;
- repository tree and relevant call/dependency flow;
- existing traceability data;
- current docs/tests.

## Procedure

1. Locate the actual source path(s) implementing the behavior.
2. Trace callers/callees, data flow, and relevant tests.
3. Follow traceability links when available.
4. Check impact across:
   - requirements;
   - scenarios/use cases;
   - analysis object/dynamic model;
   - subsystem/services;
   - interfaces/classes/contracts;
   - persistence/security/concurrency/deployment;
   - source files;
   - tests;
   - docs/trace links.
5. Mark each layer `changed`, `verify_only`, or `unaffected`.

## Output

```yaml
impact:
  requirements: verify_only
  system_design: unaffected
  object_design: changed
  code:
    changed: [path/...]
  tests:
    changed: [tests/...]
  docs:
    changed: [docs/ODD.md]
```

## Rule

The goal is not maximum coverage of documents. It is the **minimum complete impact set**.

## Mutation boundary

Read-only. It identifies impact; downstream skills perform edits.
