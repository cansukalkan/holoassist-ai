"""In-process HTTP tests: no network, database, device, or API key required."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from holoassist.api.app import local_app


@pytest.fixture
def client():
    with TestClient(local_app()) as client:
        yield client


def selection():
    return json.loads(Path("datasets/fixtures/safety-critical-request.json").read_text())


def test_health_is_liveness_only(client):
    assert client.get("/health").json() == {
        "schema_version": "1.0",
        "status": "ok",
        "scope": "synthetic_demo",
        "guidance_allowed": False,
    }


def test_critical_request_never_authorizes_and_is_repeatable(client):
    a = client.post("/v1/demo/safety/evaluate", json=selection())
    b = client.post("/v1/demo/safety/evaluate", json=selection())
    assert a.status_code == 200
    assert a.json() == b.json()
    assert a.json()["status"] == "needs_approval"
    assert a.json()["guidance_allowed"] is False
    assert all(step["display_text"] is None for step in a.json()["steps"])


@pytest.mark.parametrize("field", ["approval", "analysis", "catalog", "authenticated_reviewer"])
def test_client_cannot_supply_trusted_context(client, field):
    response = client.post("/v1/demo/safety/evaluate", json=selection() | {field: "secret-value"})
    assert response.status_code == 422
    assert response.json() == {"schema_version": "1.0", "code": "invalid_request"}
    assert "secret-value" not in response.text


def test_unknown_step_is_blocked(client):
    payload = selection()
    payload["steps"][0]["instruction_id"] = "unknown"
    report = client.post("/v1/demo/safety/evaluate", json=payload).json()
    assert report["status"] == "blocked"
    assert report["steps"][0]["display_text"] is None


def test_lost_tracking_hides_plan(client):
    payload = selection() | {"tracking_status": "lost"}
    report = client.post("/v1/demo/safety/evaluate", json=payload).json()
    assert report["status"] != "display_allowed"
    assert report["guidance_allowed"] is False


def test_no_approval_write_endpoint(client):
    assert client.post("/v1/approvals/approve", json={"approval": True}).status_code == 404


def test_malformed_json_has_sanitized_error(client):
    result = client.post("/v1/demo/safety/evaluate", content="{bad")
    assert result.status_code == 422
    assert result.json()["code"] == "invalid_request"


def test_information_card_preserves_source(client):
    payload = selection()
    payload["steps"][0].update(instruction_id="demo-information", part_id="demo-label")
    response = client.post("/v1/demo/safety/evaluate", json=payload)
    assert response.status_code == 200
    report = response.json()
    assert report["status"] == "display_allowed"
    citation = report["steps"][0]["citations"][0]
    assert citation["document_version"] == "test-1"
    assert citation["document_id"] == "holoassist-synthetic-safety"
    assert citation["page"] == 1
    assert citation["evidence_id"]
    assert report["steps"][0]["display_text"] == citation["quote"]
