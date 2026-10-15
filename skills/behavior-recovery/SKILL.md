---
name: behavior-recovery
description: Reconstruct externally meaningful software behavior by tracing real flows through code, configuration, and tests.
---

# Behavior Recovery

Start from externally meaningful triggers:
HTTP/RPC endpoint, UI action, CLI command, event/message, scheduled job, public library API.

Trace:
trigger → validation → orchestration → domain behavior → persistence/external side effect → output/error.

Do not generate one use case per function.
