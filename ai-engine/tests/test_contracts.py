"""Negative contract tests prevent ambiguous sources and sensor payloads."""

import json
from datetime import UTC, datetime

import pytest
from holoassist.contracts import Evidence, Observation, ObservationSeries
from pydantic import ValidationError


@pytest.fixture
def evidence_payload():
    return {
        "evidence_id": "synthetic-evidence-1",
        "equipment_id": "synthetic-rig",
        "document_id": "test-document",
        "document_version": "test-1",
        "checksum": "a" * 64,
        "page": 1,
        "excerpt": "Synthetic test text; not a manufacturer instruction.",
    }


@pytest.fixture
def observation_payload():
    return {
        "equipment_id": "synthetic-rig",
        "sensor_id": "synthetic-temperature",
        "timestamp_utc": "2026-10-19T12:00:00+03:00",
        "quantity": "temperature",
        "value": 25.0,
        "unit": "degC",
        "provenance": "simulated",
        "quality": "valid",
    }


def test_evidence_json_roundtrip_and_section_locator(evidence_payload):
    evidence_payload.pop("page")
    evidence_payload["section"] = "Test section"
    evidence = Evidence.model_validate(evidence_payload)
    assert Evidence.model_validate_json(evidence.model_dump_json()) == evidence
    assert evidence.section == "Test section"


@pytest.mark.parametrize("field", ["document_version", "checksum", "equipment_id", "excerpt"])
def test_evidence_missing_required_metadata(evidence_payload, field):
    evidence_payload.pop(field)
    with pytest.raises(ValidationError):
        Evidence.model_validate(evidence_payload)


@pytest.mark.parametrize(
    "change",
    [
        {"page": None},
        {"page": 0},
        {"page": True},
        {"page": "1"},
        {"section": "   "},
        {"checksum": "not-a-sha256"},
        {"excerpt": "  "},
        {"retrieval_score": float("nan")},
        {"retrieval_score": float("inf")},
        {"retrieval_score": True},
        {"schema_version": "2.0"},
        {"approval": True},
    ],
)
def test_evidence_rejects_invalid_metadata(evidence_payload, change):
    with pytest.raises(ValidationError):
        Evidence.model_validate(evidence_payload | change)


def test_retrieval_score_is_not_a_probability(evidence_payload):
    assert (
        Evidence.model_validate(evidence_payload | {"retrieval_score": -2.5}).retrieval_score
        == -2.5
    )


def test_observation_normalizes_utc_and_preserves_provenance(observation_payload):
    item = Observation.model_validate(observation_payload)
    assert item.timestamp_utc == datetime(2026, 10, 19, 9, tzinfo=UTC)
    payload = json.loads(item.model_dump_json())
    assert payload["timestamp_utc"] == "2026-10-19T09:00:00Z"
    assert payload["provenance"] == "simulated"
    assert Observation.model_validate_json(item.model_dump_json()) == item
    with pytest.raises(ValidationError):
        item.provenance = "measured"


@pytest.mark.parametrize("field", ["unit", "provenance", "quality", "timestamp_utc"])
def test_observation_requires_explicit_metadata(observation_payload, field):
    observation_payload.pop(field)
    with pytest.raises(ValidationError):
        Observation.model_validate(observation_payload)


@pytest.mark.parametrize(
    "change",
    [
        {"timestamp_utc": "2026-10-19T12:00:00"},
        {"timestamp_utc": "not-a-date"},
        {"timestamp_utc": 1792400400},
        {"timestamp_utc": True},
        {"value": float("nan")},
        {"value": float("inf")},
        {"value": float("-inf")},
        {"value": True},
        {"value": "25.0"},
        {"unit": "A"},
        {"unit": "Celsius"},
        {"provenance": "unknown"},
        {"quality": "unknown"},
        {"sensor_id": " "},
        {"schema_version": "2.0"},
        {"unexpected": 1},
    ],
)
def test_observation_rejects_ambiguous_input(observation_payload, change):
    with pytest.raises(ValidationError):
        Observation.model_validate(observation_payload | change)


@pytest.mark.parametrize(
    ("quantity", "unit"), [("temperature", "degC"), ("current", "A"), ("vibration", "m/s2")]
)
def test_supported_quantities(observation_payload, quantity, unit):
    item = Observation.model_validate(observation_payload | {"quantity": quantity, "unit": unit})
    assert item.unit == unit


def test_series_json_roundtrip(observation_payload):
    second = observation_payload | {"timestamp_utc": "2026-10-19T09:00:01Z"}
    series = ObservationSeries(observations=[observation_payload, second])
    assert ObservationSeries.model_validate_json(series.model_dump_json()) == series
    assert isinstance(series.observations, tuple)


@pytest.mark.parametrize(
    "change",
    [
        {"timestamp_utc": "2026-10-19T09:00:00Z"},
        {"timestamp_utc": "2026-10-19T08:59:59Z"},
        {"timestamp_utc": "2026-10-19T12:00:00+03:00"},
        {"sensor_id": "different-sensor"},
        {"equipment_id": "different-rig"},
        {"provenance": "measured"},
        {"quantity": "current", "unit": "A"},
    ],
)
def test_series_rejects_disorder_or_mixed_metadata(observation_payload, change):
    second = observation_payload | {"timestamp_utc": "2026-10-19T09:00:01Z"} | change
    with pytest.raises(ValidationError):
        ObservationSeries(observations=[observation_payload, second])


def test_series_requires_samples():
    with pytest.raises(ValidationError):
        ObservationSeries(observations=[])
