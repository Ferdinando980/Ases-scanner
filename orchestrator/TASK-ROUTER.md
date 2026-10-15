# ASES Task Router

The router selects rigor and skills. Do not invoke every skill by default.

## 1. Classify the task

### BUGFIX
A defect against intended/current behavior.

Default rigor: `LEAN`.
Escalate to `STANDARD` if cross-component, public-contract, security, persistence, or architectural impact exists.

Required skills:
- impact-analyzer
- simplicity-gate
- test-designer
- consistency-auditor

Optional:
- requirements-auditor if intended behavior is ambiguous;
- system-designer/object-designer if design is implicated;
- traceability-keeper if project uses trace links.

### FEATURE
New or changed externally visible behavior.

Default rigor: `STANDARD`.
Escalate to `FORMAL` for new subsystem, architecture, security boundary, data model migration, or high-risk change.

Required skills:
- requirements-auditor
- impact-analyzer
- simplicity-gate
- pattern-scout when a non-trivial design problem remains
- test-designer
- traceability-keeper
- consistency-auditor

Add system-designer/object-designer when their layer changes.

### REFACTOR
Structural change with intended behavior preserved.

Default rigor: `LEAN` or `STANDARD` depending on scope.

Required skills:
- impact-analyzer
- simplicity-gate
- object-designer if public/internal contracts move
- test-designer
- consistency-auditor

Do not rewrite requirements unless behavior changes.

### ARCHITECTURE
Subsystem boundaries, global policies, deployment, persistence strategy, access control, concurrency, global control.

Rigor: `FORMAL`.

Required skills:
- requirements-auditor
- impact-analyzer
- system-designer
- simplicity-gate
- pattern-scout if appropriate
- object-designer
- test-designer
- traceability-keeper
- consistency-auditor

### DOCUMENTATION
Documentation-only work.

Rigor: `LEAN` unless reconstructing formal project artifacts.

Required skills:
- impact-analyzer
- traceability-keeper if links change
- consistency-auditor

Never invent code behavior to make docs look complete.

### TESTING
Test addition/fix/plan/report.

Rigor: `LEAN` to `FORMAL` based on requested artifact.

Required skills:
- impact-analyzer
- test-designer
- consistency-auditor

Add requirements-auditor when the oracle is ambiguous.

## 2. Automatic escalation triggers

Escalate one rigor level for any of:

- authentication/authorization/security boundary;
- schema/data migration;
- irreversible data operation;
- public API compatibility change;
- cross-subsystem interface change;
- concurrency/control-flow policy change;
- deployment/infrastructure topology change;
- regulatory/contractual acceptance criteria;
- unclear requirement whose interpretation changes architecture.

## 3. De-escalation

Do not downgrade below what explicit project policy requires.

Otherwise prefer the lowest rigor that still preserves correctness, safety, traceability, and useful design knowledge.

## 4. Router output

Keep this compact:

```yaml
classification: FEATURE
rigor: STANDARD
reasons:
  - externally visible behavior
impacted_layers:
  - requirements
  - object_design
  - code
  - tests
skills:
  - requirements-auditor
  - impact-analyzer
  - simplicity-gate
  - object-designer
  - test-designer
  - traceability-keeper
  - consistency-auditor
```


## Repository-state routing (v0.3)

Before complexity-level selection:

- no implementation / greenfield intent → `GREENFIELD`
- implementation + reliable docs → `BROWNFIELD-DOCUMENTED`
- implementation + missing/stale/partial docs → `BROWNFIELD-UNDOCUMENTED`

For `BROWNFIELD-UNDOCUMENTED`, invoke `reverse-engineering-orchestrator` before generating or updating formal design artifacts.
