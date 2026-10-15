# ASES Decision Gates v0.2

These are decision checkpoints, not ceremonial documents. Record only enough evidence to make the decision auditable.

## G0 — Understanding Gate

PASS when the agent has:

- read the request;
- located the real implementation flow end-to-end;
- identified relevant existing tests/docs;
- identified ambiguity that would change implementation choices.

FAIL → inspect more or ask for clarification.

Never run the simplicity ladder before understanding the real flow.

---

## G1 — Requirement Quality Gate

For STANDARD/FORMAL behavior changes, PASS when intent is sufficiently:

- correct to stakeholder intent;
- complete for requested slice;
- consistent;
- unambiguous;
- realistic;
- traceable;
- testable.

If not: clarify instead of guessing.

---

## G2 — Impact Gate

PASS when affected items are identified across the relevant layers:

- requirements;
- scenarios/use cases;
- analysis objects/dynamics;
- subsystem/services;
- interfaces/classes/contracts;
- source code;
- tests;
- deployment/persistence/security as relevant;
- documentation/traceability.

The output is an impact set, not a request to regenerate every artifact.

---

## G3 — Simplicity Gate

Stop at the first rung that fully satisfies current requirements, constraints, design goals, and safety needs:

1. Does this need to exist? If speculative: skip.
2. Already in the codebase? Reuse.
3. Standard library? Use it.
4. Native platform/framework feature? Use it.
5. Already-installed dependency? Reuse it.
6. Can current design absorb it locally and clearly? Prefer that.
7. Only then add the minimum new code/abstraction.

### Abstraction evidence

Before adding interface/factory/strategy/wrapper/layer/config/plugin/dependency, name at least one concrete reason:

- multiple real variants;
- replaceability/portability requirement;
- external/unstable dependency isolation;
- actual behavior variation;
- harmful duplication;
- required test/security boundary;
- stated design goal;
- known planned change;
- framework/platform requirement;
- measured performance/resource need.

No evidence → reject abstraction.

### Protected concerns

Never simplify away:

- trust-boundary validation;
- security/authz;
- data-loss prevention/error handling;
- accessibility basics;
- explicit requirements;
- correctness on known edge cases.

---

## G4 — Pattern Gate

Run only after G3 leaves a genuine design problem.

### A. State problem and forces first

Do not start from a pattern name.

### B. Candidate set

At most 1–3 candidates.

### C. Compare against direct design

Benefits:

- lower coupling?
- isolates change?
- reduces duplication?
- clarifies responsibility?
- improves testability/substitutability?
- supports a required design goal?

Costs:

- extra types/files?
- indirection?
- harder runtime flow?
- configuration/wiring?
- cognitive/maintenance load?

### D. Decision

`APPLY <pattern>` — benefits materially exceed costs.

`NO PATTERN` — direct design is clearer/cheaper.

`DEFER` — only with a concrete revisit trigger.

Record:

```text
Problem:
Evidence:
Candidate(s):
Direct alternative:
Decision:
Why:
Consequences:
Related requirement/design goal:
Revisit trigger (if deferred):
```

---

## G5 — Design Readiness Gate

Before STANDARD/FORMAL implementation, confirm:

- responsible subsystem/component known;
- public/external interface impact known;
- persistence/security/concurrency/deployment checked where relevant;
- G3 passed;
- G4 completed if relevant;
- test oracle/acceptance behavior known.

---

## G6 — Test Design Gate

PASS when:

- correct test level selected;
- oracle is explicit;
- normal + important boundary/error cases covered;
- Category Partition used where systematic input-domain partitioning is valuable;
- duplicate/useless test cases removed;
- integration strategy chosen where multiple components are involved.

---

## G7 — Execution / Regression Gate

PASS when:

- changed behavior is exercised;
- applicable existing tests pass;
- failures are investigated, not hidden;
- corrections trigger relevant regression tests;
- actual vs expected is recorded when formal test reporting applies.

---

## G8 — Traceability / Consistency Gate

Before completion verify:

- behavior has a source reason;
- affected requirement points to current design/code/test;
- affected design matches code;
- tests point to current behavior/requirement;
- no material stale document/diagram contradiction;
- pattern decisions have rationale;
- new abstractions have evidence.

---

## G9 — Release Gate

For FORMAL work or explicit releases:

- acceptance criteria satisfied or exceptions recorded;
- unresolved incidents listed;
- relevant artifacts baselined;
- release notes/change summary available;
- known risks/debt explicitly carried forward.


# Reverse Engineering Gates

## R0 — Inventory Gate
PASS when:
- primary languages/frameworks/build tools are identified;
- entry points and major modules are known;
- tests/docs/config locations are known;
- generated/vendor code is separated from owned code.

## R1 — Evidence Gate
For every recovered high-level claim, require at least one evidence source.

Inference without evidence is not a recovered fact.

## R2 — Architecture Recovery Gate
PASS when major boundaries and dependencies are recoverable enough to explain:
- where requests/events enter;
- where business behavior lives;
- where data persists;
- what external systems are called;
- where significant cross-boundary control occurs.

## R3 — Behavior Recovery Gate
PASS when each significant recovered behavior has:
- actor/trigger;
- entry point;
- main path;
- relevant branches/errors;
- side effects;
- implementation evidence.

## R4 — Documentation Bootstrap Gate
PASS when generated documentation:
- labels provenance/confidence;
- does not claim unknown historical intent;
- distinguishes observed implementation from inferred requirements;
- contains no ceremonial empty sections.

## R5 — Traceability Recovery Gate
PASS when significant recovered behavior can be navigated to implementation and existing tests where present.

## R6 — Conflict Gate
PASS only when contradictions are either resolved with evidence or explicitly left `CONFLICTING`.
