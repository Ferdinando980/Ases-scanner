"""Evaluate explicit source oracles and write local HTML, Markdown and JSON."""
import argparse
from pathlib import Path
import sys

from ases.accuracy import evaluate_corpus


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=Path(__file__).resolve().parents[1] / "tests/fixture_accuracy/corpus.json")
    parser.add_argument("--out", type=Path, required=True, help="Empty or marked ASES output directory")
    args = parser.parse_args()
    try:
        result = evaluate_corpus(args.corpus, args.out)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Evaluation error: {exc}", file=sys.stderr)
        return 2
    passed = sum(row["passed"] for row in result["cases"].values())
    print(f"{passed}/{len(result['cases'])} cases pass. Report: {args.out / 'report.html'}")
    for name, row in result["families"].items():
        print(f"{name}: TP={row['true_positive']} FP={row['false_positive']} FN={row['false_negative']} TN={row['true_negative']}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
