"""Persistent approval metadata for synthetic demonstrations only."""

from typing import Literal, Self

from pydantic import AwareDatetime, model_validator

from holoassist.contracts.models import Checksum, Contract, NonBlank


class ApprovalRecord(Contract):
    approval_id: NonBlank
    review_id: NonBlank
    analysis_request_id: NonBlank
    context_digest: Checksum
    scope: Literal["synthetic_demo"] = "synthetic_demo"
    guidance_allowed: Literal[False] = False
    status: Literal["pending", "approved", "rejected", "consumed", "expired", "invalidated"]
    created_utc: AwareDatetime
    updated_utc: AwareDatetime
    expires_utc: AwareDatetime
    decided_by: NonBlank | None = None
    decided_utc: AwareDatetime | None = None
    consumed_utc: AwareDatetime | None = None
    reason_code: NonBlank

    @model_validator(mode="after")
    def require_consistent_lifecycle(self) -> Self:
        if self.expires_utc <= self.created_utc or self.updated_utc < self.created_utc:
            raise ValueError("invalid approval timestamps")
        if self.status in ("approved", "rejected", "consumed") and (
            not self.decided_by or not self.decided_utc
        ):
            raise ValueError("decision metadata is required")
        if bool(self.decided_by) != bool(self.decided_utc):
            raise ValueError("reviewer and decision timestamp must appear together")
        if (self.status == "consumed") != (self.consumed_utc is not None):
            raise ValueError("consumption timestamp must match state")
        return self


class DemoResumeReceipt(Contract):
    approval_id: NonBlank
    context_digest: Checksum
    scope: Literal["synthetic_demo"] = "synthetic_demo"
    guidance_allowed: Literal[False] = False
    status: Literal["demo_continuation_recorded"] = "demo_continuation_recorded"
    consumed_utc: AwareDatetime
