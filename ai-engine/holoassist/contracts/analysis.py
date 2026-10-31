"""Validated inputs and internal state for the bounded orchestration prototype."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from holoassist.contracts.models import Contract, NonBlank, ObservationSeries
from holoassist.contracts.recognition import RecognitionResult
from holoassist.rag.chunking import DocumentChunk

Symptom = Literal["overheating", "not_rotating", "unusual_vibration"]


class AnalysisRequest(Contract):
    request_id: NonBlank
    equipment_id: NonBlank
    mode: Literal["demo", "real"]
    recognition: RecognitionResult | None = None
    symptom_codes: tuple[Symptom, ...] = ()
    sensor_series: tuple[ObservationSeries, ...] = ()

    @model_validator(mode="after")
    def reject_duplicate_symptoms(self) -> Self:
        if len(set(self.symptom_codes)) != len(self.symptom_codes):
            raise ValueError("symptom codes must be unique")
        return self


class AgentError(Contract):
    node: Literal["supervisor", "knowledge", "validation"]
    code: NonBlank


class TraceEvent(Contract):
    step: Annotated[int, Field(strict=True, ge=1, le=3)]
    node: Literal["supervisor", "knowledge", "validation"]
    code: NonBlank


class AnalysisState(Contract):
    guidance_allowed: Literal[False] = False
    request: AnalysisRequest
    status: Literal["running", "needs_information", "blocked", "ready_for_diagnostic"] = "running"
    evidence: Annotated[tuple[DocumentChunk, ...], Field(max_length=3)] = ()
    missing_information: tuple[NonBlank, ...] = ()
    errors: tuple[AgentError, ...] = ()
    trace: tuple[TraceEvent, ...] = ()

    @model_validator(mode="after")
    def enforce_consistency(self) -> Self:
        if len(self.trace) > 3 or [item.step for item in self.trace] != list(
            range(1, len(self.trace) + 1)
        ):
            raise ValueError("trace must have at most three contiguous steps")
        if self.errors and self.status != "blocked":
            raise ValueError("errors require blocked status")
        if self.status == "blocked" and not self.errors:
            raise ValueError("blocked state requires an error code")
        if bool(self.missing_information) != (self.status == "needs_information"):
            raise ValueError("missing information is required only for needs_information")
        seen = set()
        revisions = {}
        expected_kind = "synthetic" if self.request.mode == "demo" else "manufacturer"
        for item in self.evidence:
            if item.equipment_id != self.request.equipment_id or item.source_kind != expected_kind:
                raise ValueError("evidence equipment/source kind does not match request")
            if item.evidence_id in seen:
                raise ValueError("duplicate evidence ID")
            seen.add(item.evidence_id)
            revision = (item.document_version, item.checksum)
            if revisions.setdefault(item.document_id, revision) != revision:
                raise ValueError("conflicting document revisions")
        if self.status == "ready_for_diagnostic":
            recognition = self.request.recognition
            if (
                recognition is None
                or recognition.status != "matched"
                or recognition.equipment_id != self.request.equipment_id
                or not self.request.symptom_codes
                or not self.evidence
                or recognition.reference_kind
                != ("synthetic" if self.request.mode == "demo" else "real")
            ):
                raise ValueError("diagnostic handoff needs matched identity, symptoms and evidence")
            expected_provenance = "simulated" if self.request.mode == "demo" else "measured"
            for series in self.request.sensor_series:
                for item in series.observations:
                    if (
                        item.equipment_id != self.request.equipment_id
                        or item.provenance != expected_provenance
                        or item.quality != "valid"
                    ):
                        raise ValueError("diagnostic handoff has invalid sensor context")
        return self
