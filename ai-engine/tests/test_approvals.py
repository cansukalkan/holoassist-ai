"""Persistent demo review, expiry, context revalidation and single-use continuation."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from holoassist.contracts.analysis import AnalysisState
from holoassist.rag.chunking import chunk_document
from holoassist.safety.approvals import ApprovalError, ApprovalStore

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "datasets/fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8-sig"))


@pytest.fixture
def context():
    state = AnalysisState(
        request=load("analysis-request.json"),
        status="ready_for_diagnostic",
        evidence=chunk_document((FIXTURES / "synthetic-safety.json").read_bytes()),
    )
    return (
        state.model_dump(mode="json"),
        load("safety-critical-request.json"),
        load("instruction-catalog.json"),
    )


@pytest.fixture
def db_path():
    directory = ROOT / "data" / "approval-tests" / uuid4().hex
    directory.mkdir(parents=True)
    return directory / "reviews.sqlite3"


@pytest.fixture
def clock():
    return [datetime(2026, 10, 21, 12, tzinfo=UTC)]


@pytest.fixture
def store(db_path, clock):
    return ApprovalStore(db_path, authorized_reviewers=("reviewer-1",), clock=lambda: clock[0])


def approve(store, record, **overrides):
    return store.decide(
        record.approval_id,
        **(
            dict(
                authenticated_reviewer="reviewer-1",
                decision="approve",
                expected_context_digest=record.context_digest,
            )
            | overrides
        ),
    )


def test_checkpoint_survives_new_store_instance(store, context, db_path, clock):
    opened = store.open_review(*context)
    fresh = ApprovalStore(db_path, authorized_reviewers=("reviewer-1",), clock=lambda: clock[0])
    assert fresh.get(opened.approval_id) == opened
    snapshot = fresh.review_context(opened.approval_id, authenticated_reviewer="reviewer-1")
    assert snapshot["snapshot"]["request"]["steps"][0]["instruction_id"] == "demo-critical"
    assert snapshot["record"]["context_digest"] == opened.context_digest
    assert opened.guidance_allowed is False


def test_approved_demo_can_be_consumed_once(store, context):
    pending = store.open_review(*context)
    approved = approve(store, pending)
    assert approved.status == "approved"
    receipt = store.resume_demo(pending.approval_id, *context)
    assert receipt.status == "demo_continuation_recorded"
    assert receipt.guidance_allowed is False
    assert store.get(pending.approval_id).status == "consumed"
    with pytest.raises(ApprovalError, match="approval_not_approved"):
        store.resume_demo(pending.approval_id, *context)
    assert [x["event"] for x in store.audit(pending.approval_id)] == [
        "review_created",
        "review_approved",
        "demo_continuation_recorded",
    ]


def test_unauthorized_reviewer_cannot_decide_or_inspect(store, context):
    record = store.open_review(*context)
    with pytest.raises(ApprovalError, match="reviewer_not_authorized"):
        approve(store, record, authenticated_reviewer="untrusted")
    with pytest.raises(ApprovalError, match="reviewer_not_authorized"):
        store.review_context(record.approval_id, authenticated_reviewer="untrusted")
    assert store.get(record.approval_id).status == "pending"


def test_reviewer_must_bind_decision_to_reviewed_context(store, context):
    record = store.open_review(*context)
    with pytest.raises(ApprovalError, match="review_context_mismatch"):
        approve(store, record, expected_context_digest="a" * 64)
    assert store.get(record.approval_id).status == "pending"


def test_rejected_request_cannot_resume_or_be_approved_again(store, context):
    record = store.open_review(*context)
    assert approve(store, record, decision="reject").status == "rejected"
    with pytest.raises(ApprovalError):
        store.resume_demo(record.approval_id, *context)
    with pytest.raises(ApprovalError, match="approval_not_pending"):
        approve(store, record)


def test_pending_request_cannot_resume(store, context):
    record = store.open_review(*context)
    with pytest.raises(ApprovalError):
        store.resume_demo(record.approval_id, *context)
    assert store.get(record.approval_id).status == "pending"


@pytest.mark.parametrize("approved", [False, True])
def test_expiry_persists_even_when_operation_is_rejected(store, context, clock, approved):
    record = store.open_review(*context, ttl_seconds=10)
    if approved:
        approve(store, record)
    clock[0] += timedelta(seconds=10)
    with pytest.raises(ApprovalError):
        if approved:
            store.resume_demo(record.approval_id, *context)
        else:
            approve(store, record)
    assert store.get(record.approval_id).status == "expired"
    assert store.audit(record.approval_id)[-1]["event"] == "approval_expired"


def test_reopening_same_review_does_not_extend_lifetime(store, context, clock):
    record = store.open_review(*context, ttl_seconds=10)
    clock[0] += timedelta(seconds=5)
    again = store.open_review(*context, ttl_seconds=3600)
    assert again.approval_id == record.approval_id
    assert again.expires_utc == record.expires_utc
    assert len(store.audit(record.approval_id)) == 1


def test_review_id_cannot_be_rebound_to_changed_catalog(store, context):
    store.open_review(*context)
    context[2]["catalog_version"] = "changed"
    with pytest.raises(ApprovalError, match="review_id_context_conflict"):
        store.open_review(*context)


@pytest.mark.parametrize(
    "change", ["catalog", "request_id", "tracking", "source", "risk", "equipment"]
)
def test_resume_revalidates_entire_current_context(store, context, change):
    record = store.open_review(*context)
    approve(store, record)
    if change == "catalog":
        context[2]["catalog_version"] = "changed"
    elif change == "request_id":
        context[1]["review_id"] = "another-review"
    elif change == "tracking":
        context[1]["tracking_status"] = "lost"
    elif change == "source":
        context[0]["evidence"][0]["checksum"] = "a" * 64
    elif change == "risk":
        context[2]["instructions"][1]["risk"] = "prohibited"
    else:
        context[0]["request"]["equipment_id"] = "another-rig"
    with pytest.raises(ApprovalError, match="context_changed_or_gate_rejected"):
        store.resume_demo(record.approval_id, *context)
    assert store.get(record.approval_id).status == "invalidated"
    assert store.audit(record.approval_id)[-1]["event"] == "context_changed_or_gate_rejected"


def test_revoked_reviewer_cannot_enable_continuation(store, context, db_path, clock):
    record = store.open_review(*context)
    approve(store, record)
    revoked = ApprovalStore(db_path, authorized_reviewers=(), clock=lambda: clock[0])
    with pytest.raises(ApprovalError, match="reviewer_authorization_revoked"):
        revoked.resume_demo(record.approval_id, *context)
    assert revoked.get(record.approval_id).status == "invalidated"


def test_racing_consumers_produce_only_one_receipt(store, context):
    record = store.open_review(*context)
    approve(store, record)

    def consume():
        try:
            store.resume_demo(record.approval_id, *context)
            return "consumed"
        except ApprovalError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: consume(), range(2)))
    assert sorted(results) == ["consumed", "rejected"]
    assert (
        sum(x["event"] == "demo_continuation_recorded" for x in store.audit(record.approval_id))
        == 1
    )


@pytest.mark.parametrize("ttl", [0, -1, 3601, True, 1.5])
def test_invalid_expiration_is_rejected(store, context, ttl):
    with pytest.raises(ApprovalError, match="invalid_approval_ttl"):
        store.open_review(*context, ttl_seconds=ttl)


@pytest.mark.parametrize("kind", ["informational", "prohibited", "unknown"])
def test_noncritical_or_forbidden_plans_cannot_enter_approval_queue(store, context, kind):
    context[2]["instructions"][1]["risk"] = kind
    with pytest.raises(ApprovalError, match="plan_not_eligible_for_approval"):
        store.open_review(*context)


def test_unknown_approval_is_rejected(store):
    with pytest.raises(ApprovalError, match="approval_not_found"):
        store.get("nonexistent")


def test_backwards_server_clock_cannot_revive_or_use_approval(store, context, clock):
    record = store.open_review(*context)
    clock[0] -= timedelta(seconds=1)
    with pytest.raises(ApprovalError, match="server_clock_regressed"):
        store.get(record.approval_id)


def test_saved_checkpoint_tampering_invalidates_decision(store, context, db_path):
    import sqlite3

    record = store.open_review(*context)
    with sqlite3.connect(db_path) as con:
        raw = con.execute(
            "SELECT snapshot_json FROM approvals WHERE approval_id=?", (record.approval_id,)
        ).fetchone()[0]
        snapshot = json.loads(raw)
        snapshot["catalog"]["catalog_version"] = "tampered"
        con.execute(
            "UPDATE approvals SET snapshot_json=? WHERE approval_id=?",
            (json.dumps(snapshot), record.approval_id),
        )
    with pytest.raises(ApprovalError, match="checkpoint_invalid"):
        approve(store, record)
    assert store.get(record.approval_id).status == "invalidated"


def test_cli_approval_survives_process_restart_and_rejects_replay(context, db_path):
    import getpass
    import os
    import subprocess
    import sys

    actor = getpass.getuser()
    backend = ApprovalStore(db_path, authorized_reviewers=(actor,))
    pending = backend.open_review(*context)
    root = db_path.parent
    files = []
    for name, value in zip(("analysis", "request", "catalog"), context, strict=True):
        path = root / f"{name}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        files.extend(["--" + name, str(path)])
    prefix = [sys.executable, "-m", "holoassist.safety.review", "--db", str(db_path)]
    env = os.environ | {"HOLOASSIST_REVIEWERS": actor, "PYTHONIOENCODING": "utf-8"}
    decision = subprocess.run(
        prefix
        + [
            "decide",
            pending.approval_id,
            "--decision",
            "approve",
            "--expected-digest",
            pending.context_digest,
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert decision.returncode == 0, decision.stderr
    assert json.loads(decision.stdout)["status"] == "approved"
    continuation = subprocess.run(
        prefix + ["resume-demo", pending.approval_id] + files,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert continuation.returncode == 0, continuation.stderr
    assert json.loads(continuation.stdout)["guidance_allowed"] is False
    replay = subprocess.run(
        prefix + ["resume-demo", pending.approval_id] + files,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert replay.returncode == 2
    assert backend.get(pending.approval_id).status == "consumed"


def test_cli_without_reviewer_allowlist_cannot_approve(context, db_path):
    import os
    import subprocess
    import sys

    backend = ApprovalStore(db_path)
    pending = backend.open_review(*context)
    env = os.environ.copy()
    env.pop("HOLOASSIST_REVIEWERS", None)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "holoassist.safety.review",
            "--db",
            str(db_path),
            "decide",
            pending.approval_id,
            "--decision",
            "approve",
            "--expected-digest",
            pending.context_digest,
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert backend.get(pending.approval_id).status == "pending"
