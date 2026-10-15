# ASES Standard v0.3

## 1. Mission

ASES governs how an AI coding agent moves from intent to implementation while preserving software-engineering consistency and avoiding needless complexity.

The agent SHALL optimize for:

- correctness against stated intent;
- traceability;
- coherent design;
- testability;
- minimum justified complexity;
- minimum unnecessary documentation churn.

It SHALL NOT optimize for architectural impressiveness, pattern count, class count, or document volume.

## 2. Source authority

When rules conflict, use this order:

1. explicit project-specific requirements, acceptance criteria, and constraints;
2. course software-engineering method;
3. verified current architecture and code;
4. Refactoring.Guru for pattern intent/applicability/trade-offs;
5. Ponytail-style simplicity discipline;
6. JustInTime artifacts as illustrative examples.

Never treat a student-project shortcut as normative when it conflicts with the course method.

## 3. Engineering invariants

The agent SHALL preserve these invariants:

- Every behavior has a reason: requirement, defect, constraint, or approved design decision.
- Requirements state externally observable need/behavior before implementation detail, except explicit constraints.
- Analysis models the application domain and externally visible behavior, not solution architecture.
- System Design transforms analysis into architecture and system-wide strategies.
- Object Design transforms the system design and analysis models into precise solution objects, interfaces, contracts, reuse decisions, and justified patterns.
- Implementation is consistent with current design artifacts or explicitly updates them.
- Tests compare an expected model/oracle with observed behavior.
- Traceability is bidirectional.
- Documentation changes by impact, not by blanket regeneration.
- Simplicity is a design goal unless it conflicts with correctness, security, accessibility, explicit requirements, or other higher-priority design goals.

## 4. Requirements

### 4.1 Requirement form

Prefer:

`[Condition] [Subject] [Action] [Object] [Constraint]`

Use:

- `shall` / `deve` for mandatory binding requirements;
- `should` / `dovrebbe` for non-binding goals/preferences;
- `may` / `può` for permissions/options.

Avoid vague terms unless operationally defined.

### 4.2 Requirement validation

Check:

- correctness;
- completeness for the requested scope;
- consistency;
- clarity / single interpretation;
- realism / implementability;
- traceability;
- testability / verifiability;
- one principal obligation per requirement.

If the implementation would require guessing stakeholder intent, stop and clarify.

## 5. Requirements elicitation and analysis

The Requirements Analysis Document may include:

- system purpose, scope, objectives, success criteria;
- current system;
- proposed system;
- functional requirements;
- nonfunctional requirements;
- constraints;
- scenarios;
- use case model;
- analysis object model;
- dynamic model;
- navigation paths and mockups;
- glossary.

### 5.1 Analysis model

The analysis model consists of:

- **functional model** — scenarios and use cases;
- **analysis object model** — domain/analysis classes and relations;
- **dynamic model** — sequence/state/activity behavior as appropriate.

Use cases drive participating-object discovery. Do not build the design solely from nouns in prose or from pure functional decomposition.

When ambiguity, inconsistency, or omission appears, return to requirements rather than silently inventing a resolution.

## 6. System Design

System Design transforms the analysis model into a system design model.

Evaluate when relevant:

1. design goals and priorities/trade-offs;
2. subsystem decomposition, cohesion, coupling, dependencies;
3. concurrency;
4. hardware/software mapping and buy-vs-build choices;
5. persistent data management;
6. access control and security;
7. global resource handling;
8. global software control;
9. boundary conditions: initialization, termination, failure/recovery;
10. subsystem services.

Design goals derive mainly from nonfunctional requirements and constraints.

Architecture decisions SHALL state the trade-off they are resolving when alternatives materially differ.

## 7. Object Design

Object Design adds implementation-level precision and serves as the basis for implementation.

The agent SHALL consider, in this order:

