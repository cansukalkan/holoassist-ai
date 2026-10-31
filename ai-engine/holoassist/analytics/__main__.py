"""Analyze a JSON ObservationSeries: python -m holoassist.analytics --series file.json."""

import argparse
import json
import sys
from pathlib import Path

from holoassist.analytics.series import analyze_series


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--series", type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.series.open("rb") as source:
            raw = source.read(5 * 1024 * 1024 + 1)
        if len(raw) > 5 * 1024 * 1024:
            raise ValueError("input exceeds 5 MiB")
        report = analyze_series(json.loads(raw.decode("utf-8-sig")))
    except (ValueError, OSError, TypeError):
        print("Sensor input rejected: invalid_or_unavailable_series", file=sys.stderr)
        return 2
    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
