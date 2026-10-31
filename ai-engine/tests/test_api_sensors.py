"""Fixture analytics through HTTP preserve simulated identity and fail closed."""

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from holoassist.api import sensors
from holoassist.api.app import local_app
from holoassist.contracts.analytics import SensorDemoResult
from pydantic import ValidationError


@pytest.fixture
def client():
    with TestClient(local_app()) as client:
        yield client


@pytest.mark.parametrize(
    "sensor,mean,indices",
    [
        ("current", 0.65, [3]),
        ("temperature", 30.0, []),
        ("vibration", 0.12, []),
    ],
)
def test_known_series_results_preserve_provenance(client, sensor, mean, indices):
    response = client.get("/v1/demo/sensors/" + sensor)
    assert response.status_code == 200
    payload = response.json()
    raw = Path("datasets/fixtures/sensor-" + sensor + ".json").read_bytes()
    assert payload["fixture_checksum"] == hashlib.sha256(raw).hexdigest()
    report = payload["report"]
    assert report["statistics"]["mean"] == pytest.approx(mean)
    assert report["outliers"]["sample_indices"] == indices
    assert report["provenance"] == "simulated"
    assert report["guidance_allowed"] is False
    assert all(s["provenance"] == "simulated" for s in payload["series"]["observations"])
    assert client.get("/v1/demo/sensors/" + sensor).json() == payload
    SensorDemoResult.model_validate(payload)


@pytest.mark.parametrize("sensor", ["unknown", "..", "sensor-current.json"])
def test_arbitrary_sensor_or_file_name_rejected(client, sensor):
    assert client.get("/v1/demo/sensors/" + sensor).status_code in (404, 422)


def write_fixture(tmp_path, monkeypatch, change):
    payload = json.loads(Path("datasets/fixtures/sensor-current.json").read_text())
    change(payload)
    (tmp_path / "sensor-current.json").write_text(json.dumps(payload))
    monkeypatch.setattr(sensors, "FIXTURE_DIRECTORY", tmp_path)


def test_measured_data_never_appears_in_demo(client, tmp_path, monkeypatch):
    def measured(payload):
        for sample in payload["observations"]:
            sample["provenance"] = "measured"

    write_fixture(tmp_path, monkeypatch, measured)
    result = client.get("/v1/demo/sensors/current")
    assert result.status_code == 503
    assert result.json() == {"schema_version": "1.0", "code": "sensor_demo_unavailable"}
    assert "measured" not in result.text


def test_invalid_quality_hides_statistics(client, tmp_path, monkeypatch):
    def suspect(payload):
        payload["observations"][0]["quality"] = "suspect"

    write_fixture(tmp_path, monkeypatch, suspect)
    result = client.get("/v1/demo/sensors/current").json()["report"]
    assert result["status"] == "needs_information"
    assert result["statistics"] is None and result["outliers"] is None
    assert result["invalid_quality_indices"] == [0]


def test_missing_fixture_sanitized(client, tmp_path, monkeypatch):
    monkeypatch.setattr(sensors, "FIXTURE_DIRECTORY", tmp_path / "private-path")
    response = client.get("/v1/demo/sensors/current")
    assert response.status_code == 503
    assert "private-path" not in response.text


def test_malformed_fixture_sanitized(client, tmp_path, monkeypatch):
    (tmp_path / "sensor-current.json").write_text("secret-invalid-content")
    monkeypatch.setattr(sensors, "FIXTURE_DIRECTORY", tmp_path)
    response = client.get("/v1/demo/sensors/current")
    assert response.status_code == 503
    assert "secret-invalid-content" not in response.text


@pytest.mark.parametrize("field,value", [("sensor_id", "other"), ("sample_count", 999)])
def test_result_contract_rejects_unbound_report(client, field, value):
    payload = client.get("/v1/demo/sensors/current").json()
    payload["report"][field] = value
    with pytest.raises(ValidationError):
        SensorDemoResult.model_validate(payload)


def test_no_sensor_write_endpoint(client):
    assert (
        client.post("/v1/demo/sensors/current", json={"provenance": "measured"}).status_code == 405
    )
