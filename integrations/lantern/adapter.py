"""Reference consumer-context adapter — a real, tested starting point, not a frozen sample.

Not imported by ASES core, which has no dependency on any consumer. This file is for a
Python-side tool that wants a smaller, task-shaped view of consumer-context.json.
Kept honest and current by runtime/tests/test_lantern_adapter.py, which runs it against a
real ASES scan, not a hand-written fixture that can drift from the real schema.

Usage: python adapter.py <consumer-context.json> <output.json>
"""
from __future__ import annotations
import json, sys
from pathlib import Path

# Schemas this adapter knows how to read. An older/newer schema it doesn't recognise
# still produces output (every field defaults to empty/None rather than raising), but the
# caller can check `source_schema_supported` instead of silently trusting stale field names.
SUPPORTED_SCHEMAS = {"ases-consumer-context/1.3", "ases-consumer-context/1.4", "ases-consumer-context/1.5"}

def adapt(generic_context: dict) -> dict:
    g = generic_context.get
    return {
        "schema": "lantern-semantic-context/2",
        "source_schema": g("schema"),
        "source_schema_supported": g("schema") in SUPPORTED_SCHEMAS,
        "source_ases_version": g("ases_version"),
        "source_generated_at": g("generated_at"),
        "project": g("project", {}),
        "attack_surface": {
            "behaviors": g("behaviors", []),
            "trust_boundaries": g("trust_boundaries", []),
            "assets": g("assets", []),
            # Present from schema 1.4+ / 1.5+ respectively; [] on an older source, same as
            # every other field here — never an error, just less to work with.
            "data_stores": g("data_stores", []),
            "external_systems": g("external_systems", []),
        },
        "observed_controls": g("controls", []),
        "sessions": g("sessions", []),
        "assumptions": g("assumptions", []),
        "trace_links": g("trace_links", []),
        "uncertainty": {
            "conflicts": g("conflicts", []),
            "unknowns": g("unknowns", []),
        }
    }

def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 1
    src, out = Path(argv[1]), Path(argv[2])
    out.write_text(json.dumps(adapt(json.loads(src.read_text(encoding="utf-8"))), indent=2), encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
