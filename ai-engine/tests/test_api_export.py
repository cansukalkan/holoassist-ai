"""Export keeps independent section decisions and source metadata intact."""

import pytest
from fastapi.testclient import TestClient
from holoassist.api import sensors
from holoassist.api.app import local_app
from holoassist.contracts.export import DemoExport
from holoassist.safety.approvals import ApprovalStore
from pydantic import ValidationError


@pytest.fixture
def client():
    with TestClient(local_app()) as client:
        yield client


def test_download_headers_and_provenance(client):
    response = client.get("/v1/demo/report")
    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith(
        'attachment; filename="holoassist-demo-'
    )
    assert response.headers["cache-control"] == "no-store"
    report = DemoExport.model_validate(response.json())
    assert report.generated_utc.utcoffset().total_seconds() == 0
    assert report.independent_sections is True
    assert report.guidance_allowed is False
    assert report.sensor.report.provenance == "simulated"
    assert report.diagnostic.source_kind == "synthetic"
    assert report.safety.steps[0].citations[0].evidence_id
    assert report.safety.steps[0].citations[0].document_version == "test-1"


@pytest.mark.parametrize(
    "scenario,status",
    [
        ("information", "display_allowed"),
        ("critical", "needs_approval"),
        ("tracking", "needs_information"),
        ("unknown", "blocked"),
    ],
)
def test_selection_preserves_safety_redaction(client, scenario, status):
    response = client.get(
        "/v1/demo/report",
        params={
            "safety": scenario,
            "sensor": "temperature",
            "diagnostic": "missing_counter_evidence",
        },
    )
    report = response.json()
    assert response.status_code == 200
    assert report["safety"]["status"] == status
    assert report["sensor"]["report"]["statistics"]["mean"] == 30
    assert report["diagnostic"]["hypotheses"] == []
    if status != "display_allowed":
        assert all(s["display_text"] is None for s in report["safety"]["steps"])
        assert all(c["quote"] is None for s in report["safety"]["steps"] for c in s["citations"])


def test_export_retains_counter_evidence(client):
    report = client.get("/v1/demo/report").json()
    assert any(
        c["relation"] == "contradicts" and c["page"] == 4
        for c in report["diagnostic"]["assertion_matches"]
    )


@pytest.mark.parametrize("field", ["safety", "sensor", "diagnostic"])
def test_unknown_scenario_cannot_select_files(client, field):
    result = client.get("/v1/demo/report", params={field: "../.env"})
    assert result.status_code == 422
    assert "../.env" not in result.text


def test_unavailable_section_never_returns_partial_download(client, tmp_path, monkeypatch):
    monkeypatch.setattr(sensors, "FIXTURE_DIRECTORY", tmp_path)
    result = client.get("/v1/demo/report")
    assert result.status_code == 503
    assert "content-disposition" not in result.headers
    assert "sensor" not in result.json() or result.json()["code"] == "sensor_demo_unavailable"


def test_export_does_not_open_or_decide_review(client, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("export cannot change review state")

    monkeypatch.setattr(ApprovalStore, "open_review", forbidden)
    monkeypatch.setattr(ApprovalStore, "decide", forbidden)
    assert client.get("/v1/demo/report").status_code == 200


def test_export_contract_refuses_mismatched_section(client):
    report = client.get("/v1/demo/report").json()
    report["selection"]["sensor"] = "vibration"
    with pytest.raises(ValidationError):
        DemoExport.model_validate(report)


def test_server_credentials_not_in_export(client, monkeypatch):
    marker = "private-token-never-exported"
    monkeypatch.setenv("HOLOASSIST_API_OPERATOR_TOKEN", marker)
    result = client.get("/v1/demo/report")
    assert marker not in result.text
    assert "approval_id" not in result.text
