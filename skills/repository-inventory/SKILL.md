---
name: repository-inventory
description: Build a minimal, evidence-based inventory of an existing codebase before reverse engineering.
---

# Repository Inventory

## Trigger
Use when entering a brownfield codebase, especially when documentation is missing or unreliable.

## Procedure
1. Identify languages, frameworks, package/build managers.
2. Find executable/public entry points.
3. Identify first-party modules/packages.
4. Separate generated/vendor/build artifacts.
5. Find configuration, schemas, migrations, data stores.
6. Find external integrations.
7. Find tests and documentation.
8. Record only architecture-relevant dependencies.

## Output
`inventory.yaml` with evidence paths.

## Stop condition
Stop once system boundaries are clear enough for recovery. Do not enumerate files for its own sake.
