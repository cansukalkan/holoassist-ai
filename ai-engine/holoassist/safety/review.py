"""Local synthetic approval CLI; development identity only, no network authentication."""

import argparse
import getpass
import json
import os
import sqlite3
import sys
from pathlib import Path

from holoassist.safety.storage import approval_store


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/approvals.sqlite3"))
    parser.add_argument("--env-file", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    opening = commands.add_parser("open")
    opening.add_argument("--ttl-seconds", type=int, default=900)
    for name in ("analysis", "request", "catalog"):
        opening.add_argument("--" + name, type=Path, required=True)
    deciding = commands.add_parser("decide")
    deciding.add_argument("approval_id")
    deciding.add_argument("--decision", choices=["approve", "reject"], required=True)
    deciding.add_argument("--expected-digest", required=True)
    for name in ("show", "audit", "inspect"):
        sub = commands.add_parser(name)
        sub.add_argument("approval_id")
    resuming = commands.add_parser("resume-demo")
    resuming.add_argument("approval_id")
    for name in ("analysis", "request", "catalog"):
        resuming.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        reviewers = tuple(
            x.strip() for x in os.environ.get("HOLOASSIST_REVIEWERS", "").split(",") if x.strip()
        )
        store = approval_store(args.db, authorized_reviewers=reviewers, env_file=args.env_file)

        def read(path):
            with path.open("rb") as source:
                raw = source.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError("input_too_large")
            return json.loads(raw.decode("utf-8-sig"))

        if args.command == "open":
            result = store.open_review(
                read(args.analysis),
                read(args.request),
                read(args.catalog),
                ttl_seconds=args.ttl_seconds,
            )
        elif args.command == "decide":
            result = store.decide(
                args.approval_id,
                authenticated_reviewer=getpass.getuser(),
                decision=args.decision,
                expected_context_digest=args.expected_digest,
            )
        elif args.command == "resume-demo":
            result = store.resume_demo(
                args.approval_id, read(args.analysis), read(args.request), read(args.catalog)
            )
        elif args.command == "inspect":
            result = store.review_context(
                args.approval_id, authenticated_reviewer=getpass.getuser()
            )
        elif args.command == "audit":
            result = store.audit(args.approval_id)
        else:
            result = store.get(args.approval_id)
        if hasattr(result, "model_dump"):
            result = result.model_dump(mode="json")
    except (ValueError, OSError, sqlite3.Error, TypeError):
        print("Approval operation rejected: invalid_context_identity_or_state", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
