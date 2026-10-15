"""Run the deterministic ASES rule-quality corpus without external repositories."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from ases.pipeline import scan_project
from ases.quality_eval import evaluate_case, summarize


def main() -> None:
    corpus = Path(__file__).resolve().parents[1] / "tests" / "fixture_quality"
    oracle = json.loads((corpus / "oracle.json").read_text(encoding="utf-8"))
    results = {}
    with TemporaryDirectory(prefix="ases-quality-") as tmp:
        for name, labels in oracle["cases"].items():
            model = scan_project(corpus / name, Path(tmp) / f"{name}.ases")["semantic_model"]
            results[name] = evaluate_case(model, labels)
    summary = summarize(results)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if summary["false_negative"] or summary["false_positive"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
