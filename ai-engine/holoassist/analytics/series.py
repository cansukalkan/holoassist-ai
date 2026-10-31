"""Pure, deterministic descriptive analysis of validated single-sensor series."""

import math
import statistics
from collections.abc import Mapping

from holoassist.contracts.analytics import DataReport
from holoassist.contracts.models import ObservationSeries


class NumericRangeError(ValueError):
    """The supplied finite numbers exceed this calculation's float range."""


def finite(value: float) -> float:
    if not math.isfinite(value):
        raise NumericRangeError("calculation is outside finite numeric range")
    return float(value)


def analyze_series(series: ObservationSeries | Mapping) -> DataReport:
    raw = series.model_dump() if isinstance(series, ObservationSeries) else series
    validated = ObservationSeries.model_validate(raw)
    samples = validated.observations
    if len(samples) > 100_000:
        raise ValueError("series exceeds 100000 samples")
    first, last = samples[0], samples[-1]
    base = dict(
        equipment_id=first.equipment_id,
        sensor_id=first.sensor_id,
        quantity=first.quantity,
        unit=first.unit,
        provenance=first.provenance,
        sample_count=len(samples),
        start_utc=first.timestamp_utc,
        end_utc=last.timestamp_utc,
    )
    invalid = tuple(i for i, item in enumerate(samples) if item.quality != "valid")
    if invalid:
        return DataReport(
            **base,
            status="needs_information",
            reason_code="invalid_sample_quality",
            invalid_quality_indices=invalid,
            missing_information=("valid_quality_series",),
        )
    if len(samples) < 2:
        return DataReport(
            **base,
            status="needs_information",
            reason_code="insufficient_samples",
            missing_information=("at_least_two_time_ordered_samples",),
        )
    try:
        values = [item.value for item in samples]
        times = [(item.timestamp_utc - first.timestamp_utc).total_seconds() for item in samples]
        mean = finite(statistics.fmean(values))
        median = finite(statistics.median(values))
        mean_time = statistics.fmean(times)
        centered_times = [time - mean_time for time in times]
        numerator = finite(
            math.fsum(
                finite(t * finite(y - mean)) for t, y in zip(centered_times, values, strict=True)
            )
        )
        denominator = finite(math.fsum(t * t for t in centered_times))
        slope = finite(numerator / denominator)
        direction = "positive" if slope > 0 else "negative" if slope < 0 else "zero"
        outliers = dict(status="insufficient_samples", sample_indices=())
        if len(values) >= 5:
            mad = finite(statistics.median([finite(abs(value - median)) for value in values]))
            if mad == 0:
                outliers = dict(status="zero_mad", sample_indices=())
            else:
                indices = tuple(
                    i
                    for i, value in enumerate(values)
                    if abs(finite(0.6744897501960817 * finite(value - median) / mad)) > 3.5
                )
                outliers = dict(status="evaluated", sample_indices=indices)
        return DataReport(
            **base,
            status="summary_available",
            reason_code="descriptive_statistics_only",
            statistics=dict(
                minimum=min(values),
                maximum=max(values),
                mean=mean,
                median=median,
                first_value=first.value,
                last_value=last.value,
                delta=finite(last.value - first.value),
                duration_seconds=times[-1],
                slope_per_second=slope,
                slope_unit={"degC": "degC/s", "A": "A/s", "m/s2": "(m/s2)/s"}[first.unit],
                slope_direction=direction,
            ),
            outliers=outliers,
        )
    except (ArithmeticError, NumericRangeError):
        return DataReport(**base, status="blocked", reason_code="numeric_range_unavailable")
