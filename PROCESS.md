# ASES Process v0.3

## Entry detection

Before normal task routing, determine repository state:

```text
Code? Docs?
  │
  ├─ no code / no authoritative implementation
  │    → GREENFIELD
  │
  ├─ code + usable/current docs
  │    → BROWNFIELD-DOCUMENTED
  │
  └─ code + missing/incomplete/stale docs
       → BROWNFIELD-UNDOCUMENTED
```

Mixed states are allowed. A project may have a reliable SDD but no ODD, or a stale README with current tests.

## Forward lifecycle

```text
Request
  ↓
G0 Understand real flow
  ↓
Task Router → LEAN / STANDARD / FORMAL
  ↓
Requirements + impact (as required)
  ↓
G1 Requirement Quality
  ↓
G2 Impact
  ↓
G3 Simplicity
  ↓
G4 Pattern (only if needed)
  ↓
System/Object Design updates (if impacted)
  ↓
G5 Design Readiness
  ↓
Implementation / refactoring
  ↓
G6 Test Design
  ↓
Tests
  ↓
G7 Execution/Regression
  ↓
Traceability + documentation sync
  ↓
G8 Consistency
  ↓
G9 Release when applicable
```

## Reverse-engineering lifecycle

```text
Repository / codebase
  ↓
R0 Repository inventory
  ↓
R1 Artifact trust assessment
  ↓
R2 Architecture recovery
  ↓
R3 Behavior recovery
  ↓
R4 Object/design recovery
  ↓
R5 Test recovery
  ↓
R6 Semantic model reconstruction
  ↓
R7 Documentation bootstrap
  ↓
R8 Traceability reconstruction
  ↓
R9 Consistency/conflict audit
  ↓
Documented brownfield baseline
```

### R0 Repository inventory
Identify the smallest set of facts needed to understand the system:
- languages/frameworks/build tools;
- entry points;
- modules/packages;
- dependencies;
- database/storage;
- config;
- external integrations;
- tests;
- docs already present.

Do not document every file merely because it exists.

### R1 Artifact trust assessment
Classify available sources:
`AUTHORITATIVE | CURRENT | STALE | INFERRED | CONFLICTING | UNKNOWN`.

### R2 Architecture recovery
Recover boundaries, dependencies, runtime/deployment shape, persistence, external systems, control flow, and security/trust boundaries only where evidence exists.

### R3 Behavior recovery
Trace real end-to-end flows from public entry point to side effects.

### R4 Object/design recovery
Recover significant classes/interfaces, responsibilities, contracts, state machines, and design structures. Do not assign named patterns without evidence.

### R5 Test recovery
Map tests to behavior and implementation. Record uncovered significant behavior rather than fabricating coverage.

### R6 Semantic model reconstruction
Normalize recovered information into `semantic-model.yaml`.

### R7 Documentation bootstrap
Generate only useful baseline artifacts. Mark provenance and confidence.

### R8 Traceability reconstruction
Build observed links such as:
`behavior → implementation → test`.

### R9 Consistency/conflict audit
Report contradictions, stale documents, orphan implementation, undocumented behavior, and unresolved unknowns.

## Transition rule

When enough baseline documentation exists for maintenance:

`BROWNFIELD-UNDOCUMENTED → BROWNFIELD-DOCUMENTED`

Future work then uses normal impact-driven synchronization.

## Artifact policy

Artifacts are maintained only when they carry useful project knowledge.

- Small/local changes may update no formal document.
- A material public behavior change should usually update requirement/trace/test information.
- Architecture/security/persistence changes require explicit design documentation.
- Do not create empty ceremonial documents.
- Reverse engineering does not justify a documentation dump.

## Documentation sync rule

At the end of a change, ask:

1. Did externally visible behavior change?
2. Did a subsystem/interface responsibility change?
3. Did a public class/interface contract change?
4. Did persistence/security/deployment/control strategy change?
5. Did a test oracle/coverage relation change?

Only affected artifacts are updated.
