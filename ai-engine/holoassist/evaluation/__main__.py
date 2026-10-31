"""CLI runner for the reproducible synthetic benchmark suite."""

import argparse
from pathlib import Path

from holoassist.evaluation.benchmark import run_synthetic_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run reproducible offline synthetic benchmark across HoloAssist subsystems."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON file path to write the validated benchmark report.",
    )
    args = parser.parse_args()
    report = run_synthetic_benchmark(Path("."))
    payload = report.model_dump_json(indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()

