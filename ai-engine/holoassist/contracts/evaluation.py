"""Contracts for reproducible synthetic fixture benchmarks; never real-hardware claims."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from holoassist.contracts.models import Checksum, Contract, FiniteNumber, NonBlank


class VisionBenchmarkSummary(Contract):
    frames_evaluated: Annotated[int, Field(strict=True, ge=1)]
    true_positives: Annotated[int, Field(strict=True, ge=0)]
    true_negatives: Annotated[int, Field(strict=True, ge=0)]
    false_positives: Annotated[int, Field(strict=True, ge=0)]
    false_negatives: Annotated[int, Field(strict=True, ge=0)]
    precision: Annotated[FiniteNumber, Field(ge=0.0, le=1.0)]
    recall: Annotated[FiniteNumber, Field(ge=0.0, le=1.0)]
    f1: Annotated[FiniteNumber, Field(ge=0.0, le=1.0)]
    warped_max_corner_error_px: Annotated[FiniteNumber, Field(ge=0.0)]
    calibrated_probabilities: Literal[False] = False


class RagBenchmarkSummary(Contract):
    documents_indexed: Annotated[int, Field(strict=True, ge=1)]
    chunks_indexed: Annotated[int, Field(strict=True, ge=1)]
    queries_executed: Annotated[int, Field(strict=True, ge=1)]
    citation_locator_rate: Annotated[FiniteNumber, Field(ge=0.0, le=1.0)]
    unsupported_claim_count: Annotated[int, Field(strict=True, ge=0)]
    cross_equipment_leakage_count: Annotated[int, Field(strict=True, ge=0)]
    cache_hits: Annotated[int, Field(strict=True, ge=0)]
    cache_misses: Annotated[int, Field(strict=True, ge=0)]
    cold_query_ms: Annotated[FiniteNumber, Field(ge=0.0)]
    warm_query_ms: Annotated[FiniteNumber, Field(ge=0.0)]
    corpus_digest: Checksum


class DiagnosticBenchmarkSummary(Contract):
    sensor_series_verified: Annotated[int, Field(strict=True, ge=1)]
    supervisor_handoff_ready: bool
    contradiction_preserved: bool
    missing_counter_evidence_abstained: bool


class SafetySpatialBenchmarkSummary(Contract):
    checks_total: Annotated[int, Field(strict=True, ge=1)]
    checks_passed: Annotated[int, Field(strict=True, ge=0)]
    safety_violations: Annotated[int, Field(strict=True, ge=0)]
    tracking_loss_suppressed: bool
    unknown_anchor_suppressed: bool
    replay_token_rejected: bool
    digest_tamper_rejected: bool

    @model_validator(mode="after")
    def require_consistent_counts(self) -> Self:
        if self.checks_passed > self.checks_total:
            raise ValueError("checks_passed cannot exceed checks_total")
        if self.safety_violations != self.checks_total - self.checks_passed:
            raise ValueError("safety_violations must equal failed safety checks")
        return self


class OpenHardwareGate(Contract):
    gate_id: NonBlank
    status: Literal["open_hardware_dependency"] = "open_hardware_dependency"
    summary: NonBlank


class SyntheticBenchmarkReport(Contract):
    suite_id: NonBlank = "holoassist-synthetic-benchmark-v1"
    scope: Literal["synthetic_fixture_benchmark"] = "synthetic_fixture_benchmark"
    equipment_id: NonBlank = "synthetic-rig"
    source_kind: Literal["synthetic"] = "synthetic"
    provenance: Literal["simulated"] = "simulated"
    physical_device_validated: Literal[False] = False
    calibrated_probabilities: Literal[False] = False
    guidance_allowed: Literal[False] = False
    all_synthetic_gates_passed: bool
    total_duration_ms: Annotated[FiniteNumber, Field(ge=0.0)]
    vision: VisionBenchmarkSummary
    rag: RagBenchmarkSummary
    diagnostic: DiagnosticBenchmarkSummary
    safety_spatial: SafetySpatialBenchmarkSummary
    fixture_digests: dict[NonBlank, Checksum]
    open_hardware_gates: Annotated[tuple[OpenHardwareGate, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def verify_overall_gate_flag(self) -> Self:
        expected = (
            self.vision.false_positives == 0
            and self.vision.false_negatives == 0
            and self.rag.unsupported_claim_count == 0
            and self.rag.cross_equipment_leakage_count == 0
            and self.rag.citation_locator_rate == 1.0
            and self.diagnostic.supervisor_handoff_ready
            and self.diagnostic.contradiction_preserved
            and self.diagnostic.missing_counter_evidence_abstained
            and self.safety_spatial.safety_violations == 0
        )
        if self.all_synthetic_gates_passed != expected:
            raise ValueError("all_synthetic_gates_passed must match subsystem verification results")
        return self

