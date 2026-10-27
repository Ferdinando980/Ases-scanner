# Engineering documents: contract 1.0

The optional `engineering-model.json` sidecar uses `ases-engineering-model/1.0`.
Existing 1.5 context, 1.3 findings and 2.0 evidence contracts retain their authority,
identity and absence rules. Documents never enter their source-syntax observations.

An engineering record has an identity, authority and immutable source locations:
relative path, SHA-256, and page, sheet/cell, line or XML element. Original IDs are
preserved. Multiple occurrences remain separate evidence, grouped by declared ID;
different declarations remain visible. A content hash groups byte-identical copies;
it does not prove independent corroboration. Versions and approval are declarations.

Source extraction is `complete`, `partial`, `unsupported` or `failed`; interpretation
is `partial` or `not-run`. Complete extraction means the supported textual/cell
representation was read within limits. It never means every diagram, sentence,
formula or implication was understood. Formula text and cached values are separate.
Macros, scripts, target builds and target tests are never executed.

Requirements are documented needs, code entries are observed syntax, inferred
links are candidates, imported results are historical and reviews are explicit
user confirmations. Neither priority, an assertion nor a report copy proves that
a requirement is implemented. A branch guard is not an invariant. No declared type
means undeclared, not an inferred type presented as fact.

Document method `inert-documents/9` also reads explicitly typed HTML requirement
rows with UID/statement fields and bounded formal heading/obligation blocks.
These records preserve original IDs and may have `kind: unspecified`; consumers
must retain that value rather than treating the record as absent. Legacy readers
retain their existing classification rules. Original `fields.title` and
`fields.status` are declarations, never satisfaction or execution evidence. A typed
UID without a statement remains a partial record with an explicit issue.

`declared-document-reference` links retain `native_role`, `href` and source
locations. Resolution checks an exact declared UID and local document path;
external URLs and alternate document representations remain unresolved. A readable
record with that UID may still be opened for comparison. The engineering schema
stays 1.0; comparison exposes the method change. Consumer feeds remain unchanged.

`recovered_requirements` is a separate collection of **sentences interpreted from
implementation**, not an ID extraction pass. It starts at supported HTTP handlers
or public library callables, reads branch/return/throw/call syntax and follows
unambiguous static links up to four calls and 40 entities. Python uses AST, JS/TS
uses the existing Tree-sitter grammar, Java uses bounded body recovery. Anonymous
Java classes/lambdas, dynamic dispatch, exception joins and external effects remain
explicitly partial. Up to 1,000 entry points and 50,000 body facts are interpreted.
Inner-helper results are kept separate from outward results. A method called
`save` is a possible effect call, not proof of database persistence. Reconstructed
sentences, branch conditions, outcomes, source locations and proposed characterization
tests remain linked. Proposed tests are neither independent oracles nor executions.
Reviews can confirm/reject an interpretation without changing its original authority.

Behavior method `branch-local-flow/12` retains early-exit fallthrough conditions,
stops unreachable syntax, handles conditional return expressions and short-circuit
calls, and suppresses exits overridden by an unconditional `finally` exit. Supported
HTTP handler response-parameter calls can produce outcomes without a JS return;
rebound/shadowed parameters are not trusted as response bindings. Local declared
catch matching is partial and never a proof of runtime name binding. Loop joins,
conditional finally overrides, comprehensions and exception dispatch remain partial.
Each body is bounded to 500 facts and 64 live paths; reached limits appear explicitly.
For interpreted Python/JS bodies, linked helper evidence must match a retained call
fact; the broader structural graph cannot reintroduce a call after an early exit.
The sidecar records its behavior profile; document comparison exposes a profile
change. Stable evidence ordering avoids spurious review conflicts between processes.

Version 3 adds inert AST-based Java body interpretation for uniquely located methods,
including if/else paths, early exits, ternary returns and short-circuit calls. It does
not borrow a following body for an abstract declaration. Nested callable/class bodies
are excluded from outer exits. Java compound joins (loops, switch, try/catch/finally,
synchronization, assertions and labelled statements) remain unresolved: inner exits
are withheld and later continuation is explicitly partial. Structural Java declarations
and bindings remain heuristic; comments cannot create type owners. See the
[capability table](FLOW-COVERAGE.md) for admitted scope and measured examples.
`behavior_parser_profiles.java` records grammar and limits; comparison exposes both
behavior and parser changes and requests document review, including with unchanged
source records. This additive engineering metadata does not change consumer feeds.

