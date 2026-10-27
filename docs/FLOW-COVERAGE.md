# Reading flow coverage

ASES describes supported local syntax. It does not run the target, solve arbitrary predicates or recover stakeholder intent. A readable sentence can still be incomplete: read its path conditions, **Limits of this flow**, linked source and method profile before acting on it.

Current engineering method: `branch-local-flow/12`. The Java body interpreter uses the official [Tree-sitter Java grammar](https://github.com/tree-sitter/tree-sitter-java), with its installed version and budgets recorded in `behavior_parser_profiles.java`. This profile is separate from the structural graph's Java heuristics and from document declarations. An AST proves syntax structure, not runtime binding or compilation success. Python `http.server` exact-table and ordered literal prefix dispatch are separately recorded as `stdlib-dispatch/2`; Python response outcomes require a supported local serializer/HTTP-writer wrapper, not a method-name guess. Callable return values ignored by this dispatch stay internal, rather than becoming HTTP outcomes. Prefix records use wildcard labels; shadowing, guards and dynamic dispatch remain partial.

| Capability | Python / JS–TS | Java |
|---|---|---|
| If/else and early exits | Supported local paths | Supported in uniquely located method bodies |
| Conditional return expressions | Separate branch outcomes | Separate branch outcomes |
| Short-circuit calls | Retained with local conditions | Retained with local conditions |
| Statements after a local return/throw | Not attributed as subsequent work | Not attributed as subsequent work |
| Nested functions, lambdas and classes | Nested bodies are not outer exits | Nested bodies are not outer exits; anonymous-class methods are excluded |
| Loops and switch/match joins | Partial; no iteration/termination guarantee | Not admitted as resolved flow; compound exits withheld, continuation labelled partial |
| Catch dispatch and conditional finally | Partial; no general propagation proof | Not admitted as resolved flow; compound exits withheld, continuation labelled partial |
| Linked helpers | Bounded linked evidence, not proven entry behavior | Bounded name-based structural links filtered by retained calls; overloads, receiver binding and propagation remain unresolved |
| Constructors, package-private/generic signatures and type binding | Not applicable as a cross-language guarantee | Structural/API heuristics remain incomplete; the body interpreter does not establish complete declaration recovery |
| Malformed Java body | Not applicable | Outward claims withheld; partial recovery reported |

The Java interpreter deliberately omits exits inside unsupported compound constructs rather than flattening them into unconditional results. An omitted error is not proof of error-free execution. A downstream return labelled as a partial continuation is not proof that the construct completes normally. Assert enablement, labelled exits and synchronized joins are also unresolved.

Budgets: 5 MiB per source, 200,000 traversed Java syntax nodes, depth 128 for local Java flow, 500 facts and 64 live paths per body. Reached limits are reported. Linked interpretation remains bounded to 4 call levels and 40 entities per entry. Source positions and grammar/profile changes can require review even when the apparent text is similar; a missing record does not mean a resolved problem.

## Reproducible checks and their limits

`runtime/tests/fixture_documents/product-corpus.json` is a frozen development corpus of **24 synthetic entries**, eight per language family, and 120 expected local-flow claims. The current profile recovers all selected claims: outcomes TP 72 / FP 0 / FN 0; explicit errors and possible effects each TP 24 / FP 0 / FN 0. Version 2 passed 16/24 cases and failed the eight Java path oracles. The labels were not changed to obtain the improvement.

These are variations of one guard/three-exit family, not 24 independent projects. Independent label review remains pending. They do not establish support for the unresolved rows in the table, or correctness of any arbitrary repository.

From the checkout:

```sh
ases documents-evaluate runtime/tests/fixture_documents/product-corpus.json --out product-flow-evaluation
python -m pytest -q runtime/tests/test_java_flow.py
```

The evaluation writes expected/actual facts and explanations to HTML, Markdown and JSON. The Java tests include close negatives for abstract methods, same-line ambiguous overloads, comments, Unicode, nested bodies, dead helper calls, unresolved compound constructs and budgets. Passing a test that requires an explicit limitation does not mean that construct has become fully supported. No target test is executed by these commands.

## Continuations, exports and comparison

Profile 5 labels Python/JS continuations after unresolved loops and conditional
`finally` joins as partial. A preceding return or error that a conditional finally
can override is withheld from outward claims. A literal-false Python while body is
not treated as executed work. JS switch alternatives are not flattened into a
single unconditional path. These rules prevent false certainty; they do not solve
iteration, termination or general exception propagation.

Static JS anonymous assignments such as `exports.read`, `module.exports.read`,
`module.exports` and anonymous default exports can be matched by syntax position.
Computed property names remain unresolved. The graph's consumer identities are
unchanged.

The evaluator uses `whole-expression-negation/2`: whole-predicate negation and
source-language syntax tokens preserve precedence, parentheses and literal content.
A function named `not` is not a logical operator. Structured oracle predicates
must agree with displayed text. This is conservative normalization, not a general
semantic-equivalence solver. See `test_flow_boundaries.py` and
`test_behavior_evaluation.py` for adversarial checks.

The expression comparison profile `syntax-tokens/3` treats physical CR and CRLF
line terminators inside JavaScript template strings as LF, following
[ECMAScript template values](https://tc39.es/ecma262/2022/multipage/ecmascript-language-lexical-grammar.html#sec-template-literal-lexical-components).
Explicit escaped carriage returns, literal spaces and raw escaped text stay
distinct. This affects claim evaluation, not the source evidence or the recovered
business meaning. `test_claim_line_endings.py` covers tagged and ordinary templates
and nearby negatives.

A callable containing only assignments can remain in the interface inventory
without a reconstructed behavioral row: the current local-flow profile describes
admitted returns, explicit errors and possible named calls. A missing row is an
uninterpreted selected entry for coverage, not a successful negative observation or
proof of no state change. General assignment/state-transition interpretation remains
outside this profile.

## Local object bindings and partial shapes

Profile 6 can retain fields returned through a preceding, root-block JavaScript or
TypeScript `const` object binding. The return expression stays unchanged; the
sentence cites both the return and its object initializer. This is a bounded
syntax interpretation, not general alias analysis. Reassignment, shadowing,
mutation, escape, nested capture and direct `eval` withhold the shape hint.
`let`, conditional declarations and factory-return aliases remain unresolved.

Spreads and unknown keys make the field list explicitly partial. Computed,
numeric and escaped keys are withheld; an object-literal `__proto__` setter is
not an own field. A partial list never proves a complete response schema.
Adversarial cases are in `test_js_object_shape.py`.

## Overload bodies and unqualified Java calls

Profile 7 retains the unique TypeScript implementation body when preceding overload
signatures have no bodies. Each signature stays a separate interface declaration;
it does not borrow the implementation's graph identity. Unrelated interface signatures
with the same name do not acquire a body mapping. Ambiguous declarations remain
unresolved rather than choosing an overload by argument types.

Explicit unqualified Java method invocations such as `remove(key)` can now supply
a nine-name possible-call candidate, with local conditions and source evidence.
They do not prove dispatch, execution, mutation or persistence. Bare Python and
JavaScript calls retain their previous narrower classification. See
`test_overload_body_mapping.py` for overload, interface, guard and unreachable-call
negatives. This method change requests review of affected saved interpretations.

Profile 10 also retains explicit per-entry selection/exclusion reasons. Conventional
Python protocol methods are eligible; an ordinary private-name exclusion is not
a negative finding. Java nested owner chains, enum constant overrides and implicit
public interface methods are mapped only where a unique syntax body is available.
Profile 3 uses TypeScript/TSX grammar for corresponding expression comparisons and
removes only redundant grouping around the entire expression.


Profile 11 additionally recovers uniquely indexed Python nested callable bodies
and Java class methods with package-private visibility as internal-only summaries.
Their own-body scope is explicit (`lexical-local` / `package-local`); callers,
callees and runtime accessibility are not established. Public/semantic entries
keep priority under the 1,000-entry budget. Private-name exclusions and empty or
unmapped bodies remain outside resolved behavior. This improves entry coverage,
not support for arbitrary loops, dispatch or business intent.


Profile 12 additionally analyzes private-by-convention and explicitly private or
protected callable bodies as `implementation-local` summaries. They consume only
the remaining budget after primary entries, without transitive propagation.
Supported Python conditional function declarations in module/function scopes retain
source context and an unresolved availability/registration warning; a conditional
redefinition prevents an asserted unconditional call binding. Conditional classes,
class-body methods, lambdas and arbitrary dynamic dispatch remain partial.

The body coverage inventory distinguishes missing mappings from inspected bodies
with no admitted facts. Empty methods and assignment-only methods do not acquire
invented returns, effects or requirements. The known external regression now
recovers summaries for 90/90 and 239/244 entries; the other five have explicit
inspected/no-admitted-facts coverage. All selected local return/error/call facts
are retained in that frozen cohort; this does not establish universal coverage.

Patch 1.13.1 propagates conditional declaration context through nested descendants;
indexing a handler inside a conditional factory does not establish its route.
