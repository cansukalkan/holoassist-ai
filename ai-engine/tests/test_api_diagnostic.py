"""HTTP adapter keeps source and contradiction gating in the existing evaluator."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from holoassist.api import diagnostic
from holoassist.api.app import local_app
from holoassist.contracts.diagnostic import DiagnosticReport


@pytest.fixture
def client():
    with TestClient(local_app()) as client:
        yield client


def test_complete_preserves_support_and_counter_source(client):
    response = client.get("/v1/demo/diagnostic/complete")
    assert response.status_code == 200
    report = DiagnosticReport.model_validate(response.json())
    assert report.source_kind == "synthetic"
    assert report.guidance_allowed is False
    assert len(report.hypotheses) == 2
    load = next(h for h in report.hypotheses if h.code == "demo_load_state")
    assert load.uncertainty == "conflicting_evidence"
    contrary = next(c for c in report.assertion_matches if c.relation == "contradicts")
    assert contrary.page == 4
    assert contrary.document_version == "test-1"
    assert contrary.evidence_id in load.contradicting_evidence_ids
    assert contrary.checksum and contrary.quote
    assert response.json() == client.get("/v1/demo/diagnostic/complete").json()


def test_missing_counter_source_withholds_all_hypotheses(client):
    response = client.get("/v1/demo/diagnostic/missing_counter_evidence")
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "needs_information"
    assert result["hypotheses"] == [] and result["assertion_matches"] == []
    assert result["missing_information"] == ["source_for:demo_load_state:load-contradiction"]
    assert result["guidance_allowed"] is False


def test_unknown_scenario_rejected(client):
    assert client.get("/v1/demo/diagnostic/other").status_code == 422


def test_missing_analysis_sanitized(client, tmp_path, monkeypatch):
    monkeypatch.setattr(diagnostic, "ANALYSIS_FILE", tmp_path / "private-analysis")
    result = client.get("/v1/demo/diagnostic/complete")
    assert result.status_code == 503
    assert result.json() == {"schema_version": "1.0", "code": "diagnostic_demo_unavailable"}
    assert "private-analysis" not in result.text


def test_invalid_catalog_sanitized(client, tmp_path, monkeypatch):
    path = tmp_path / "catalog.json"
    path.write_text("secret-invalid-catalog")
    monkeypatch.setattr(diagnostic, "CATALOG_FILE", path)
    result = client.get("/v1/demo/diagnostic/complete")
    assert result.status_code == 503
    assert "secret-invalid-catalog" not in result.text


def test_manufacturer_data_cannot_enter_synthetic_adapter(client, tmp_path, monkeypatch):
    state = json.loads(Path("docs/examples/diagnostic-analysis.json").read_text())
    for chunk in state["evidence"]:
        chunk["source_kind"] = "manufacturer"
    path = tmp_path / "analysis.json"
    path.write_text(json.dumps(state))
    monkeypatch.setattr(diagnostic, "ANALYSIS_FILE", path)
    assert client.get("/v1/demo/diagnostic/complete").status_code == 503


def test_does_not_accept_client_analysis_or_write(client):
    response = client.post("/v1/demo/diagnostic/complete", json={"approval": True})
    assert response.status_code == 405