The document evaluator accepts optional closed `behaviors` oracles with entry selectors,
rationale, and explicit expected outcome/error/effect claims. It scores local entry-body
claims separately from IDs and lists transitive claims outside that oracle. Predicate
normalization handles parentheses and double negation only; it is not an equivalence
solver. Baseline failures, false claims, omissions and zero positive denominators remain
visible in HTML/Markdown/JSON. Independent label review is a separate status.

Generated Javadoc and JaCoCo can be read as documentation/report sources without
making their generated files production-code evidence. Excel result rows retain
their declared outcome, sheet, date, missing environment/revision and raw values.
Checklist answers and formula caches remain self-reports, not quality verdicts.

Bounds: 32 MiB per input, 128 MiB total inputs, 1,000 PDF pages per input,
250,000 populated workbook cells; ZIP expansion 128 MiB. Inputs are processed
independently. Limits and missing optional readers remain visible in coverage.
The desk retains its worker cancellation and deadline. CLI progress callbacks
can interrupt extraction at page, sheet, XML or source boundaries.

`ases documents SNAPSHOT --out PACKAGE [--review REVIEW.json] [--language it|en]`
uses the saved engineering model, never the target. It refuses unrecognized output
and detects edits to generated files before replacing them. Reviews accept 1.0
annotations and `ases-engineering-review/1.1` authoring. Version 1.1 requires a base
model digest; operations can retain their individual base digest. Context and
annotations use the expected record digest. Conflicts retain the original data and
review. Exports include the review; the packaged review schema describes both versions.

`controlled-narrative/5` retains bounded Italian explanations before code evidence,
retaining inspectable clause-to-fact IDs. It explains simple comparisons, field access,
literal result fields, explicit errors and named possible calls. Identifier labels
do not establish business purpose. Literal field values are withheld for duplicate,
computed or expanded keys that could change the result. Unknown expressions are
explicitly marked as untranslated, with their original syntax retained in saved facts.
Python AST is used only for Python; JS/Java use their own grammar, not Python precedence.
The English wording retains the existing technical expressions. The desk displays
Italian clauses directly and puts original expressions/source navigation behind
evidence details; document code blocks are collapsed in the desk reader.
Generated condition negations retain a separate predicate descriptor; a JS function
named `not` is not a logical negation. Original expressions stay intact. Partial paths,
helper scope and omitted display claims remain explicit. This does not measure
general readability or recover stakeholder intent.

`stdlib-dispatch/2` recognizes imported Python `http.server` handlers, including
factory-local classes, and unmutated literal exact-match dispatch tables of local
functions. A supported request-path lookup must be connected to invocation of its
selected callable. Registry mutation/escape, shadowed bindings, fixed-key lookups,
unused tables and dynamic registration are withheld or remain partial.
Ordered literal `(prefix, local_handler)` lists/tuples are also recovered when a
supported lookup helper returns that candidate under `request_path.startswith(prefix)`.
Prefix declarations use a `*` suffix and carry `match_kind`, `path_prefix` and
separate route scope; they do not assert an exact URL or effective reachability.
Overlapping prefixes, exact-match precedence and request guards can shadow a candidate.
Routes and their call links are inferred static mappings, not observed requests.
Only a locally evidenced JSON-serialization/HTTP-write wrapper can add Python
response outcomes; its name alone cannot. Literal HTTP statuses are explained with
source references. Entry declaration locations remain separate from body evidence.
For this stdlib dispatch, a callable's Python return value is internal control flow,
not an HTTP response body; it remains in `returns` and does not become an external outcome.

`entry-selection/1` preserves the HTTP-handler view when recognized routes exist.
For library fallback over the 1,000-entry budget, application paths precede declared
auxiliary benchmark/example/script/work/research directories, with round-robin
allocation across files. This selection does not exclude files from the inventory
or prove business importance. Unselected API declarations remain inspectable; this
is not a claim of complete feature coverage. Method changes remain visible in diff.
The independent 50,000 body-fact budget is also allocated to HTTP entry files first,
then linked files, remaining application files and auxiliary trees. Primary handler
bodies precede other declarations in their file. A body that does not fit the remaining
budget is omitted with coverage recorded; its facts are not silently sliced.

New scans record the new narrative method. Older snapshots keep their saved wording;
reopening them does not silently rewrite interpretations. A rescan can change record
digests and review support even when source facts are unchanged. Original evidence,
consumer feeds and satisfaction states remain separate from the presentation change.

