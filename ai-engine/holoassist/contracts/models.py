"""Validated source references and sensor data; no equipment limits are assumed."""

from datetime import UTC, datetime
from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

NonBlank = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)]
Checksum = Annotated[str, StringConstraints(strict=True, pattern=r"^[a-f0-9]{64}$")]
FiniteNumber = Annotated[float, Field(strict=True, allow_inf_nan=False)]


class Contract(BaseModel):
    """Reject unknown fields and accidental mutation after validation."""

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)
    schema_version: Literal["1.0"] = "1.0"


class Evidence(Contract):
    """A retrieved excerpt with a locator into a specific source revision.

    checksum is the SHA-256 of original document bytes, not the excerpt.
    This validates metadata shape, not source authenticity or claim support.
    """

    evidence_id: NonBlank
    equipment_id: NonBlank
    document_id: NonBlank
    document_version: NonBlank
    checksum: Checksum
    page: Annotated[int, Field(strict=True, ge=1)] | None = None
    section: NonBlank | None = None
    excerpt: NonBlank
    retrieval_score: FiniteNumber | None = None

    @model_validator(mode="after")
    def require_locator(self) -> Self:
        if self.page is None and self.section is None:
            raise ValueError("at least one source locator (page or section) is required")
        return self


class Observation(Contract):
    """One explicit simulated or measured sensor reading in canonical units."""

    equipment_id: NonBlank
    sensor_id: NonBlank
    timestamp_utc: AwareDatetime
    quantity: Literal["temperature", "current", "vibration"]
    value: FiniteNumber
    unit: Literal["degC", "A", "m/s2"]
    provenance: Literal["simulated", "measured"]
    quality: Literal["valid", "suspect", "invalid"]

    @field_validator("timestamp_utc", mode="before")
    @classmethod
    def require_explicit_timestamp(cls, value: object) -> object:
        # Epoch numbers are deliberately excluded: seconds/milliseconds are ambiguous.
        if not isinstance(value, str | datetime):
            raise ValueError("timestamp must be an ISO-8601 string or aware datetime")
        return value

    @field_validator("timestamp_utc")
    @classmethod
    def normalize_utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_matching_unit(self) -> Self:
        expected = {"temperature": "degC", "current": "A", "vibration": "m/s2"}
        if self.unit != expected[self.quantity]:
            raise ValueError(f"{self.quantity} requires unit {expected[self.quantity]}")
        return self


class ObservationSeries(Contract):
    """A nonempty single-sensor series without silent sorting or provenance mixing."""

    observations: Annotated[tuple[Observation, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_series(self) -> Self:
        first = self.observations[0]
        identity = (
            first.equipment_id,
            first.sensor_id,
            first.quantity,
            first.unit,
            first.provenance,
        )
        previous = None
        for item in self.observations:
            key = (item.equipment_id, item.sensor_id, item.quantity, item.unit, item.provenance)
            if key != identity:
                raise ValueError(
                    "series must use one equipment, sensor, quantity, unit and provenance"
                )
            if previous is not None and item.timestamp_utc <= previous:
                raise ValueError("series timestamps must be strictly increasing")
            previous = item.timestamp_utc
        return self
