<p align="center">🔎</p>

<h1 align="center">ASES</h1>

<p align="center">Architecture &amp; Software Evidence Scanner<br/>Build with a method. Understand with evidence.</p>

<p align="center"><b>English</b> · <a href="README.it.md">Italiano</a></p>

## Why I built it

Some projects begin with an idea and no code. Others arrive with plenty of code and a README last seen alive three refactors ago. I wanted a useful way to work from either end.

ASES combines a **software engineering toolkit** with a **Python scanner for understanding existing software**. The kit gives coding assistants a method for requirements, design, implementation, tests and maintained documentation. The scanner works back from source code to supported structure, relationships and documentation, keeping the evidence attached. It runs locally without an LLM or an API key.

They belong together: understand what exists, decide what should change, implement it, and check that code, tests and documentation still agree. Preferably without introducing a Strategy Factory Manager to fix a two-line conditional.

## Two parts, three starting points

| Starting point | What ASES provides | How it works |
|---|---|---|
| New project | Requirements, scenarios, design decisions, test oracles and traceability | An agent follows the engineering standard, selected skills and templates |
| Existing project with documentation | Change-impact analysis, consistency checks and updates to affected artifacts | The agent checks implementation and documentation before changing either |
| Existing project with missing or stale documentation | Source inventory, structural evidence, recovered models and documentation | The scanner builds a baseline; the agent reviews uncertainties and uses the recovered material |

**The engineering kit and the scanner have different jobs.** The kit consists of instructions, gates, skills, adapters and templates. The scanner is executable software. Installing the Python package installs the scanner; using the method also requires configuring the agent with the kit. The package does not independently interview stakeholders or implement an application from a sentence.

## Develop with the engineering kit

The workflow is:

```text
intent → requirements → analysis → system design → object design
       → implementation → tests → results and traceability
```

[STANDARD.md](STANDARD.md) defines the method; [the router](orchestrator/TASK-ROUTER.md) chooses the relevant procedures and level of rigor. A small fix can stay `LEAN`; a meaningful feature uses `STANDARD`; architectural or security-sensitive work can require `FORMAL` artifacts. Documentation changes according to impact, rather than growing a new appendix whenever someone renames a variable.

The kit includes:

- requirement validation, impact analysis and consistency review;
- system/object design, reuse decisions and API contracts;
- a Simplicity Gate before considering patterns or abstractions;
- test design with explicit expected results, regression checks and incident reporting;
- bidirectional links from requirements and decisions to code, tests and results;
- templates for SOW, RAD, SDD, ODD, design decisions and TP/TCS/TIR/TSR test documents;
- instruction adapters for several coding assistants.

The methodology draws on university software engineering material, with its sources and their roles recorded in [the source map](sources/SOURCE-MAP.md). Templates provide structure; they do not make an empty document useful by themselves.

To adopt it, place the kit in the target project's `.ases` directory and merge the appropriate adapter into the agent's existing instructions. Keep existing project instructions. The [engineering guide](docs/ENGINEERING-WORKFLOW.md) lists the files, setup and a concrete example. The legacy `scripts/ases.py` companion offers classification hints and file-presence checks; the agent remains responsible for reasoning.

## Understand existing code with the scanner

[![Scanner pipeline: classify source roles, extract syntax, reconstruct static relations, explain findings and compare snapshots.](docs/images/ases-pipeline.png)](docs/images/ases-pipeline.svg)

The scanner separates owned source and tests from generated, vendored, tooling and documentation files. It extracts facts, builds a graph, reconstructs supported relationships and exports readable documents plus tool-neutral data. Source code, imports and build scripts are read as data; the target application is never executed.

You can use it to:

- inventory modules, classes, functions, interfaces, persistence and test declarations;
- recover supported routes, handlers, calls and bounded entry-to-boundary paths;
- inspect local control/session signals and static test links;
- review observed architecture, patterns, conformance and justified refactoring candidates;
- inspect frontend components, templates, services, literal requests and supported frontend/backend matches;
- generate a documented baseline and compare later snapshots without treating line movement as a new application.

| Area | Current extraction | Practical boundary |
|---|---|---|
| JavaScript / TypeScript | Inert Tree-sitter parsing for `.js/.jsx/.mjs/.cjs/.ts/.tsx/.mts/.cts`; lexical bindings, literal modules, re-exports, CommonJS forms, callbacks and selected Express/NestJS constructs | Compiler aliases, computed dispatch and higher-order behavior remain incomplete |
| Python | AST declarations, imports, heuristic call links, selected web decorators and ORM hints | Call resolution is partial; it does not implement Python's runtime binding semantics |
| Java | Heuristic type/member/dependency extraction and selected Spring-like annotations | It is not a Java compiler; servlet route mappings and overload dispatch are not comprehensively reconstructed |
| Frontend | Selected Angular/React-style structure, templates, typed Angular HTTP clients, admitted imported clients, ambient fetch and literal HTML forms | Template grammars are partial; embedded Vue/Svelte scripts and runtime rendering are not exhaustively parsed |
| Other inventoried languages | File/source-role inventory where recognized | Inventory does not imply a structural parser exists |

