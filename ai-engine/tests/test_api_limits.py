"""Body limits apply to received bytes before the downstream handler can write."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from holoassist.api.app import local_app
from holoassist.api.limits import BodyLimitMiddleware
from holoassist.safety.approvals import ApprovalStore


def run_body(headers, chunks, limit=8):
    sent = []
    called = []
    incoming = [
        dict(type="http.request", body=chunk, more_body=i < len(chunks) - 1)
        for i, chunk in enumerate(chunks)
    ]

    async def receive():
        return incoming.pop(0)

    async def send(message):
        sent.append(message)

    async def downstream(scope, receive, send):
        called.append(await receive())

    asyncio.run(
        BodyLimitMiddleware(downstream, max_bytes=limit)(
            {"type": "http", "headers": headers},
            receive,
            send,
        )
    )
    return sent, called


def test_limit_allows_exact_bytes():
    sent, called = run_body([(b"content-length", b"8")], [b"1234", b"5678"])
    assert not sent
    assert called[0]["body"] == b"12345678"


@pytest.mark.parametrize("headers", [[], [(b"content-length", b"0")]])
def test_streaming_over_limit_does_not_reach_endpoint(headers):
    sent, called = run_body(headers, [b"12345", b"6789"])
    assert not called
    assert sent[0]["status"] == 413
    assert b"request_too_large" in sent[1]["body"]


def test_long_length_header_cannot_bypass_received_byte_limit():
    sent, called = run_body([(b"content-length", b"999999999999999999999999")], [b"123456789"])
    assert not called
    assert sent[0]["status"] == 413


@pytest.mark.parametrize(
    "headers",
    [
        [(b"content-length", b"-1")],
        [(b"content-length", b"bad")],
        [(b"content-length", b"1"), (b"content-length", b"1")],
    ],
)
def test_invalid_length_rejected(headers):
    sent, called = run_body(headers, [])
    assert not called
    assert sent[0]["status"] == 400


def test_limit_counts_utf8_bytes():
    sent, called = run_body([], ["şşşşş".encode()])
    assert sent[0]["status"] == 413
    assert not called


def test_oversized_json_sanitized():
    with TestClient(local_app()) as client:
        response = client.post("/v1/demo/safety/evaluate", content=b"x" * 65537)
    assert response.status_code == 413
    assert response.json() == {"schema_version": "1.0", "code": "request_too_large"}


def test_read_only_server_reports_no_storage():
    with TestClient(local_app()) as client:
        assert client.get("/ready").json()["storage"] == "not_configured"


def test_readiness_checks_storage_without_writes(tmp_path):
    store = ApprovalStore(tmp_path / "reviews.db")
    store.check_ready()
    with store._transaction() as con:
        assert con.execute("SELECT count(*) FROM approvals").fetchone()[0] == 0
        assert con.execute("SELECT count(*) FROM approval_events").fetchone()[0] == 0
