from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Dict, List

from annotraq.core import DEFAULT_WEIGHTS, DatasetError, evaluate, validate_items
from annotraq.io import load_jsonl, write_json
from annotraq.reporting import write_html


def _weights(value: str) -> Dict[str, float]:
    result: Dict[str, float] = {}
    try:
        for entry in value.split(","):
            name, number = entry.split("=", 1)
            result[name.strip()] = float(number)
    except (ValueError, TypeError) as error:
        raise argparse.ArgumentTypeError("use name=value pairs separated by commas") from error
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="annotraq",
        description="Benchmark AI-generated data annotations against adjudicated references.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate a JSONL dataset")
    validate_parser.add_argument("dataset", type=Path)

    evaluate_parser = subparsers.add_parser("evaluate", help="score a JSONL dataset")
    evaluate_parser.add_argument("dataset", type=Path)
    evaluate_parser.add_argument("--json", type=Path, default=Path("annotraq-report.json"), help="JSON report path")
    evaluate_parser.add_argument("--html", type=Path, default=Path("annotraq-report.html"), help="HTML report path")
    evaluate_parser.add_argument("--bootstrap", type=int, default=1000, help="bootstrap rounds for the confidence interval")
    evaluate_parser.add_argument("--seed", type=int, default=42, help="random seed for reproducible intervals")
    evaluate_parser.add_argument(
        "--weights",
        type=_weights,
        default=dict(DEFAULT_WEIGHTS),
        help="comma-separated weights that add to 1 (accuracy=.6,completeness=.2,consistency=.1,format_validity=.1)",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        items = load_jsonl(args.dataset)
        if args.command == "validate":
            validate_items(items)
            print(f"Valid dataset: {len(items)} records")
            return 0

        report = evaluate(items, weights=args.weights, bootstrap_rounds=args.bootstrap, seed=args.seed)
        write_json(args.json, report)
        write_html(args.html, report, title=f"Benchmark report for {args.dataset.name}")
        summary = report["summary"]
        low, high = summary["confidence_interval_95"]
        print(f"AnnotraQ score: {summary['overall_score']:.2f}/100 (grade {summary['grade']})")
        print(f"95% confidence interval: {low:.2f}–{high:.2f}")
        print(f"JSON report: {args.json}")
        print(f"HTML report: {args.html}")
        return 0
    except DatasetError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
