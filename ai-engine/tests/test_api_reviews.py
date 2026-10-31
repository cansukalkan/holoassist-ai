"""Local review authorization and persistent lifecycle over in-process HTTP."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from holoassist.api.app import create_app
from holoassist.api.auth import LocalCredentials
from holoassist.contracts.analysis import AnalysisState
from holoassist.contracts.safety import InstructionCatalog
from holoassist.safety.approvals import ApprovalStore

OPERATOR = "o" * 64
REVIEWER = "r" * 64


def headers(token):
    return {"Authorization": "Bearer " + token}


def request_body():
    selection = json.loads(Path("datasets/fixtures/safety-critical-request.json").read_text())
    selection["review_id"] = str(uuid4())
    return {"selection": selection}


def client_for(path):
    return TestClient(
        create_app(
            AnalysisState.model_validate_json(
                Path("docs/examples/safety-analysis.json").read_bytes()
            ),
            InstructionCatalog.model_validate_json(
                Path("datasets/fixtures/instruction-catalog.json").read_bytes()
            ),
            store=ApprovalStore(path, authorized_reviewers=("local-api-reviewer",)),
            credentials=LocalCredentials(OPERATOR, REVIEWER),
        )
    )


@pytest.fixture
def client(tmp_path):
    with client_for(tmp_path / "reviews.db") as client:
        yield client


@pytest.mark.parametrize("token", [None, "wrong"])
def test_unauthenticated_open_writes_nothing(client, token):
    response = client.post(
        "/v1/demo/reviews", json=request_body(), headers=headers(token) if token else {}
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["code"] == "authentication_required"


def test_operator_cannot_decide_or_inspect(client):
    record = client.post("/v1/demo/reviews", json=request_body(), headers=headers(OPERATOR)).json()
    base = "/v1/demo/reviews/" + record["approval_id"]
    assert client.get(base + "/context", headers=headers(OPERATOR)).status_code == 403
    assert (
        client.post(
            base + "/decision",
            json={"decision": "approve", "expected_context_digest": record["context_digest"]},
            headers=headers(OPERATOR),
        ).status_code
        == 403
    )
    assert client.get(base, headers=headers(OPERATOR)).json()["status"] == "pending"


def test_reviewer_cannot_open(client):
    assert (
        client.post("/v1/demo/reviews", json=request_body(), headers=headers(REVIEWER)).status_code
        == 403
    )


@pytest.mark.parametrize("field", ["approval", "authenticated_reviewer", "analysis", "catalog"])
def test_forged_trust_fields_rejected(client, field):
    body = request_body() | {field: "secret-do-not-echo"}
    result = client.post("/v1/demo/reviews", json=body, headers=headers(OPERATOR))
    assert result.status_code == 422
    assert "secret-do-not-echo" not in result.text


def test_idempotency_and_changed_context_conflict(client):
    body = request_body()
    a = client.post("/v1/demo/reviews", json=body, headers=headers(OPERATOR))
    b = client.post("/v1/demo/reviews", json=body, headers=headers(OPERATOR))
    assert a.status_code == 200
    assert a.json() == b.json()
    body["selection"]["steps"][0]["step_id"] = "different"
    assert client.post("/v1/demo/reviews", json=body, headers=headers(OPERATOR)).status_code == 409


def test_reviewer_inspects_and_decides_persistently(tmp_path):
    path = tmp_path / "reviews.db"
    with client_for(path) as client:
        record = client.post(
            "/v1/demo/reviews", json=request_body(), headers=headers(OPERATOR)
        ).json()
        base = "/v1/demo/reviews/" + record["approval_id"]
        context = client.get(base + "/context", headers=headers(REVIEWER))
        assert context.status_code == 200
        assert context.json()["snapshot"]["catalog"]["catalog_version"] == "test-1"
        body = {"decision": "approve", "expected_context_digest": record["context_digest"]}
        wrong = body | {"expected_context_digest": "0" * 64}
        assert (
            client.post(base + "/decision", json=wrong, headers=headers(REVIEWER)).status_code
            == 409
        )
        result = client.post(base + "/decision", json=body, headers=headers(REVIEWER))
        assert result.status_code == 200
        assert result.json()["decided_by"] == "local-api-reviewer"
        assert result.json()["guidance_allowed"] is False
        assert (
            client.post(base + "/decision", json=body, headers=headers(REVIEWER)).status_code == 409
        )
    with client_for(path) as restarted:
        assert restarted.get(base, headers=headers(REVIEWER)).json()["status"] == "approved"
    events = ApprovalStore(path).audit(record["approval_id"])
    assert events[-1]["actor"] == "local-api-reviewer"


def test_rejection_and_missing_record(client):
    record = client.post("/v1/demo/reviews", json=request_body(), headers=headers(OPERATOR)).json()
    base = "/v1/demo/reviews/" + record["approval_id"]
    result = client.post(
        base + "/decision",
        json={"decision": "reject", "expected_context_digest": record["context_digest"]},
        headers=headers(REVIEWER),
    )
    assert result.json()["status"] == "rejected"
    assert (
        client.get("/v1/demo/reviews/" + str(uuid4()), headers=headers(OPERATOR)).status_code == 404
    )


@pytest.mark.parametrize("tokens", [("", ""), ("same" * 16, "same" * 16), ("short", "r" * 64)])
def test_invalid_server_credentials_fail_closed(tokens):
    with pytest.raises(ValueError):
        LocalCredentials(*tokens)


def test_old_credential_revoked_after_rotation():
    assert LocalCredentials("n" * 64, REVIEWER).authenticate(OPERATOR) is None


def test_readiness_and_storage_failure_are_separate_from_liveness(client, monkeypatch):
    from holoassist.safety.approvals import ApprovalError

    assert client.get("/ready").json()["storage"] == "reachable"

    def unavailable(self):
        raise ApprovalError("secret-storage-detail")

    monkeypatch.setattr(ApprovalStore, "check_ready", unavailable)
    result = client.get("/ready")
    assert result.status_code == 503
    assert result.json() == {"schema_version": "1.0", "code": "storage_unavailable"}
    assert "secret-storage-detail" not in result.text
    assert client.get("/health").status_code == 200
