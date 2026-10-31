"""Exercise the localhost development API without displaying credentials or deciding reviews."""

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from dotenv import dotenv_values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, choices=(8001, 8002), default=8001)
    args = parser.parse_args()
    environment = dotenv_values(".env")
    base = f"http://127.0.0.1:{args.port}"

    def call(path, token=None, body=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        request = Request(
            base + path,
            headers=headers,
            data=json.dumps(body).encode() if body is not None else None,
        )
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)

    selection = json.loads(Path("datasets/fixtures/safety-critical-request.json").read_text())
    selection["review_id"] = "http-postgres-demo-" + uuid4().hex
    unauth_status, _ = call("/v1/demo/reviews", body={"selection": selection})
    operator = environment["HOLOASSIST_API_OPERATOR_TOKEN"]
    reviewer = environment["HOLOASSIST_API_REVIEWER_TOKEN"]
    status, record = call("/v1/demo/reviews", operator, {"selection": selection})
    if status != 200:
        raise SystemExit("Local review creation failed; credentials were not displayed.")
    base_path = "/v1/demo/reviews/" + record["approval_id"]
    repeated_status, repeated = call("/v1/demo/reviews", operator, {"selection": selection})
    context_status, _ = call(base_path + "/context", reviewer)
    forbidden_status, _ = call(
        base_path + "/decision",
        operator,
        {
            "decision": "approve",
            "expected_context_digest": record["context_digest"],
        },
    )
    read_status, stored = call(base_path, operator)
    result = {
        "schema_version": "1.0",
        "scope": "synthetic_demo",
        "unauthenticated_status": unauth_status,
        "create_status": status,
        "repeat_returns_same_id": repeated_status == 200
        and repeated.get("approval_id") == record["approval_id"],
        "reviewer_context_status": context_status,
        "operator_decision_status": forbidden_status,
        "read_status": read_status,
        "record": stored,
    }
    assert unauth_status == 401 and forbidden_status == 403 and context_status == 200
    assert result["repeat_returns_same_id"] and stored["status"] == "pending"
    assert stored["guidance_allowed"] is False
    output_name = "api-container-review.json" if args.port == 8002 else "api-postgres-review.json"
    Path("docs/examples", output_name).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        "HTTP + PostgreSQL demo verified: 401/403, idempotent open, reviewer context; "
        "review remains pending."
    )


if __name__ == "__main__":
    main()