`operations` is an optional view grouped only by identical explicit handler sets.
Shared helpers do not merge different operations. Supported steps retain source
scope, not a guaranteed global call sequence. Context is a user overlay. Explicit
add/adopt actions materialize `user_requirements` separately from original declarations:
author, scope, acceptance criterion, human authority and unverified satisfaction.
Adopted needs survive a changed/missing candidate with support needing review.
The immutable base model and review must be retained together; authored records
are materialized by the reviewed view and rendered RAD. Document diff loads both.

Design: direct extraction/model/render/review modules reuse the fact graph and
desk. Native XML/ZIP/AST/HTML parsers handle inert formats; PDF is an optional
dependency. No pattern framework or second source graph is needed. Section specs
and schema ship in the wheel. Impact: ingestion → model → renderers → CLI/desk;
legacy evidence contracts are verify-only. Synthetic fixtures are redistributable;
external course/project artifacts and private results remain outside this repo.

Quality controls record method and scope: deterministic identity/reference/report checks,
heuristic declaration/interface comparisons, and explicit human review of domain intent,
contract meaning, test partitions, guides and diagram semantics. A missing structured oracle
is a reading gap, not proof of an untestable requirement. Javadoc comparison only matches a
unique supported declaration; ambiguous overloads remain unassessed. Regeneration records
hashes of its own generated document files and refuses manual edits, in both CLI and desk.

## Maintained views and method changes

`inert-documents/5` additionally recovers bounded Italian/English explicit obligation
sentences without requirement IDs, such as “Il sistema deve…” or “The system shall…”.
Original words and source locations are retained. Content keys are generated with
`declared_id: null`; no identifier is attributed to the author. Classification is
heuristic and satisfaction remains unverified. Fenced Markdown examples, example/future
sections, labels, developer commands and optional/descriptive statements are withheld.
Archive-like source paths explicitly leave current release applicability unknown;
identical sentences in separate files are not silently merged as one stakeholder need.
This does not recover arbitrary prose or business intent; multi-line/diagram-only
statements may still be missed. Version 4 and later treat JSON/YAML
as structured input: only the supported `requirements` list is interpreted. Other
dialects remain inventoried with hashes and an explicit unsupported status; raw
experiment/configuration rows are not treated as requirement prose or test results.
Version 3 and later preserve static HTML table cells and recognized requirement
headers independently of surrounding paragraphs. Priority columns do not become
part of requirement statements. Table/row locations are retained without inventing
PDF page numbers; continuation across pages applies to PDF tables only. Nested
HTML layouts remain partial. The populated-cell budget also bounds static tables.

`OVERVIEW.md` and `TRACEABILITY.md` are views of the same saved model as the full
documents. Hashed record anchors connect requirements, API and tests in both
directions. Ambiguous/missing references remain unresolved. Missing-work excerpts
are grouped once per document. Observed frontend/design information and source
declarations of current/proposed design are retained separately.

`record_changes` separates supported content from position/hash movement, signature,
behavior and statement changes. `analysis_scope` records configured scope; source-set
and scope changes are distinct. Relocation matches are review candidates, never an
identity migration or automatic transfer of confirmation. Legacy unknown scope stays
unknown. A missing item is not a resolved item. CLI and desk compare reviewed models.

`explicit-entry-operations/2` includes method/parser profiles in its evidence digest.
Changed support leaves an adopted human need intact with `needs-review`; satisfaction
stays `not-verified`. Document, behavior, narrative, parser and operation method
changes request review of affected sections even when source bytes are unchanged.

The desk's complete ZIP retains the model, review, documents and content manifest.
Its reduced ZIP contains only allowlisted aggregate counts and an omission manifest,
without original text, paths, notes or reopenable evidence. Aggregates are still
information about a project. No automatic sharing occurs. Complete export is bounded
to 128 MiB of input files; exceeding it leaves the completed result available.

### Object-shape and worksheet support

Flow profile 6 emits an `object-shape` fact for an admitted local `const` object
binding. Narrative profile 3 links the return clause to that fact and the return
fact, matching by entity and binding rather than line alone. Same-line bindings
cannot cross-cite. Partial field lists are named explicitly; unsupported alias
or mutation paths do not acquire a shape assertion.

Document profile 3 recognizes explicit ID, statement, actor and priority worksheet
headers, including Italian variants. Header state is separate per sheet; sparse
cell addresses and sheet/row/cell provenance survive. Duplicate columns are not
guessed. Formula caches are not adopted as authored requirement text or priority.
The headerless fallback remains available. These method changes request review
of affected sections; they do not change consumer feed contracts.

