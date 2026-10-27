# Working with the ASES engineering kit

ASES has an executable scanner and an agent-guided engineering method. The Python package installs the scanner. The method is configured separately from the files in this repository; an agent applies it to the project's actual requirements and implementation.

This guide documents the author's workflow and authorized use. Permissions remain those in [LICENSE](../LICENSE).

## Configure the project

Use an empty `.ases` directory for the kit. If it already holds scanner results, preserve or explicitly clean those results first; do not merge the kit into generated output.

Copy these files and directories from the ASES checkout:

```text
your-project/
├── AGENTS.md                 # merge the appropriate adapter into existing instructions
└── .ases/
    ├── AGENTS.md
    ├── STANDARD.md
    ├── GATES.md
    ├── orchestrator/
    ├── skills/
    ├── templates/
    ├── schemas/
    └── scripts/
```

The root agent instructions should reference `.ases/AGENTS.md`. Adapters are available in `adapters/`; preserve the target project's existing instructions and constraints. The templates and example traceability records need project-specific content before they represent real requirements or design decisions.

The helper can check that the method's required files are present:

```sh
python .ases/scripts/ases.py check .
python .ases/scripts/ases.py classify "Add a second notification provider"
```

`classify` is a deterministic English-keyword hint, and `check` checks files and review markers. Neither validates requirements, proves design consistency or substitutes for the agent's review.

## Start from the project's actual state

For a new system, work from intention through requirements, analysis, system design, object design, implementation and tests. For a documented system, inspect the implementation and assess document freshness before changing anything. For an undocumented system, recover a baseline from code and keep inferred behavior separate from stakeholder-approved requirements.

For example, give the agent this task:

> Follow the ASES instructions in this project. Add a second notification provider. First inspect the existing implementation and tests, clarify the required observable behavior, identify affected artifacts, and compare a direct solution with any proposed abstraction. Implement the smallest complete change, verify it and update only the documents and trace links whose meaning changed.

The expected result is a reviewed change, appropriate tests and consistent documentation. Two providers do not automatically require a pattern. A small stable conditional is allowed to remain a small stable conditional.

## Keep design and reconstruction distinct

`templates/RAD.md`, `SDD.md` and `ODD.md` help the agent write requirements and design with explicit decisions. The executable scanner's generated documents describe observed or inferred implementation. They can supply a useful starting point; they do not retroactively approve requirements or recover a decision that was never recorded.

Use `LEAN`, `STANDARD` or `FORMAL` rigor according to the router. The presence of a test-report template is not an obligation to generate one for every typo.

## Combine the kit with the scanner

For an existing repository, a saved scan can help locate components, dependencies, tests and uncertainties before a change. After implementation, a second scan and semantic diff can help review structural consequences. Test execution and requirement acceptance remain separate activities.

```sh
ases scan /path/to/your-project --out before.ases
# Develop and verify the authorized change with the agent.
ases scan /path/to/your-project --out after.ases
ases semantic-diff before.ases after.ases
```

Without `--out`, an installed kit in `.ases` is preserved and scan results go to `ases-scan.ases`. Explicit nonempty, unrecognized destinations are refused. Generated output carries `.ases-output`; `ases clean` removes recognized output and refuses engineering kits. Keep useful baselines, and place disposable trials in a temporary directory with cleanup managed by the calling script.
