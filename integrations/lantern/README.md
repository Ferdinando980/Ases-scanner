# Reference Consumer Adapter

ASES does not depend on any consumer.

**What this actually is today**: `adapter.py` is a tested reference implementation showing how
to read `consumer-context.json` (currently schema `ases-consumer-context/1.5`, see
`../CONSUMER-CONTRACT.md`) into a smaller, task-shaped view, in Python. This file is useful as
a starting point for a Python-side consumer, or as a worked example of the field names and the
tolerant-on-an-unknown-schema pattern (`source_schema_supported`) a real integration should use.

It is kept accurate by `runtime/tests/test_lantern_adapter.py`, which runs it against a real
ASES scan output, not a hand-written fixture — if the consumer-context contract changes shape,
that test fails instead of this file silently going stale.

Recommended flow for building a new consumer on top of it:

```text
repository
  ↓
ASES
  ↓
consumer-context.json (ases-consumer-context/1.5)
  ↓
your adapter (start from adapter.adapt() here)
  ↓
security hypotheses / scanner correlation / verification
```

Fields currently reshaped by `adapt()`: `project`, `behaviors`, `trust_boundaries`, `assets`,
`data_stores`, `external_systems`, `controls`, `sessions`, `assumptions`, `trace_links`,
`conflicts`, `unknowns`, plus the source's own `schema`/`ases_version`/`generated_at` so a
consumer can reason about freshness without re-deriving it.

A consumer should preserve ASES provenance and keep separate:
`observed fact → inference → security hypothesis → verified finding`.

This adapter is optional and external to the ASES core.
