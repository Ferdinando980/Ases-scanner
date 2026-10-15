# ASES Source Map

This file explains where the standard came from and what authority each source has.

## A. University course — normative methodological source

### Introduction / lifecycle

Used for:

- software engineering as disciplined production rather than code-and-fix;
- distinction between requirements/definition, development/design/implementation/testing, and maintenance;
- lifecycle choice, iterative/incremental development, and risk awareness;
- verification vs validation.

### UML modeling

Used for:

- functional/object/dynamic model distinction;
- use case, class, sequence, statechart, activity, component, deployment roles;
- UML as specification/modeling notation, not implementation itself.

### Requirements elicitation

Used for:

- SOW/problem-statement contents;
- scenarios and use cases;
- functional/nonfunctional requirements and constraints;
- validation: correctness, completeness, consistency, clarity, realism, traceability;
- requirement evolution/change management;
- requirement wording (`shall`/`should`/`may`, structured condition-subject-action-object-constraint form);
- RAD structure.

### Requirements analysis

Used for:

- iterative clarification/formalization;
- functional, analysis-object, dynamic models;
- use-case-driven participating-object discovery;
- ambiguity/inconsistency/omission detection.

### Project organization / communication / management

Used for:

- explicit roles and responsibility;
- planned/unplanned communication events;
- reviews, walkthroughs, inspections, releases, postmortems;
- scheduling/dependencies/PERT/Gantt concepts;
- project/product/business risks.

### System Design

Used for:

- design goals and trade-offs;
- subsystem decomposition and refinement;
- concurrency;
- hardware/software mapping;
- persistent data management;
- access control/security;
- global resource handling/control;
- boundary conditions;
- SDD structure and subsystem services.

### Object Design

Used for:

- Object Design as implementation-level refinement;
- reuse/buy-vs-build;
- class libraries/COTS/adaptation;
- interface/API specification;
- contracts;
- restructuring;
- optimization;
- ODD as class/interface specification rather than a mere pattern report.

### Design Patterns

Course catalog used in v0.2:

- Abstract Factory
- Builder
- Adapter
- Bridge
- Composite
- Facade
- Proxy
- Command
- Observer
- Strategy

Course textual clues are treated as candidate-generation hints, not automatic pattern-selection rules.

### Testing / Category Partition

Used for:

- testing as expected-vs-observed comparison;
- unit/integration/system/performance distinctions;
- test oracle;
- Category Partition categories/choices/constraints/test frames;
- drivers/stubs and integration strategies;
- regression testing;
- TP/TCS/TIR/TSR roles and structures;
- incident vs fault distinction.

### Mapping Models to Code

Used for:

- forward/reverse engineering;
- object-model transformations;
- refactoring as behavior-preserving structural change;
- maintaining consistency from models to code.

## B. Refactoring.Guru — external pattern reference

Authority: secondary reference for pattern intent, structure, applicability, and trade-offs.

It does not override project requirements, course constraints, or the Simplicity Gate.

## C. Ponytail — external simplicity discipline

Authority: simplicity/YAGNI influence only.

ASES adopts the core ladder:

1. Does it need to exist?
2. Already in codebase?
3. Standard library?
4. Native platform/framework?
5. Installed dependency?
6. Existing design/local solution?
7. Minimum new code.

ASES explicitly preserves security, validation, accessibility, data-loss prevention, correctness, and explicit requirements.

## D. JustInTime — illustrative student case study

Authority: example only.

Useful for:

- seeing a complete set of student-produced SOW/RAD/SDD/ODD/testing artifacts;
- traceability-matrix shape;
- realistic examples of requirements, diagrams, subsystem documentation, tests, and code;
- identifying where real project documents become incomplete or drift from methodology.

Not used as normative authority where it diverges from course material.


## v0.3 Reverse Engineering

Primary methodological basis:
- course material on model↔code transformations, forward engineering, reverse engineering, and refactoring;
- lifecycle/design/testing material for the models being reconstructed.

ASES extensions:
- provenance states;
- artifact trust model;
- semantic-model export;
- documentation-bootstrap workflow.

These extensions prevent false certainty during automated recovery.


## v0.5 Executable semantic recovery

ASES extension:
- deterministic Java/Spring and TypeScript/Node repository scanners;
- fact-graph normalization;
- evidence-preserving semantic inference;
- trust-boundary and asset inference;
- recovered RAD rendering.

The implementation is intentionally conservative: compiler-grade AST resolution and security interpretation remain outside this milestone.


## v1.0 Self-hosting and integration

ASES engineering extensions:
- self-hosting validation;
- baseline drift audit;
- generic consumer context;
- optional downstream adapters.

These do not change the source hierarchy: course material remains the methodological foundation, external pattern/simplicity sources remain supplemental, and downstream consumers do not define ASES core semantics.
