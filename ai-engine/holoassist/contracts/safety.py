"""Synthetic instruction-display gate contracts; not physical operation authorization."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from holoassist.contracts.diagnostic import SourceAssertion
from holoassist.contracts.models import Checksum, Contract, NonBlank

Risk = Literal["informational", "critical", "prohibited", "unknown"]
Decision = Literal["display_allowed", "needs_information", "needs_approval", "blocked"]


class CatalogInstruction(Contract):
    instruction_id: NonBlank
    part_id: NonBlank
    risk: Risk
    text: NonBlank
    sources: Annotated[tuple[SourceAssertion, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def require_exact_catalog_text(self) -> Self:
        supports = [item for item in self.sources if item.relation == "supports"]
        if not any(item.quote == self.text for item in supports):
            raise ValueError("instruction text must equal a complete supporting source quote")
        if len({item.assertion_id for item in self.sources}) != len(self.sources):
            raise ValueError("source assertion IDs must be unique per instruction")
        return self


class InstructionCatalog(Contract):
    catalog_id: NonBlank
    catalog_version: NonBlank
    equipment_id: NonBlank
    scope: Literal["synthetic_demo"]
    instructions: Annotated[tuple[CatalogInstruction, ...], Field(min_length=1, max_length=20)]

    @model_validator(mode="after")
    def require_unique_instructions(self) -> Self:
        ids = [item.instruction_id for item in self.instructions]
        if len(set(ids)) != len(ids):
            raise ValueError("instruction IDs must be unique")
        return self


class RequestedStep(Contract):
    step_id: NonBlank
    instruction_id: NonBlank
    part_id: NonBlank


class SafetyRequest(Contract):
    review_id: NonBlank
    analysis_request_id: NonBlank
    tracking_status: Literal["tracked", "lost", "unknown"]
    steps: Annotated[tuple[RequestedStep, ...], Field(min_length=1, max_length=5)]

    @model_validator(mode="after")
    def require_unique_steps(self) -> Self:
        if len({item.step_id for item in self.steps}) != len(self.steps):
            raise ValueError("step IDs must be unique")
        if len({item.instruction_id for item in self.steps}) != len(self.steps):
            raise ValueError("instructions must not repeat")
        return self


class SafetyCitation(Contract):
    assertion_id: NonBlank
    evidence_id: NonBlank
    document_id: NonBlank
    document_version: NonBlank
    checksum: Checksum
    page: Annotated[int, Field(strict=True, ge=1)] | None = None
    section: NonBlank | None = None
    relation: Literal["supports", "contradicts"]
    quote: NonBlank | None = None


class StepDecision(Contract):
    step_id: NonBlank
    instruction_id: NonBlank
    part_id: NonBlank
    risk: Risk
    status: Decision
    reason_code: NonBlank
    citations: tuple[SafetyCitation, ...] = ()
    display_text: NonBlank | None = None


class SafetyReport(Contract):
    review_id: NonBlank
    analysis_request_id: NonBlank
    catalog_id: NonBlank
    catalog_version: NonBlank
    context_digest: Checksum
    source_kind: Literal["synthetic"] = "synthetic"
    guidance_allowed: Literal[False] = False
    status: Decision
    reason_code: NonBlank
    steps: Annotated[tuple[StepDecision, ...], Field(min_length=1, max_length=5)]

    @model_validator(mode="after")
    def enforce_atomic_display(self) -> Self:
        priority = {"display_allowed": 0, "needs_information": 1, "needs_approval": 2, "blocked": 3}
        expected_status = max((item.status for item in self.steps), key=priority.__getitem__)
        if self.status != expected_status:
            raise ValueError("plan status must preserve the most restrictive step decision")
        if any(c.page is None and c.section is None for s in self.steps for c in s.citations):
            raise ValueError("citation source location is required")
        all_allowed = all(item.status == "display_allowed" for item in self.steps)
        if (self.status == "display_allowed") != all_allowed:
            raise ValueError("report may allow display only when every step is allowed")
        if self.status != "display_allowed" and any(item.display_text for item in self.steps):
            raise ValueError("rejected plan must not expose instruction text")
        if self.status != "display_allowed" and any(
            c.quote for s in self.steps for c in s.citations
        ):
            raise ValueError("rejected plan must not expose instruction quotes")
        for item in self.steps:
            if item.status == "display_allowed":
                if item.risk != "informational" or not item.citations:
                    raise ValueError("only source-bound informational steps may allow demo display")
                if any(citation.relation != "supports" for citation in item.citations):
                    raise ValueError("allowed step cannot contain contradictory sources")
            if self.status == "display_allowed":
                if not item.display_text or not any(
                    c.quote == item.display_text for c in item.citations
                ):
                    raise ValueError("display text must match a source quote")
        return self
