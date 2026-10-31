"""Synthetic 3D anchor catalog and fail-closed card projection contracts; not physical AR."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from holoassist.contracts.models import Contract, FiniteNumber, NonBlank
from holoassist.contracts.safety import Decision, SafetyCitation

SpatialRenderMode = Literal["card_and_highlight", "highlight_needs_approval", "suppressed"]


class AnchorPose3D(Contract):
    x: FiniteNumber
    y: FiniteNumber
    z: FiniteNumber
    callout_offset_y: Annotated[FiniteNumber, Field(gt=0.0, le=2.0)] = 0.24


class SpatialAnchorSpec(Contract):
    anchor_id: NonBlank
    part_id: NonBlank
    label: NonBlank
    pose: AnchorPose3D


class SpatialAnchorCatalog(Contract):
    catalog_id: NonBlank
    catalog_version: NonBlank
    equipment_id: NonBlank
    scope: Literal["synthetic_demo"]
    anchors: Annotated[tuple[SpatialAnchorSpec, ...], Field(min_length=1, max_length=20)]

    @model_validator(mode="after")
    def require_unique_anchors_and_parts(self) -> Self:
        anchor_ids = [item.anchor_id for item in self.anchors]
        part_ids = [item.part_id for item in self.anchors]
        if len(set(anchor_ids)) != len(anchor_ids):
            raise ValueError("anchor IDs must be unique")
        if len(set(part_ids)) != len(part_ids):
            raise ValueError("anchor part IDs must be unique")
        return self


class SpatialCardProjection(Contract):
    step_id: NonBlank
    part_id: NonBlank
    anchor_id: NonBlank | None = None
    anchor_label: NonBlank | None = None
    render_mode: SpatialRenderMode
    reason_code: NonBlank
    pose: AnchorPose3D | None = None
    display_text: NonBlank | None = None
    citations: tuple[SafetyCitation, ...] = ()
    source_kind: Literal["synthetic"] = "synthetic"
    guidance_allowed: Literal[False] = False

    @model_validator(mode="after")
    def enforce_projection_invariants(self) -> Self:
        if any(c.page is None and c.section is None for c in self.citations):
            raise ValueError("citation source location is required")
        if self.render_mode == "suppressed":
            if self.anchor_id is not None or self.anchor_label is not None or self.pose is not None:
                raise ValueError("suppressed projection must not expose anchor pose or identity")
            if self.display_text is not None or any(c.quote is not None for c in self.citations):
                raise ValueError("suppressed projection must not expose text or quotes")
            return self
        if self.anchor_id is None or self.anchor_label is None or self.pose is None:
            raise ValueError("active projection requires anchor identity, label, and 3D pose")
        if self.render_mode == "highlight_needs_approval":
            if self.display_text is not None or any(c.quote is not None for c in self.citations):
                raise ValueError("approval-gated highlight must not expose text or quotes")
            return self
        if not self.citations or any(c.relation != "supports" for c in self.citations):
            raise ValueError("card_and_highlight requires supporting citations")
        if not self.display_text or not any(c.quote == self.display_text for c in self.citations):
            raise ValueError("card_and_highlight display_text must match a source quote")
        return self


class SpatialProjectionReport(Contract):
    review_id: NonBlank
    analysis_request_id: NonBlank
    catalog_id: NonBlank
    catalog_version: NonBlank
    safety_status: Decision
    tracking_status: Literal["tracked", "lost", "unknown"]
    ar_session_active: Literal[False] = False
    physical_device_validated: Literal[False] = False
    guidance_allowed: Literal[False] = False
    source_kind: Literal["synthetic"] = "synthetic"
    active_anchor_count: Annotated[int, Field(strict=True, ge=0)]
    cards: Annotated[tuple[SpatialCardProjection, ...], Field(min_length=1, max_length=5)]

    @model_validator(mode="after")
    def enforce_report_invariants(self) -> Self:
        expected_active = sum(1 for card in self.cards if card.render_mode != "suppressed")
        if self.active_anchor_count != expected_active:
            raise ValueError("active_anchor_count must equal non-suppressed card count")
        if self.tracking_status != "tracked":
            if self.active_anchor_count != 0 or any(
                card.render_mode != "suppressed" for card in self.cards
            ):
                raise ValueError("non-tracked status must suppress all spatial anchors")
        if self.safety_status != "display_allowed":
            if any(card.render_mode == "card_and_highlight" for card in self.cards):
                raise ValueError("card_and_highlight requires safety_status display_allowed")
            if any(card.display_text is not None for card in self.cards) or any(
                c.quote is not None for card in self.cards for c in card.citations
            ):
                raise ValueError("non-displayable plan must redact all card text and quotes")
        return self