Imports establish candidates. Static calls establish reconstructed use. Neither establishes network traffic. An `HttpClient` wrapper is not automatically a design-pattern emergency.

## Findings with their reasoning attached

[![Illustrative ASES finding with evidence, counter-evidence, source role, confidence and scoped interpretation.](docs/images/ases-output.png)](docs/images/ases-output.svg)

Results preserve evidence, counter-evidence, assumptions, categorical confidence and limitations. Finding states distinguish `OBSERVED`, `INFERRED`, `OPPORTUNITY`, `HINT`, `UNKNOWN`, `CONTRADICTED` and `SUPPRESSED`. Evidence states are a separate vocabulary. Public static relations and paths remain inferred, even when the supporting syntax is directly observed.

A class called `Factory` earns no design-pattern medal for showing up. A test link does not establish that the test ran or passed. A detected control does not establish effective protection. Conformance rules follow architecture first observed in that project; they do not impose a universal preferred architecture.

Entity identity, finding fingerprint, observation identity and snapshot identity serve different purposes. Harmless formatting can change locations and source hashes without changing meaning. Absence needs comparable scope and the relevant analysis method; a missing result is not automatically a resolved finding.

## Run a source scan

From the repository root, with Python 3.11 or newer in an active virtual environment:

```sh
python -m pip install -e ./runtime
ases --version

ases scan /path/to/project --out current.ases
ases scan https://github.com/OWNER/REPOSITORY --out remote.ases
```

For a new environment, use `python -m venv .venv`, then activate it with `.\.venv\Scripts\Activate.ps1` in PowerShell or `source .venv/bin/activate` on macOS/Linux. If PowerShell activation is unavailable, use `.\.venv\Scripts\python.exe -m pip install -e ./runtime` and `.\.venv\Scripts\ases.exe` directly. Git is required for repository URLs; local scans do not need it. Scanning does not require the development/test dependencies. See [TESTING.md](TESTING.md) to run ASES's own checks.

Choose the source scope deliberately. ASES honors its documented exclusions and `.asesignore`; it does not automatically interpret every project's Git-ignored local directory as generated code. Local experiments and temporary fixtures may need explicit exclusion.

Read the results in this order:

1. Open `current.ases/docs/SUMMARY.md` for the review summary, then `SYSTEM-OVERVIEW.md` for the structure.
2. Read `current.ases/docs/QUALITY.md` and the unknowns before judging what is missing.
3. Inspect the relevant finding in `scanner-findings.json` or `docs/ODD.md`, including evidence, assumptions and confidence; check the referenced source.
4. Use the queries below to follow a route or symbol. Run the project's own tests separately before deciding what to change.

Query the saved snapshot:

```sh
ases inspect current.ases
ases inspect current.ases --collection analysis_unknowns --limit 20
ases inspect current.ases --collection entities --select read --limit 20
ases trace current.ases "GET /users" --direction forward
ases trace current.ases read --direction backward
ases semantic-diff previous.ases current.ases
ases scan /path/to/project --out next.ases --baseline current.ases
```

Queries read saved evidence without silently rescanning mutable source. Exact ID/name/path matching reports ambiguity. Response pagination is distinct from source-analysis coverage. Canonical `entities` include declarations beyond the smaller legacy `components` projection; those counts are not interchangeable.

## What comes back

A source scan writes:

| Output | Purpose |
|---|---|
| `docs/SUMMARY.md`, `SYSTEM-OVERVIEW.md` | Review guide and recovered system overview |
| `docs/RAD.md`, `SDD.md`, `ODD.md` | Behavior, architecture and object-design reconstruction from implementation evidence |
| `docs/TESTING.md`, `TRACEABILITY.yaml`, `CONTROLS.yaml`, `QUALITY.md` | Recovered test baseline, links, control observations and quality/coverage limits |
| `semantic-model.yaml`, `manifest.json`, `validation.json` | Semantic model, source/profile fingerprint and consistency checks |
| `scanner-findings.json` | Normalized findings, hints and suppressed results, feed **1.3** |
| `consumer-context.json` | Legacy consumer context **1.5** |
| `consumer-context.v2.json` | Structural snapshot **2.0**: entities, observations, normalized relations, identity mappings, hashes and scoped coverage |
| `fact-graph.json` | Internal investigation data; downstream tools can use the public contracts |

Recovered RAD/SDD/ODD describe observed or inferred implementation. They cannot recover an undocumented stakeholder decision by sheer confidence. Documents created through the engineering workflow can instead record requirements and decisions explicitly supplied and reviewed during development.

### How to interpret the result

