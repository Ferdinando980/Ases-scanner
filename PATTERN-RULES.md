# ASES Pattern Analysis Rules — v1.7

ASES treats pattern analysis as an evidence problem, not a pattern-matching game.

## Output states

- **OBSERVED** — static structure provides direct evidence consistent with the pattern/architecture.
- **OPPORTUNITY** — a concrete smell plus supporting evidence makes the refactoring worth surfacing.
- **HINT** — a weak signal exists, but evidence is insufficient for the main scanner feed.

`scanner-findings.json.findings` contains observed/actionable items. Low-confidence HINT items are isolated in `hints[]`; explicit project suppressions remain auditable in `suppressed[]`. Pattern results also expose a conceptual `level`: ARCHITECTURE, APPLICATION_PATTERN, GOF, or DESIGN_IDIOM.

## Global guardrails

1. Production code only. Test files do not generate refactoring opportunities.
2. One weak syntactic signal is never enough for an OPPORTUNITY.
3. Standard-library types, exceptions, DTOs/responses and generic value objects are filtered from Factory evidence.
4. Receiver count is not Facade evidence. Facade requires repeated dependency-level subsystem overlap across production components.
5. Low-confidence results are HINT, not actionable findings.
6. Every result includes positive/negative signals, evidence, confidence, rule ID, rationale and a "do not use when" guardrail.
7. A pattern is never presented as required merely because it is applicable.

## Architectural patterns

### Layered Architecture — `architecture.layered`
OBSERVED when the dependency graph contains controller→service and service→repository edges. Confidence increases with repeated evidence and decreases when controller→repository shortcuts are observed.

### MVC — `architecture.mvc`
OBSERVED when controllers, model/domain types and view templates are all present. Static structure is not treated as proof of perfect MVC responsibility separation.

### Repository — `architecture.repository`
OBSERVED from production repository components recovered by language/framework scanners.

### Service Layer — `architecture.service_layer`
OBSERVED when multiple production services exist and controllers depend on them.

## Creational

### Factory — `creation.factory_idiom`
OBSERVED when a Factory-named production type creates multiple meaningful targets. OPPORTUNITY requires a real creation-selection policy (for example conditional dispatch among meaningful concrete targets). Mere co-location of `new` expressions is insufficient.

Filtered evidence includes exceptions, DTO/request/response/value records, common standard-library containers and common framework response/view wrappers.

## Behavioral

### State — `behavior.state_family`, `opportunity.state_dispatch`
OBSERVED from a State-named common contract with multiple production implementations. OPPORTUNITY may be emitted for state/status/phase dispatch with at least three branches.

### Strategy — `behavior.strategy_family`, `opportunity.strategy_dispatch`
OBSERVED from a Strategy-named contract with multiple implementations. Generic three-way variant dispatch is only a HINT; stronger branching is required for an OPPORTUNITY.

### Command — `behavior.command_family`, `opportunity.command_dispatch`
OBSERVED from a Command-named contract with multiple implementations. OPPORTUNITY requires command/action/operation dispatch with multiple branches.

### Observer — `opportunity.observer_fanout`
OPPORTUNITY requires direct fan-out to at least three distinct listener/subscriber/notification endpoints. Three calls to the same endpoint do not qualify.

Receiver names alone do not authorize the opportunity. For admitted JS/TS suffixes (`.js/.jsx/.mjs/.cjs/.ts/.tsx/.mts/.cts`), comments and literal contents are withheld. Calls to `.emit` on statically bound Node EventEmitter instances provide counterevidence and are excluded individually; unrelated direct notifications in the same file still count. Import aliases, namespace/CommonJS constructors and simple instance aliases are admitted. Shadowed or mutated instances/constructors do not provide this authority; ambiguous same-line occurrences remain conservative. Subclasses, custom event buses, cross-module factories and arbitrary alias mutation are not exhaustively resolved. Parser byte/encoding/scope guards apply to every admitted suffix.

### Chain of Responsibility — `opportunity.chain_handlers`
OPPORTUNITY requires at least three distinct handler-like branches with sequential early-return dispatch.

### Template Method — `opportunity.template_method`
A base/abstract lifecycle without a proven invariant orchestration is only a HINT. It becomes an OPPORTUNITY when the base type both defines and invokes several lifecycle steps.

## Structural

### Adapter — `opportunity.adapter_boundary`
OPPORTUNITY requires boundary-oriented code, an external/client signal and multiple renamed field translations. Mapping alone is only a HINT.

### Facade — `opportunity.facade_repeated_orchestration`
OPPORTUNITY is project-level and requires at least two production components to actively call at least three of the same subsystem collaborators. Shared injected fields, local variables, DOM APIs and arbitrary receiver counts are insufficient.

### Decorator — `opportunity.decorator_wrapping`
Nested wrapping alone is a HINT. OPPORTUNITY requires stronger evidence that wrappers share a naming/role contract.

### Proxy — `opportunity.proxy_remote_concerns`
OPPORTUNITY requires repeated remote-access evidence plus at least two cross-cutting access concerns such as retry, cache, auth/token or timeout. Native client middleware/interceptors remain the preferred simpler solution when sufficient.


## Source hygiene gate (v1.7)

Pattern rules run only on `OWNED_SOURCE` production code by default. Tests may provide test evidence but do not generate refactoring opportunities. `GENERATED`, `VENDORED`, `TOOLING`, `DOCUMENTATION`, and `BUILD_ARTIFACT` files are inventoried when useful but cannot trigger design-pattern recommendations.

Additional precision rules:
- Factory requires branch-local selection among alternative concrete products; many unrelated `new` expressions are insufficient.
- Facade requires repeated *active calls* to the same subsystem collaborators from multiple production components; shared injected fields alone are insufficient.
- Adapter can be `OBSERVED` when an Adapter-named contract is implemented at an external protocol/API boundary.
- `DAO` and `*ServiceImpl` idioms contribute to Repository/Service Layer/Layered Architecture evidence.

## Frontend rules (v1.7)

Frontend analysis uses the same claim states and evidence contract as backend analysis. It recovers owned components, server-rendered templates, API/service modules, stores, literal API calls and forms. If a frontend API service layer is first `OBSERVED`, direct component-to-API calls may become `CONTRADICTED`; without that observed convention, repeated direct calls are at most an `OPPORTUNITY`. Cross-boundary unmatched routes remain `HINT` unless an exact path is observed with a conflicting HTTP method.
