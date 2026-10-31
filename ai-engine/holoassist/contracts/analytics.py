"""Descriptive sensor analytics output, never a maintenance authorization."""

from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from holoassist.contracts.models import (
    Checksum,
    Contract,
    FiniteNumber,
    NonBlank,
    ObservationSeries,
)

Index = Annotated[int, Field(strict=True, ge=0)]


class SeriesStatistics(Contract):
    minimum: FiniteNumber
    maximum: FiniteNumber
    mean: FiniteNumber
    median: FiniteNumber
    first_value: FiniteNumber
    last_value: FiniteNumber
    delta: FiniteNumber
    duration_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    slope_per_second: FiniteNumber
    slope_unit: Literal["degC/s", "A/s", "(m/s2)/s"]
    slope_direction: Literal["positive", "negative", "zero"]

    @model_validator(mode="after")
    def require_consistent_summary(self) -> Self:
        if self.minimum > self.maximum or not self.minimum <= self.mean <= self.maximum:
            raise ValueError("summary minimum/mean/maximum are inconsistent")
        expected = (
            "positive"
            if self.slope_per_second > 0
            else "negative"
            if self.slope_per_second < 0
            else "zero"
        )
        if self.slope_direction != expected:
            raise ValueError("slope direction must reflect its sign")
        return self


class OutlierSummary(Contract):
    method: Literal["modified_z_score_mad"] = "modified_z_score_mad"
    threshold: Literal[3.5] = 3.5
    status: Literal["evaluated", "insufficient_samples", "zero_mad"]
    sample_indices: tuple[Index, ...] = ()

    @model_validator(mode="after")
    def require_consistent_outliers(self) -> Self:
        if self.status != "evaluated" and self.sample_indices:
            raise ValueError("unevaluated outlier summary cannot contain indices")
        if tuple(sorted(set(self.sample_indices))) != self.sample_indices:
            raise ValueError("outlier indices must be unique and sorted")
        return self


class DataReport(Contract):
    equipment_id: NonBlank
    sensor_id: NonBlank
    quantity: Literal["temperature", "current", "vibration"]
    unit: Literal["degC", "A", "m/s2"]
    provenance: Literal["simulated", "measured"]
    guidance_allowed: Literal[False] = False
    sample_count: Annotated[int, Field(strict=True, ge=1)]
    start_utc: AwareDatetime
    end_utc: AwareDatetime
    status: Literal["summary_available", "needs_information", "blocked"]
    reason_code: NonBlank
    invalid_quality_indices: tuple[Index, ...] = ()
    missing_information: tuple[NonBlank, ...] = ()
    statistics: SeriesStatistics | None = None
    outliers: OutlierSummary | None = None

    @model_validator(mode="after")
    def require_consistent_report(self) -> Self:
        available = self.status == "summary_available"
        if available != (self.statistics is not None and self.outliers is not None):
            raise ValueError("available report requires statistics and outlier result")
        if not available and (self.statistics is not None or self.outliers is not None):
            raise ValueError("unavailable report cannot contain partial statistics")
        if (self.status == "needs_information") != bool(self.missing_information):
            raise ValueError("missing information must reflect report status")
        if self.end_utc < self.start_utc:
            raise ValueError("report time range is reversed")
        if any(i >= self.sample_count for i in self.invalid_quality_indices):
            raise ValueError("invalid-quality index outside series")
        if available:
            duration = (self.end_utc - self.start_utc).total_seconds()
            if self.statistics.duration_seconds != duration:
                raise ValueError("statistics duration does not match report timestamps")
            if self.outliers.status == "evaluated" and self.sample_count < 5:
                raise ValueError("outlier evaluation requires at least five samples")
            if self.sample_count < 2 or self.invalid_quality_indices:
                raise ValueError("statistics require at least two valid-quality samples")
            if any(i >= self.sample_count for i in self.outliers.sample_indices):
                raise ValueError("outlier index outside series")
            if (
                self.statistics.slope_unit
                != {"degC": "degC/s", "A": "A/s", "m/s2": "(m/s2)/s"}[self.unit]
            ):
                raise ValueError("slope unit does not match series unit")
        if self.unit != {"temperature": "degC", "current": "A", "vibration": "m/s2"}[self.quantity]:
            raise ValueError("quantity and unit do not match")
        return self


class SensorDemoResult(Contract):
    """Bind a server-owned simulated series to its descriptive report."""

    fixture_id: Literal["current", "temperature", "vibration"]
    fixture_checksum: Checksum
    scope: Literal["synthetic_demo"] = "synthetic_demo"
    series: ObservationSeries
    report: DataReport

    @model_validator(mode="after")
    def require_matching_series(self) -> Self:
        first, last = self.series.observations[0], self.series.observations[-1]
        if first.provenance != "simulated" or self.report.provenance != "simulated":
            raise ValueError("sensor demo requires simulated data")
        if self.fixture_id != first.quantity:
            raise ValueError("fixture must match sensor quantity")
        for key in ("equipment_id", "sensor_id", "quantity", "unit", "provenance"):
            if getattr(first, key) != getattr(self.report, key):
                raise ValueError("series and report identity mismatch")
        if (
            self.report.sample_count != len(self.series.observations)
            or self.report.start_utc != first.timestamp_utc
            or self.report.end_utc != last.timestamp_utc
        ):
            raise ValueError("series and report range mismatch")
        return self
