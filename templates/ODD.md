# Object Design Document — Template

## 1. Object Design overview

Describe how analysis/system-design information is refined into implementation-level objects.

## 2. Package/module structure

## 3. Reuse and adaptation decisions

- existing project code reused;
- stdlib/native/framework features reused;
- installed/COTS components reused;
- wrappers/adapters only where justified.

## 4. Subsystem/API interface specifications

## 5. Class/interface specifications

For each material public/subsystem class or interface:

```yaml
name: ClassName
kind: class|interface|record|module
subsystem: ...
responsibility: ...
visibility: ...
operations:
  - signature: ...
    parameters: ...
    returns: ...
    exceptions: ...
    preconditions: ...
    postconditions: ...
invariants: ...
dependencies: ...
security_notes: ...
persistence_notes: ...
concurrency_notes: ...
pattern_role: null
source: src/...
related_requirements: [...]
related_tests: [...]
```

## 6. Design pattern decisions

Include only patterns actually justified by the Pattern Gate.

## 7. Restructuring decisions

## 8. Optimization decisions

Only evidence-backed optimizations.

## 9. Traceability