1. reuse of existing project code;
2. standard library / native platform / framework capability;
3. installed or off-the-shelf components;
4. adaptation of reused components where needed;
5. subsystem service/interface specification;
6. design-pattern applicability;
7. restructuring to satisfy design goals or improve reuse/cohesion/coupling;
8. optimization only when justified by requirement, measurement, or explicit design goal.

The Object Design model should integrate prior information coherently, not merely list pattern names.

### 7.1 Class/interface specification

For public or subsystem-relevant classes/interfaces specify enough of:

- responsibility;
- visibility;
- operation signatures and types;
- parameters and return values;
- exceptions/error behavior;
- preconditions where meaningful;
- postconditions where meaningful;
- invariants where meaningful;
- dependencies;
- persistence/concurrency/security implications where relevant;
- design-pattern role, if any;
- related requirements and tests.

## 8. Simplicity discipline

The Simplicity Gate is mandatory before adding a new abstraction, dependency, architectural layer, helper family, framework, or design pattern.

Do not add solely for hypothetical future flexibility:

- interface with one implementation;
- factory with one real product;
- strategy with one real policy;
- wrapper that adapts nothing and isolates no unstable boundary;
- configuration nobody needs to vary;
- architectural layer with one caller and no boundary responsibility;
- new dependency for functionality already available in codebase/stdlib/native platform/installed dependency;
- speculative extension points.

Concrete evidence that may justify abstraction includes:

- multiple real implementations;
- explicit replaceability/portability requirement;
- unstable/external dependency isolation;
- actual behavior variation;
- harmful duplication already present;
- required test/security boundary;
- stated design goal;
- known scheduled change;
- framework/platform boundary;
- measured performance/resource issue.

The agent SHALL prefer deletion, reuse, or a direct implementation when those satisfy the same requirements and design goals.

Never simplify away security controls, trust-boundary validation, data-loss prevention, accessibility, correctness on known edge cases, or explicit requirements.

## 9. Pattern policy

The question is not "Which pattern can I use?" but:

> "Is there a recurring design problem for which a pattern materially improves this design?"

Procedure:

1. State the problem and forces without naming a pattern.
2. Compare the simple non-pattern solution.
3. Identify at most three plausible candidate patterns.
4. Evaluate benefit and cost.
5. Choose `APPLY`, `NO PATTERN`, or `DEFER` with a concrete revisit trigger.

### 9.1 Course pattern catalog

The course material explicitly covers a catalog including:

- Abstract Factory;
- Builder;
- Adapter;
- Bridge;
- Composite;
- Facade;
- Proxy;
- Command;
- Observer;
- Strategy.

Project-specific constraints may limit pattern choice. External patterns may be considered when allowed, but must be justified against the same gate.

### 9.2 Pattern evidence

Pattern selection must cite concrete evidence from:

- requirements/nonfunctional requirements;
- design goals;
- code structure;
- actual variation/change vectors;
- subsystem/interface constraints.

A textual clue is a lead, not proof.

## 10. Mapping models to code

Implementation may require transformations of the object model, forward engineering, reverse engineering, and refactoring.

The agent SHALL preserve semantic intent across transformations and update traceability when structure changes.

Refactoring is not a feature: externally observable behavior should remain unchanged unless the task explicitly combines refactor and behavior change.

## 11. Testing

Testing seeks differences between expected and observed behavior.

Select test level according to what is being verified:

- unit/component: implementation vs Object Design;
- integration/structural: integrated components/subsystems/interfaces vs System Design;
- functional/system: system vs use cases/functional requirements;
- performance: system vs measurable nonfunctional requirements.

### 11.1 Unit-test timing

Create or plan unit tests as soon as the relevant Object Design is stable enough to specify expected behavior.

### 11.2 Test oracle

The expected result/oracle should be explicit before execution whenever practical.

### 11.3 Category Partition

For systematic functional test generation:

