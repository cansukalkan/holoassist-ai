"""Run the bounded Supervisor prototype from a validated local JSON request."""

import argparse
import json
import sys
from pathlib import Path

from holoassist.agents.supervisor import run_analysis
from holoassist.contracts.analysis import AnalysisRequest
from holoassist.rag.store import ChromaKnowledgeStore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--db", type=Path, default=Path("data/demo-chroma"))
    args = parser.parse_args()
    try:
        with args.request.open("rb") as source:
            raw = source.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("request exceeds 1 MiB")
        request = AnalysisRequest.model_validate_json(raw.decode("utf-8-sig"))
        source_kind = "synthetic" if request.mode == "demo" else "manufacturer"
        store = ChromaKnowledgeStore(args.db, source_kind=source_kind)
        result = run_analysis(request, store)
    except (ValueError, OSError):
        print("Analysis request rejected: invalid_request_or_unavailable_data", file=sys.stderr)
        return 2
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
