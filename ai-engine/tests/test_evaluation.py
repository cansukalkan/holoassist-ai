"""Tests for reproducible synthetic benchmark suite and /v1/demo/evaluation."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from holoassist.api import evaluation as api_evaluation
from holoassist.api.app import local_app
from holoassist.contracts.evaluation import SyntheticBenchmarkReport
from holoassist.evaluation.benchmark import run_synthetic_benchmark
from pydantic import ValidationError

pytest.importorskip("cv2", reason="install .[vision] for full benchmark tests")
pytest.importorskip("chromadb", reason="install .[rag] for full benchmark tests")


def test_run_synthetic_benchmark_passes_all_synthetic_gates():
    report = run_synthetic_benchmark(Path("."))
    assert report.all_synthetic_gates_passed is True
    assert report.scope == "synthetic_fixture_benchmark"
    assert report.physical_device_validated is False
    assert report.calibrated_probabilities is False
    assert report.guidance_allowed is False
    assert report.vision.precision == 1.0
    assert report.vision.recall == 1.0
    assert report.vision.warped_max_corner_error_px < 12.0
    assert report.rag.citation_locator_rate == 1.0
    assert report.rag.unsupported_claim_count == 0
    assert report.rag.cross_equipment_leakage_count == 0
    assert report.rag.cache_hits == 2
    assert report.diagnostic.contradiction_preserved is True
    assert report.diagnostic.missing_counter_evidence_abstained is True
    assert report.safety_spatial.safety_violations == 0
    assert len(report.open_hardware_gates) == 3


def test_benchmark_contract_rejects_false_all_passed_claim():
    report = run_synthetic_benchmark(Path("."))
    payload = report.model_dump(mode="json")
    payload["safety_spatial"]["checks_passed"] = 7
    payload["safety_spatial"]["safety_violations"] = 1
    payload["all_synthetic_gates_passed"] = True
    with pytest.raises(ValidationError):
        SyntheticBenchmarkReport.model_validate(payload)


def test_evaluation_endpoint_and_digest_verified_fallback(monkeypatch, tmp_path):
    api_evaluation.clear_evaluation_cache()
    with TestClient(local_app()) as client:
        response = client.get("/v1/demo/evaluation")
        assert response.status_code == 200
        parsed = SyntheticBenchmarkReport.model_validate(response.json())
        assert parsed.all_synthetic_gates_passed is True

        # Simulate API-only container fallback with tampered saved digest -> must fail closed (503)
        api_evaluation.clear_evaluation_cache()
        tampered = json.loads(Path("docs/examples/synthetic-benchmark-report.json").read_text())
        tampered["fixture_digests"]["datasets/fixtures/synthetic-guide.json"] = "0" * 64
        bad_file = tmp_path / "tampered.json"
        bad_file.write_text(json.dumps(tampered), encoding="utf-8")

        def raise_import_error(*args, **kwargs):
            raise ImportError("optional cv2 missing")

        monkeypatch.setattr(api_evaluation, "run_synthetic_benchmark", raise_import_error)
        monkeypatch.setattr(api_evaluation, "SAVED_BENCHMARK_FILE", bad_file)
        failed = client.get("/v1/demo/evaluation")
        assert failed.status_code == 503
        assert failed.json()["code"] == "evaluation_demo_unavailable"

