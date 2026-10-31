"""Verify descriptive arithmetic, irregular sampling, quality gates and abstention."""

import json
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from holoassist.analytics import analyze_series
from holoassist.contracts.analytics import DataReport
from holoassist.contracts.models import ObservationSeries
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]


def series(values, seconds=None, **changes):
    origin = datetime(2026, 10, 21, tzinfo=UTC)
    times = list(range(len(values))) if seconds is None else seconds
    return {
        "observations": [
            dict(
                equipment_id="synthetic-rig",
                sensor_id="sensor",
                timestamp_utc=(origin + timedelta(seconds=t)).isoformat(),
                quantity="temperature",
                value=float(value),
                unit="degC",
                provenance="simulated",
                quality="valid",
            )
            | changes
            for t, value in zip(times, values, strict=True)
        ]
    }


def test_linear_irregular_series_uses_actual_elapsed_seconds():
    result = analyze_series(series([10, 14, 24], [0, 2, 7]))
    assert result.status == "summary_available"
    assert result.statistics.mean == 16
    assert result.statistics.minimum == 10
    assert result.statistics.maximum == 24
    assert result.statistics.median == 14
    assert result.statistics.delta == 14
    assert result.statistics.duration_seconds == 7
    assert result.statistics.slope_per_second == pytest.approx(2)
    assert result.statistics.slope_unit == "degC/s"
    assert result.statistics.slope_direction == "positive"
    assert result.outliers.status == "insufficient_samples"
    assert result.guidance_allowed is False
    assert result.provenance == "simulated"
    assert DataReport.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize(
    "values,direction,slope",
    [([3, 2, 1], "negative", -1), ([2, 2, 2], "zero", 0), ([-2, -1, 0], "positive", 1)],
)
def test_slope_sign_is_descriptive(values, direction, slope):
    report = analyze_series(series(values))
    assert report.statistics.slope_direction == direction
    assert report.statistics.slope_per_second == pytest.approx(slope)


def test_outlier_sample_index_is_not_a_fault_verdict():
    report = analyze_series(series([10, 11, 12, 100, 13, 14]))
    assert report.outliers.status == "evaluated"
    assert report.outliers.sample_indices == (3,)
    assert report.outliers.threshold == 3.5
    assert report.reason_code == "descriptive_statistics_only"


def test_zero_mad_does_not_divide_by_zero_or_claim_no_anomaly():
    report = analyze_series(series([10, 10, 10, 10, 100]))
    assert report.status == "summary_available"
    assert report.outliers.status == "zero_mad"
    assert report.outliers.sample_indices == ()


@pytest.mark.parametrize("quality", ["suspect", "invalid"])
def test_untrusted_quality_is_not_silently_dropped(quality):
    payload = series([10, 11, 12])
    payload["observations"][1]["quality"] = quality
    report = analyze_series(payload)
    assert report.status == "needs_information"
    assert report.invalid_quality_indices == (1,)
    assert report.sample_count == 3
    assert report.statistics is None
    assert report.outliers is None


def test_one_sample_requests_more_data():
    result = analyze_series(series([10]))
    assert result.status == "needs_information"
    assert result.statistics is None
    assert result.reason_code == "insufficient_samples"


@pytest.mark.parametrize("values", [[], [float("nan"), 1], [float("inf"), 1]])
def test_empty_or_nonfinite_series_is_rejected(values):
    with pytest.raises(ValidationError):
        analyze_series(series(values))


@pytest.mark.parametrize("seconds", [[0, 0], [1, 0]])
def test_duplicate_or_reversed_time_is_rejected(seconds):
    with pytest.raises(ValidationError):
        analyze_series(series([1, 2], seconds))


@pytest.mark.parametrize(
    "change",
    [
        {"provenance": "measured"},
        {"unit": "A", "quantity": "current"},
        {"sensor_id": "different"},
        {"equipment_id": "different"},
    ],
)
def test_mixed_series_context_is_rejected(change):
    payload = series([1, 2])
    payload["observations"][1] |= change
    with pytest.raises(ValidationError):
        analyze_series(payload)


def test_large_finite_values_return_explicit_numeric_failure():
    result = analyze_series(series([1e308, -1e308]))
    assert result.status == "blocked"
    assert result.reason_code == "numeric_range_unavailable"
    assert result.statistics is None


def test_measured_provenance_is_preserved_without_asserting_authenticity():
    result = analyze_series(series([1, 2, 3], provenance="measured"))
    assert result.provenance == "measured"
    assert result.guidance_allowed is False


@pytest.mark.parametrize(
    "quantity,unit,slope_unit",
    [("temperature", "degC", "degC/s"), ("current", "A", "A/s"), ("vibration", "m/s2", "(m/s2)/s")],
)
def test_supported_quantities_and_slope_units(quantity, unit, slope_unit):
    result = analyze_series(series([1, 2, 3], quantity=quantity, unit=unit))
    assert result.statistics.slope_unit == slope_unit
    assert result.quantity == quantity
    assert result.unit == unit


def test_series_instance_is_revalidated():
    source = ObservationSeries.model_validate(series([1, 2, 3]))
    assert analyze_series(source) == analyze_series(source.model_dump())


@pytest.mark.parametrize("name", ["temperature", "current", "vibration"])
def test_committed_sensor_fixtures_remain_simulated(name):
    payload = json.loads(
        (ROOT / f"datasets/fixtures/sensor-{name}.json").read_text(encoding="utf-8-sig")
    )
    result = analyze_series(payload)
    assert result.status == "summary_available"
    assert result.provenance == "simulated"
    assert result.sample_count == 6


@pytest.mark.parametrize(
    "change",
    [
        {"guidance_allowed": True},
        {"status": "needs_information"},
        {"unit": "A"},
        {"sample_count": 1},
    ],
)
def test_report_rejects_inconsistent_fields(change):
    report = analyze_series(series([1, 2, 3])).model_dump()
    with pytest.raises(ValidationError):
        DataReport.model_validate(report | change)


def test_cli_does_not_echo_bad_payload(monkeypatch, capsys):
    from holoassist.analytics.__main__ import main

    monkeypatch.setattr("sys.argv", ["holoassist.analytics", "--series", "fixture.json"])
    with patch(
        "holoassist.analytics.__main__.Path.open",
        return_value=BytesIO(b'{"secret":"private-test-value"}'),
    ):
        assert main() == 2
    captured = capsys.readouterr()
    assert "invalid_or_unavailable_series" in captured.err
    assert "private-test-value" not in captured.err


def test_large_but_representable_statistics_are_not_arbitrarily_rejected():
    result = analyze_series(series([1e200, 1e200, 1e200]))
    assert result.status == "summary_available"
    assert result.statistics.mean == 1e200
    assert result.statistics.slope_per_second == 0