Flow profile 7 includes the body-mapping correction for TypeScript overloads and
the Java unqualified-method candidate policy. Bodyless signatures retain their
source interface records without sharing the graph identity of a concrete body.
The correction does not resolve runtime overload selection. Possible-call evidence
remains separate from effective mutation, durable storage and requirement satisfaction.
Consumer feeds and model/review schemas are unchanged; method changes request review.

Native ReqView `.reqw` and ARFF files are read inertly with bounded extraction.
ReqView FR/NFR types are preserved; REQ/custom untyped needs stay unspecified.
ARFF F/FR/RF and NF/NFR/RNF are explicit kinds; opaque taxonomy codes are
retained as `source_kind`, not guessed into author-declared semantics. Generated
ARFF row keys are source-scoped and are not declared IDs. Native attributes and
document positions remain available in the record.

`explicit-prose/2` keeps whole source assertions, distinguishing obligations,
recommendations, described behavior and stated permissions. `classification.origin`
separates declared section types, text heuristics and unknowns. Textual reasons are
inspectable, uncalibrated hints; a sentence in a document is not proof of implementation
or current stakeholder approval. Optional offline GLiNER2 produces separate cited
hypotheses, with memory/token/timeout failures kept visible.


### Historical 1.12 recovery and internal scopes

`inert-documents/9` and `explicit-prose/3` retain literal subjectless strong-modal
obligations and bounded declarative output/rate assertions. `subject_missing`
warns that actor and applicability are unspecified; no subject is invented.
`constraint-signals/2` exposes inspectable textual quality-constraint signals,
including compact units, access restrictions and resource limits. Original declared
types still outrank heuristic suggestions; no score is a calibrated probability.

`branch-local-flow/11` admits uniquely indexed Python nested callables as
`entry_scope=lexical-local`, `entry_visibility=local-callable`. Java class methods
with bodies and implicit package visibility may be `package-local` /
`package-private`. Their summaries cover only their own bodies (depth 0, one
entity), after primary semantic/public entries within the shared 1,000-entry
budget. They do not inherit callers/callees or assert a public ingress. Explicit
semantic entries are not duplicated. Private-name exclusions, missing mappings
and bodies without admitted facts remain explicit limitations.

`explicit-entry-operations/3` preserves these internal scopes and visibilities in
operation views and document/UI explanations. Java `$` type identities and
annotation comments retain declaration positions without erasing route strings.
The optional `requirement_classification_profile` field identifies the heuristic;
consumer feeds and declared satisfaction authority remain unchanged.


### Current 1.13.1 coverage and classification

`branch-local-flow/12`, `entry-selection/2`, `explicit-entry-operations/4` and
`controlled-narrative/6` retain private-by-convention and explicitly private or
protected callables as `implementation-local` own-body summaries, after primary
entries within the shared 1,000-entry budget. Existing lexical-local and
package-local scopes remain. Internal entries use depth zero and one entity;
no caller/callee facts or public accessibility are inferred.

Python function declarations inside module/function control syntax can be indexed
with exact lexical identity and source position. `conditional_declaration` and
`declaration_context` retain source syntax; availability and branch truth stay
unknown. Their nonprivate summaries use `conditional-local`. Conditional
redefinitions do not reuse an unconditional call binding. Ancestor declaration
context is inherited through all indexed callable descendants, including decorators. Route registration
remains unresolved when conditional, even if its function body was indexed.
Conditional class/method declarations, lambdas and arbitrary dispatch are not
made complete by this expansion.

`behavior_coverage.body_evidence_status` distinguishes `body-not-mapped`,
`interpreted-with-admitted-facts` and `interpreted-no-admitted-facts`, with API
entity/positions. An inspected body with no admitted facts creates no synthetic
return, requirement or proof of no effects. Entry selection is reported separately.
Narratives, operations, UI and document-change review preserve internal scope and
conditional availability. A scope/context change requests document review even
when the returned expression is unchanged.

`constraint-signals/3` broadens inspectable quality-constraint forms. Showing a
quality metric is kept distinct from imposing a bound on it. Exact source reasons,
declared-type precedence, unspecified cases and unverified satisfaction remain.
Mixed feature/quality sentences can still disagree with the author's category;
these are review suggestions, not recovered authoritative intent.