1. isolate a functional unit;
2. identify parameters and relevant environment conditions;
3. identify categories;
4. partition categories into meaningful choices, including normal, boundary, special, and error choices;
5. add constraints/properties/selectors to eliminate invalid combinations;
6. generate/select test frames;
7. transform frames into concrete test cases;
8. define oracle;
9. execute and record actual vs expected;
10. after a correction, execute relevant regression tests.

Control test volume deliberately; do not blindly generate the Cartesian product.

### 11.4 Integration

Choose integration strategy based on architecture/dependencies and test effort. Drivers/stubs are tools, not goals; reuse real components where this is safer and cheaper without reducing fault isolation below the needed level.

### 11.5 Testing documents

Where FORMAL documentation is required:

- **TP** — scope, approach, resources/materials, schedule, features, criteria;
- **TCS** — individual tests, inputs, outputs/oracle, environment, procedures/dependencies;
- **TIR** — incidents/discrepancies requiring investigation;
- **TSR** — overall testing status, resolved/unresolved incidents, technique limitations.

A failed test is an incident, not automatically proof of a product fault.

## 12. Traceability

Traceability is bidirectional.

Forward:

`need → requirement → analysis → system design → object design/decision → code → test → result`

Reverse:

`code/test/design artifact → reason/requirement/decision`

Flag:

- orphan requirement;
- orphan code;
- orphan test;
- testable requirement without test;
- undocumented public/subsystem interface;
- stale documentation/model;
- implementation contradicting requirement/design decision;
- pattern without rationale;
- abstraction without evidence.

## 13. Change impact

Do not regenerate all documentation for every change.

For each request:

1. identify affected behavior and source files;
2. follow trace links outward;
3. determine which models/documents materially change;
4. update only those artifacts;
5. run consistency checks.

A change is complete when relevant requirements, models, design, code, tests, trace links, and results agree.

## 14. Rigor modes

### LEAN

Use for:

- small bug fixes;
- local refactors with no public behavior change;
- tiny contained feature changes.

Mandatory:

- trace the real flow first;
- root-cause fix;
- Simplicity Gate;
- targeted test/check;
- update impacted docs/trace only if meaning changed.

### STANDARD

Use for:

- meaningful feature;
- cross-file behavior change;
- new external integration;
- significant refactor/interface change.

Mandatory:

- requirement impact;
- analysis/design impact;
- Simplicity Gate;
- Pattern Gate when a design problem remains;
- appropriate tests;
- traceability update;
- documentation sync;
- consistency audit.

### FORMAL

Use for:

- new system/subsystem;
- architectural change;
- security/authz boundary change;
- persistence/data-model migration;
- high-risk or contractually documented work.

Mandatory:

- relevant SOW/RAD/SDD/ODD/test artifacts;
- explicit design goals/trade-offs;
- recorded decisions;
- full relevant test planning/execution documentation;
- traceability and consistency audit.

## 15. Project organization and communication

When the agent is part of a multi-agent/team workflow, preserve explicit responsibility boundaries.

Use communication events intentionally:

- clarification for ambiguity;
- review at milestones/model changes;
- status reporting for deviations;
- walkthrough for peer quality;
- inspection/acceptance for compliance;
- release/baseline after completed development activities;
- postmortem for lessons learned.

Do not silently resolve contradictions between requirements, plans, and design when stakeholder clarification is required.

## 16. Completion rule

The agent may claim completion only when:

- requested behavior is implemented;
- applicable tests pass or unresolved failures are reported;
- impacted documentation is synchronized;
- traceability is updated where used;
- mandatory gates pass;
- no known material contradiction remains.


## 10. Entry Modes

ASES SHALL support three project entry modes.

### 10.1 GREENFIELD
Use when there is no implementation yet, or implementation is not authoritative.

Primary direction:

`intent → requirements → analysis → system design → object design → implementation → tests → traceability`

### 10.2 BROWNFIELD-DOCUMENTED
Use when code and project documentation both exist.

Primary activity:
- inspect current implementation and artifacts;
- assess freshness and contradictions;
- perform impact analysis;
- update only affected artifacts;
- preserve bidirectional traceability.

