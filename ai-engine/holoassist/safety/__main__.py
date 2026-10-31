"""Evaluate the independent synthetic instruction-display gate."""

import argparse
import json
import sys
from pathlib import Path

from holoassist.safety.gate import evaluate_plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    args = parser.parse_args()
    try:

        def read(path):
            with path.open("rb") as source:
                raw = source.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError("input exceeds 1 MiB")
            return json.loads(raw.decode("utf-8-sig"))

        report = evaluate_plan(read(args.analysis), read(args.request), read(args.catalog))
    except (OSError, ValueError, TypeError):
        print("Safety input rejected: invalid_or_unavailable_context", file=sys.stderr)
        return 2
    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
