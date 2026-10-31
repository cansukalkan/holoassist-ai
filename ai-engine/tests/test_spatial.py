"""Tests for synthetic 3D anchor catalog, fail-closed projection, and /v1/demo/spatial."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from holoassist.api import spatial as api_spatial
from holoassist.api.app import local_app
from holoassist.contracts.analysis import AnalysisState
from holoassist.contracts.safety import InstructionCatalog, SafetyRequest
from holoassist.contracts.spatial import (
    AnchorPose3D,
    SpatialAnchorCatalog,
    SpatialCardProjection,
    SpatialProjectionReport,
)
from holoassist.safety.gate import evaluate_plan
from holoassist.spatial.projector import project_safety_to_anchors
from pydantic import ValidationError


@pytest.fixture
def fixtures():
    state = AnalysisState.model_validate_json(
        Path("docs/examples/safety-analysis.json").read_bytes()
    )
    instructions = InstructionCatalog.model_validate_json(
        Path("datasets/fixtures/instruction-catalog.json").read_bytes()
    )
    anchors = SpatialAnchorCatalog.model_validate_json(
        Path("datasets/fixtures/spatial-anchor-catalog.json").read_bytes()
    )
    return state, instructions, anchors


def test_informational_step_binds_verified_anchor(fixtures):
    state, instructions, anchors = fixtures
    req = SafetyRequest(
        review_id="spatial-test-info",
        analysis_request_id=state.request.request_id,
        tracking_status="tracked",
        steps=(
            {
                "step_id": "step-1",
                "instruction_id": "demo-information",
                "part_id": "demo-label",
            },
        ),
    )
    safety = evaluate_plan(state, req, instructions)
    report = project_safety_to_anchors(safety, tracking_status="tracked", anchor_catalog=anchors)
    assert report.ar_session_active is False
    assert report.physical_device_validated is False
    assert report.guidance_allowed is False
    assert report.active_anchor_count == 1
    card = report.cards[0]
    assert card.render_mode == "card_and_highlight"
    assert card.anchor_id == "anchor-demo-label"
    assert card.pose == AnchorPose3D(x=0.0, y=0.64, z=0.0, callout_offset_y=0.24)
    assert card.display_text == safety.steps[0].display_text


def test_critical_step_highlights_part_as_needs_approval_without_text(fixtures):
    state, instructions, anchors = fixtures
    req = SafetyRequest(
        review_id="spatial-test-crit",
        analysis_request_id=state.request.request_id,
        tracking_status="tracked",
        steps=(
            {
                "step_id": "step-1",
                "instruction_id": "demo-critical",
                "part_id": "demo-critical-part",
            },
        ),
    )
    safety = evaluate_plan(state, req, instructions)
    report = project_safety_to_anchors(safety, tracking_status="tracked", anchor_catalog=anchors)
    assert report.active_anchor_count == 1
    card = report.cards[0]
    assert card.render_mode == "highlight_needs_approval"
    assert card.anchor_id == "anchor-demo-critical-part"
    assert card.display_text is None
    assert all(c.quote is None for c in card.citations)


def test_tracking_lost_clears_all_anchors(fixtures):
    state, instructions, anchors = fixtures
    req = SafetyRequest(
        review_id="spatial-test-lost",
        analysis_request_id=state.request.request_id,
        tracking_status="lost",
        steps=(
            {
                "step_id": "step-1",
                "instruction_id": "demo-information",
                "part_id": "demo-label",
            },
        ),
    )
    safety = evaluate_plan(state, req, instructions)
    report = project_safety_to_anchors(safety, tracking_status="lost", anchor_catalog=anchors)
    assert report.active_anchor_count == 0
    assert report.cards[0].render_mode == "suppressed"
    assert report.cards[0].pose is None
    assert report.cards[0].anchor_id is None


def test_unknown_part_and_equipment_mismatch_suppress_projection(fixtures):
    state, instructions, anchors = fixtures
    req = SafetyRequest(
        review_id="spatial-test-unknown",
        analysis_request_id=state.request.request_id,
        tracking_status="tracked",
        steps=(
            {
                "step_id": "step-1",
                "instruction_id": "demo-information",
                "part_id": "unknown-part",
            },
        ),
    )
    safety = evaluate_plan(state, req, instructions)
    report = project_safety_to_anchors(safety, tracking_status="tracked", anchor_catalog=anchors)
    assert report.active_anchor_count == 0
    assert report.cards[0].reason_code == "unknown_anchor_part"

    mismatch = project_safety_to_anchors(
        safety,
        tracking_status="tracked",
        anchor_catalog=anchors,
        equipment_id="other-rig",
    )
    assert mismatch.active_anchor_count == 0
    assert mismatch.cards[0].reason_code == "anchor_equipment_mismatch"


def test_contract_rejects_inconsistent_spatial_payload(fixtures):
    _, _, anchors = fixtures
    with pytest.raises(ValidationError):
        SpatialCardProjection(
            step_id="step-1",
            part_id="demo-label",
            anchor_id="anchor-demo-label",
            anchor_label="Plaka",
            render_mode="suppressed",
            reason_code="invalid",
            pose=anchors.anchors[0].pose,
        )


def test_spatial_http_endpoint_and_fail_closed_behavior(monkeypatch, tmp_path):
    with TestClient(local_app()) as client:
        info = client.get("/v1/demo/spatial/information")
        assert info.status_code == 200
        parsed = SpatialProjectionReport.model_validate(info.json())
        assert parsed.active_anchor_count == 1
        assert parsed.cards[0].anchor_id == "anchor-demo-label"

        lost = client.get("/v1/demo/spatial/tracking")
        assert lost.status_code == 200
        assert lost.json()["active_anchor_count"] == 0

        traversal = client.get("/v1/demo/spatial/invalid")
        assert traversal.status_code == 422

        monkeypatch.setattr(api_spatial, "ANCHOR_CATALOG_FILE", tmp_path / "missing.json")
        unavailable = client.get("/v1/demo/spatial/information")
        assert unavailable.status_code == 503
        assert unavailable.json()["code"] == "spatial_demo_unavailable"
