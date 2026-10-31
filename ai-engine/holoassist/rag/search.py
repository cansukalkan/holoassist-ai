"""Local retrieval CLI: `python -m holoassist.rag.search --help`."""

import argparse
import json
import sys
from pathlib import Path

from holoassist.rag.chunking import MAX_DOCUMENT_BYTES
from holoassist.rag.store import ChromaKnowledgeStore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/chroma"))
    parser.add_argument("--source-kind", choices=["synthetic", "manufacturer"], required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    index = commands.add_parser("index")
    index.add_argument("document", type=Path)
    index.add_argument("--max-chars", type=int, default=1000)
    index.add_argument("--overlap", type=int, default=100)
    query = commands.add_parser("query")
    query.add_argument("text")
    query.add_argument("--equipment-id", required=True)
    query.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    try:
        store = ChromaKnowledgeStore(args.db, source_kind=args.source_kind)
        if args.command == "index":
            with args.document.open("rb") as source:
                raw = source.read(MAX_DOCUMENT_BYTES + 1)
            result = {
                "indexed_chunks": store.index_document(
                    raw, max_chars=args.max_chars, overlap=args.overlap
                ),
                "source_kind": args.source_kind,
            }
        else:
            result = [
                item.model_dump(mode="json")
                for item in store.search(
                    args.text, equipment_id=args.equipment_id, top_k=args.top_k
                )
            ]
    except ImportError:
        print('Install retrieval dependencies: pip install -e ".[rag]"', file=sys.stderr)
        return 2
    except (OSError, ValueError) as error:
        print(f"Retrieval rejected: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
