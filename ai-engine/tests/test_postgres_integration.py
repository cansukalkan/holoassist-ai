"""Opt-in real PostgreSQL integration tests; isolated schemas, no application data reset."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("HOLOASSIST_TEST_POSTGRES") != "1",
    reason="set HOLOASSIST_TEST_POSTGRES=1 to run against a real test server",
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "datasets/fixtures"


@pytest.fixture
def pg_store():
    psycopg = pytest.importorskip("psycopg")
    from dotenv import dotenv_values
    from holoassist.safety.postgres import PostgresApprovalStore
    from psycopg import sql

    env = {**dotenv_values(ROOT / ".env"), **os.environ}
    params = dict(
        host=env.get("HOLOASSIST_POSTGRES_HOST", "127.0.0.1"),
        port=int(env.get("HOLOASSIST_POSTGRES_PORT", "5433")),
        dbname=env.get("HOLOASSIST_POSTGRES_DATABASE", "holoassist"),
        user=env.get("HOLOASSIST_POSTGRES_USER", "holoassist"),
        password=env.get("HOLOASSIST_POSTGRES_PASSWORD", ""),
    )
    schema = "test_" + uuid4().hex
    with psycopg.connect(**params, autocommit=True, connect_timeout=5) as con:
        con.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    now = [datetime(2026, 10, 21, 12, tzinfo=UTC)]

    def fresh():
        return PostgresApprovalStore(
            **params,
            options=f"-c search_path={schema}",
            authorized_reviewers=("reviewer",),
            clock=lambda: now[0],
        )

    try:
        yield fresh(), fresh, now
    finally:
        # Schema was generated and created by this test; application schema is never dropped.
        with psycopg.connect(**params, autocommit=True, connect_timeout=5) as con:
            con.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


@pytest.fixture
def context():
    from holoassist.contracts.analysis import AnalysisState
    from holoassist.rag.chunking import chunk_document

    def load(name):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8-sig"))

    state = AnalysisState(
        request=load("analysis-request.json"),
        status="ready_for_diagnostic",
        evidence=chunk_document((FIXTURES / "synthetic-safety.json").read_bytes()),
    )
    return state, load("safety-critical-request.json"), load("instruction-catalog.json")


def approve(store, record):
    return store.decide(
        record.approval_id,
        authenticated_reviewer="reviewer",
        decision="approve",
        expected_context_digest=record.context_digest,
    )


def test_postgres_lifecycle_survives_reconnection(pg_store, context):
    store, fresh, _ = pg_store
    record = store.open_review(*context)
    approve(store, record)
    reopened = fresh()
    assert reopened.get(record.approval_id).status == "approved"
    receipt = reopened.resume_demo(record.approval_id, *context)
    assert receipt.guidance_allowed is False
    assert store.get(record.approval_id).status == "consumed"
    assert len(store.audit(record.approval_id)) == 3


def test_postgres_replay_is_rejected(pg_store, context):
    from holoassist.safety.approvals import ApprovalError

    store, _, _ = pg_store
    record = store.open_review(*context)
    approve(store, record)
    store.resume_demo(record.approval_id, *context)
    with pytest.raises(ApprovalError):
        store.resume_demo(record.approval_id, *context)


def test_postgres_parallel_consumers_cannot_double_consume(pg_store, context):
    from holoassist.safety.approvals import ApprovalError

    store, fresh, _ = pg_store
    record = store.open_review(*context)
    approve(store, record)
    stores = [fresh(), fresh()]

    def consume(backend):
        try:
            backend.resume_demo(record.approval_id, *context)
            return True
        except ApprovalError:
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(consume, stores)) == [False, True]


def test_postgres_parallel_open_is_idempotent(pg_store, context):
    store, fresh, _ = pg_store
    stores = [store, fresh()]
    with ThreadPoolExecutor(max_workers=2) as executor:
        records = list(executor.map(lambda backend: backend.open_review(*context), stores))
    assert records[0].approval_id == records[1].approval_id
    assert len(store.audit(records[0].approval_id)) == 1


def test_postgres_expiry_persists_after_denied_consumption(pg_store, context):
    from holoassist.safety.approvals import ApprovalError

    store, fresh, clock = pg_store
    record = store.open_review(*context, ttl_seconds=1)
    approve(store, record)
    clock[0] += timedelta(seconds=1)
    with pytest.raises(ApprovalError):
        store.resume_demo(record.approval_id, *context)
    assert fresh().get(record.approval_id).status == "expired"


def test_postgres_changed_context_is_invalidated(pg_store, context):
    from holoassist.safety.approvals import ApprovalError

    store, fresh, _ = pg_store
    record = store.open_review(*context)
    approve(store, record)
    context[2]["catalog_version"] = "changed"
    with pytest.raises(ApprovalError):
        store.resume_demo(record.approval_id, *context)
    assert fresh().get(record.approval_id).status == "invalidated"


def test_postgres_http_reviews_persist(pg_store, context):
    from fastapi.testclient import TestClient
    from holoassist.api.app import create_app
    from holoassist.api.auth import LocalCredentials
    from holoassist.contracts.safety import InstructionCatalog

    store, fresh, _ = pg_store
    state, selection, catalog = context
    store.reviewers = frozenset({"reviewer", "local-api-reviewer"})
    operator = {"Authorization": "Bearer " + "o" * 64}
    reviewer = {"Authorization": "Bearer " + "r" * 64}
    with TestClient(
        create_app(
            state,
            InstructionCatalog.model_validate(catalog),
            store=store,
            credentials=LocalCredentials("o" * 64, "r" * 64),
        )
    ) as client:
        record = client.post("/v1/demo/reviews", json={"selection": selection}, headers=operator)
        assert record.status_code == 200
        record = record.json()
        base = "/v1/demo/reviews/" + record["approval_id"]
        assert (
            client.post("/v1/demo/reviews", json={"selection": selection}, headers=operator).json()
            == record
        )
        body = {"decision": "reject", "expected_context_digest": record["context_digest"]}
        assert client.post(base + "/decision", json=body, headers=operator).status_code == 403
        assert client.get(base + "/context", headers=reviewer).status_code == 200
        response = client.post(base + "/decision", json=body, headers=reviewer)
        assert response.status_code == 200
        assert response.json()["guidance_allowed"] is False
    assert fresh().get(record["approval_id"]).status == "rejected"
    assert fresh().audit(record["approval_id"])[-1]["actor"] == "local-api-reviewer"
