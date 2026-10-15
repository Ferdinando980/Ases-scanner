# Local rule-quality corpus

These are synthetic repositories with explicit, reviewable oracles in `oracle.json`.
They cover a Spring-style controller → service interface/implementation → repository
interface/implementation chain; a component frontend with an API module and matching
backend route; and generated/vendored-only noise that must not create architecture.

Run `python runtime/tools/evaluate_quality.py` with `runtime` on `PYTHONPATH`.
The command exits nonzero for a labeled false positive or false negative.

Precision and recall here apply **only to the claims labeled in the oracle**, not to
all possible ASES findings or all software architecture. Unlisted findings are
reported as `unassessed_findings`; unsupported concepts are listed separately and
are not counted as absent. A 100% score on this small corpus is a regression signal,
not a general accuracy estimate. Broader language/framework coverage needs more
independently reviewed cases and occasional real-project validation.
