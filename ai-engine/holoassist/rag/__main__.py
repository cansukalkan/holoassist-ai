"""Run `python -m holoassist.rag source.json` to inspect source-preserving chunks."""

import argparse
import json
import sys
from pathlib import Path

from holoassist.rag.chunking import MAX_DOCUMENT_BYTES, chunk_document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    parser.add_argument("--max-chars", type=int, default=1000)
    parser.add_argument("--overlap", type=int, default=100)
    args = parser.parse_args()
    try:
        with args.document.open("rb") as source:
            raw = source.read(MAX_DOCUMENT_BYTES + 1)
        chunks = chunk_document(raw, max_chars=args.max_chars, overlap=args.overlap)
    except (OSError, ValueError) as error:
        print(f"Document rejected: {error}", file=sys.stderr)
        return 2
    print(
        json.dumps([item.model_dump(mode="json") for item in chunks], ensure_ascii=True, indent=2)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
