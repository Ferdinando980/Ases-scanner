# Example — Adding a second notification provider

## Router

```yaml
classification: FEATURE
rigor: STANDARD
```

## Impact

Existing notification code has one provider and a new explicit requirement adds a second provider.

## Simplicity Gate

- Need exists: yes.
- Existing provider code can be reused partially.
- Stdlib/native does not solve provider selection.
- There are now two real behavior variants.

Result: abstraction evidence exists.

## Pattern Gate

Problem: runtime-selectable notification behavior with two real implementations.

Candidates: Strategy, direct conditional.

Decision: `APPLY Strategy` only if provider behavior is substantial or expected to vary independently. If the choice is a tiny stable branch, use `NO PATTERN` and keep direct code.

The pattern is not selected merely because there are two classes.