| What you see | What it means | What to check next |
|---|---|---|
| `validation: PASS` | The generated model passes its consistency/schema checks | It does not establish complete extraction or a correct application |
| `OBSERVED` / `INFERRED` | A supported source observation / a reconstruction based on observations | Inspect evidence and assumptions; a static call is not proof of execution |
| `OPPORTUNITY` / `HINT` | A refactoring candidate / a weak lead | Confirm the design problem before changing code; neither is a verdict |
| `CONTRADICTED` | A declared rule conflicts with recovered evidence | Check that the rule, evidence and affected scope match the current project |
| `PARTIAL` / `UNKNOWN` | The relevant method is incomplete or cannot answer within this scope | Missing output is not proof of absence; coverage is separate from confidence |
| `SUPPRESSED` | A result was withheld by the rule's qualification/suppression policy | Review the recorded reason rather than treating it as a confirmed finding |
| `library_call` / `external_api_call` | An imported-library call / an admitted static API-client candidate | Neither proves network traffic; an unrecognized client's remote effects remain unresolved |
| A removed item in a diff | The item is no longer recovered in the second snapshot | Confirm comparable profiles and coverage; read `uncertain` before calling it resolved |

Confidence is categorical (`low`, `medium`, `high`), not a calibrated probability. Counts of recovered tests are declarations and links, not a test run or code-coverage report. A page that says PASS can still deserve a very close look.

### Where the files go

`--out` selects a persistent result directory. Without it, a local source scan uses `.ases`; if that directory already contains the engineering kit or other unrecognized material, the result goes to `ases-scan.ases`. The installed method is preserved. Explicit nonempty, unrecognized output directories are refused.

For a repository URL, the default persistent output is `<repository-name>.ases` in the current directory. The checkout is temporary and cleaned after scanning; the report is retained so you can inspect it. Prefer an explicit `--out` when comparing runs. Do not use the same output directory for the baseline and the new scan: an existing recognized output is replaced.

Generated outputs carry `.ases-output`. Repeated scans replace recognized generated output; cleanup requires that marker and refuses engineering kits or repository roots. A directory merely ending in `.ases` is not permission to delete it.

```sh
ases clean current.ases
ases clean --all
```

`--all` applies to recognized direct output directories in the current folder. Keep persistent results when they are useful baselines; use a temporary directory for disposable experiments. A benchmark should leave measurements, not an archaeological layer in the projects folder.

## Sites, supplied artifacts and imported observations

```sh
ases scan-site https://example.org --max-pages 5
ases scan-artifact supplied-dist --out artifact.ases
ases reconcile-artifact current.ases artifact.ases/artifact-snapshot.json
ases export current.ases --schema 2.0 --out context-v2.json
```

Site mode samples public same-origin HTML, respects `robots.txt`, and records pages, forms, script references and framework hints. It does not execute JavaScript or submit forms; source architecture and client-rendered behavior remain unobserved.

Artifact mode reads supplied local JS bundles, source maps and selected manifest fields within explicit file/byte/node bounds. Reconciliation distinguishes exact bytes, source-map assertions, ambiguity, mismatch and unknown correspondence. Optional runtime input must already come from an external collector. ASES does not run builds, acquire runtime observations, fetch missing maps, decode arbitrary transformed-symbol equivalence or infer deployment truth. A loaded script is not an executed feature.

## Independent from its consumers

ASES supplies generic engineering procedures and structural evidence. Other tools can consume that evidence for documentation, maintenance, cybersecurity and assurance alongside other sources. Risk, compliance, organizational priorities and final control-effectiveness judgments belong to the consumer. ASES works independently and does not require a consumer's internal model or a raw-graph reader.

## Validation and current state

Runtime **1.9.0**, engineering standard **0.3**. The latest verified Windows/Python 3.14.7 suite has **241 passed, 1 skipped**; the skipped case needs symbolic-link permissions. The [accuracy benchmark](docs/ACCURACY.md) covers 16 synthetic cases with 39 explicit labels and writes inspectable HTML, Markdown and JSON. All 16 cases and position-change checks pass. Independent label review is pending; this is a regression corpus, not an accuracy estimate for arbitrary repositories.

Start with the [engineering guide](docs/ENGINEERING-WORKFLOW.md) for development, the [CLI guide](runtime/README.md) for scanner commands, and [TESTING.md](TESTING.md) to reproduce the checks. [Evidence terminology](EPISTEMOLOGY.md), [pattern rules](PATTERN-RULES.md) and [consumer contracts](integrations/CONSUMER-CONTRACT.md) explain interpretation and integration. Dynamic dispatch, global middleware, servlet routes, custom clients/event buses and runtime execution remain method-specific limits. Zero speculative opportunities is a valid result.

## License

Copyright © 2026 Ferdinando Gregorio Fernandez. All rights reserved. Source is visible for portfolio evaluation; reuse, redistribution and derivative works are not permitted. See [LICENSE](LICENSE). Dependencies retain their terms in [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
