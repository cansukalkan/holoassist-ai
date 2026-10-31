"""Fail-closed projection of SafetyReport decisions onto synthetic 3D rig anchors."""

from collections.abc import Mapping
from typing import Literal

from holoassist.contracts.safety import SafetyCitation, SafetyReport
from holoassist.contracts.spatial import (
    SpatialAnchorCatalog,
    SpatialCardProjection,
    SpatialProjectionReport,
)


def _redact_citations(items: tuple[SafetyCitation, ...]) -> tuple[SafetyCitation, ...]:
    return tuple(item.model_copy(update={"quote": None}) for item in items)


def project_safety_to_anchors(
    report: SafetyReport | Mapping,
    *,
    tracking_status: Literal["tracked", "lost", "unknown"],
    anchor_catalog: SpatialAnchorCatalog | Mapping,
    equipment_id: str = "synthetic-rig",
) -> SpatialProjectionReport:
    if tracking_status not in ("tracked", "lost", "unknown"):
        raise ValueError("tracking_status must be tracked, lost, or unknown")
    if not isinstance(equipment_id, str) or not equipment_id.strip():
        raise ValueError("equipment_id must be nonblank")
    validated_report = SafetyReport.model_validate(
        report.model_dump() if isinstance(report, SafetyReport) else report
    )
    validated_catalog = SpatialAnchorCatalog.model_validate(
        anchor_catalog.model_dump()
        if isinstance(anchor_catalog, SpatialAnchorCatalog)
        else anchor_catalog
    )
    if validated_catalog.scope != "synthetic_demo" or validated_report.source_kind != "synthetic":
        raise ValueError("synthetic_demo_scope_required")
    equipment_mismatch = validated_catalog.equipment_id != equipment_id.strip()
    anchors_by_part = {anchor.part_id: anchor for anchor in validated_catalog.anchors}

    cards: list[SpatialCardProjection] = []
    for step in validated_report.steps:
        if equipment_mismatch:
            cards.append(
                SpatialCardProjection(
                    step_id=step.step_id,
                    part_id=step.part_id,
                    render_mode="suppressed",
                    reason_code="anchor_equipment_mismatch",
                    citations=_redact_citations(step.citations),
                )
            )
            continue
        if tracking_status != "tracked":
            cards.append(
                SpatialCardProjection(
                    step_id=step.step_id,
                    part_id=step.part_id,
                    render_mode="suppressed",
                    reason_code="tracking_lost_anchor_cleared",
                    citations=_redact_citations(step.citations),
                )
            )
            continue
        anchor = anchors_by_part.get(step.part_id)
        if anchor is None:
            cards.append(
                SpatialCardProjection(
                    step_id=step.step_id,
                    part_id=step.part_id,
                    render_mode="suppressed",
                    reason_code="unknown_anchor_part",
                    citations=_redact_citations(step.citations),
                )
            )
            continue
        if (
            validated_report.status == "display_allowed"
            and step.status == "display_allowed"
            and step.risk == "informational"
            and step.display_text is not None
        ):
            cards.append(
                SpatialCardProjection(
                    step_id=step.step_id,
                    part_id=step.part_id,
                    anchor_id=anchor.anchor_id,
                    anchor_label=anchor.label,
                    render_mode="card_and_highlight",
                    reason_code="verified_synthetic_anchor_bound",
                    pose=anchor.pose,
                    display_text=step.display_text,
                    citations=step.citations,
                )
            )
        elif step.status == "needs_approval" and step.risk == "critical":
            cards.append(
                SpatialCardProjection(
                    step_id=step.step_id,
                    part_id=step.part_id,
                    anchor_id=anchor.anchor_id,
                    anchor_label=anchor.label,
                    render_mode="highlight_needs_approval",
                    reason_code="approval_required_text_redacted",
                    pose=anchor.pose,
                    display_text=None,
                    citations=_redact_citations(step.citations),
                )
            )
        else:
            cards.append(
                SpatialCardProjection(
                    step_id=step.step_id,
                    part_id=step.part_id,
                    render_mode="suppressed",
                    reason_code=step.reason_code,
                    citations=_redact_citations(step.citations),
                )
            )

    active_count = sum(1 for card in cards if card.render_mode != "suppressed")
    return SpatialProjectionReport(
        review_id=validated_report.review_id,
        analysis_request_id=validated_report.analysis_request_id,
        catalog_id=validated_catalog.catalog_id,
        catalog_version=validated_catalog.catalog_version,
        safety_status=validated_report.status,
        tracking_status=tracking_status,
        active_anchor_count=active_count,
        cards=tuple(cards),
    )
