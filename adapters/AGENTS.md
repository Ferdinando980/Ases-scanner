# Project Engineering Instructions

Follow `.ases/AGENTS.md` and treat `.ases/STANDARD.md` as the source of truth for engineering behavior.

Before substantial code changes:

1. classify the task using `.ases/orchestrator/TASK-ROUTER.md`;
2. understand the real code path and relevant tests/docs;
3. run the required skills only;
4. run Simplicity Gate before Pattern Gate;
5. update only impacted documentation/traceability;
6. test and audit consistency before completion.

Do not create abstractions, dependencies, patterns, or documents just because a template exists.