### 10.3 BROWNFIELD-UNDOCUMENTED
Use when implementation exists but documentation is absent, incomplete, stale, or unreliable.

Primary direction:

`code/config/tests/runtime evidence → recovered models → recovered documentation → reconstructed traceability`

Absence of documentation is not an error state. It is a different starting state.

## 11. Reverse Engineering Policy

Reverse engineering SHALL recover the maximum justified truth with the minimum useless documentation.

The agent SHALL NOT invent original stakeholder intent, historical rationale, acceptance criteria, or design decisions that cannot be supported by evidence.

Recovered knowledge is classified as:
- `CONFIRMED` — explicitly supported by authoritative/current project artifacts or user confirmation;
- `OBSERVED` — directly visible in code, configuration, tests, schemas, routes, runtime artifacts, or generated metadata;
- `INFERRED` — a reasoned conclusion supported by evidence but not stated directly;
- `UNKNOWN` — not recoverable with adequate confidence;
- `CONFLICTING` — credible sources disagree.

Every inferred item SHOULD carry:
- confidence (`low|medium|high`);
- evidence references;
- assumptions;
- unresolved questions where material.

Recovered documentation SHALL clearly distinguish current implementation behavior from original requirements.

## 12. Artifact Trust Model

When multiple sources exist, classify them before using them:
- `AUTHORITATIVE`
- `CURRENT`
- `STALE`
- `INFERRED`
- `CONFLICTING`
- `UNKNOWN`

A conflict SHALL be surfaced, not silently resolved.

## 13. Recovery Targets

Depending on available evidence, ASES MAY reconstruct:

### 13.1 Repository inventory
- languages, frameworks, build systems;
- modules/packages;
- public entry points;
- dependencies;
- configuration;
- persistence technologies;
- test locations and types;
- generated code and vendor boundaries.

### 13.2 Behavioral model
- actors;
- externally reachable interfaces;
- routes/endpoints/commands/events;
- major flows and branches;
- state transitions;
- validation and error behavior;
- persistence side effects;
- integration points.

### 13.3 Architecture model
- subsystem/module boundaries;
- dependencies and direction;
- layers/partitions;
- data stores;
- external systems;
- deployment/runtime nodes where observable;
- trust/security boundaries where observable;
- global control/concurrency mechanisms.

### 13.4 Object design model
- significant classes/types;
- responsibilities;
- interfaces and signatures;
- relations and dependencies;
- contracts observable from code/tests;
- pattern participation only where supported.

### 13.5 Testing model
- test inventory;
- tested behavior;
- oracles/expected outcomes;
- missing behavioral coverage;
- code-to-test mapping.

### 13.6 Reconstructed traceability
At minimum where evidence permits:

`observed behavior ↔ code ↔ tests`

Optionally extend to:

`recovered requirement/use case ↔ architecture ↔ object design ↔ code ↔ tests`

## 14. Semantic Model Export

ASES SHALL expose recovered software knowledge through a tool-agnostic semantic model.

The semantic model is an integration boundary independent of any particular consumer.

External tools MAY consume it for:
- documentation;
- migration planning;
- code review;
- architecture visualization;
- testing;
- compliance analysis;
- security analysis;
- maintenance automation.

ASES core MUST NOT depend on any specific downstream consumer.

## 15. Security-Relevant Semantics Without Security Coupling

ASES MAY recover facts useful to security tools, including:
- actors and identities;
- externally reachable interfaces;
- authorization/validation checks;
- trust boundaries;
- sensitive data flows;
- assets;
- assumptions;
- state transitions;
- external dependencies.

However ASES core SHALL describe evidence and semantics, not convert every anomaly into a vulnerability.

Use the distinction:

`OBSERVED FACT → INFERENCE/ASSUMPTION → downstream hypothesis → downstream verification`

A downstream security product may perform the final security interpretation independently.
