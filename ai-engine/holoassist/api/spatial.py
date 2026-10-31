"""Allowlisted synthetic spatial anchor projection endpoint; no physical AR session."""

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException

from holoassist.contracts.analysis import AnalysisState
from holoassist.contracts.safety import InstructionCatalog, SafetyRequest
from holoassist.contracts.spatial import SpatialAnchorCatalog, SpatialProjectionReport
from holoassist.safety.gate import evaluate_plan
from holoassist.spatial.projector import project_safety_to_anchors

ANCHOR_CATALOG_FILE = Path("datasets/fixtures/spatial-anchor-catalog.json")
SCENARIOS: dict[str, tuple[str, str, Literal["tracked", "lost"]]] = {
    "information": ("demo-information", "demo-label", "tracked"),
    "critical": ("demo-critical", "demo-critical-part", "tracked"),
    "tracking": ("demo-information", "demo-label", "lost"),
    "unknown": ("demo-information", "unknown-part", "tracked"),
}


def spatial_router(state_json: str, catalog_json: str) -> APIRouter:
    router = APIRouter(prefix="/v1/demo/spatial", tags=["synthetic spatial anchor projection"])

    @router.get("/{scenario}", response_model=SpatialProjectionReport)
    def spatial_demo(scenario: Literal["information", "critical", "tracking", "unknown"]):
        try:
            with ANCHOR_CATALOG_FILE.open("rb") as source:
                raw = source.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError("anchor_catalog_too_large")
            anchor_catalog = SpatialAnchorCatalog.model_validate_json(raw)
            state = AnalysisState.model_validate_json(state_json)
            instruction_catalog = InstructionCatalog.model_validate_json(catalog_json)
            instruction_id, part_id, tracking = SCENARIOS[scenario]
            selection = SafetyRequest(
                review_id=f"spatial-{scenario}",
                analysis_request_id=state.request.request_id,
                tracking_status=tracking,
                steps=(
                    {
                        "step_id": "step-1",
                        "instruction_id": instruction_id,
                        "part_id": part_id,
                    },
                ),
            )
            safety_report = evaluate_plan(state, selection, instruction_catalog)
            return project_safety_to_anchors(
                safety_report,
                tracking_status=tracking,
                anchor_catalog=anchor_catalog,
                equipment_id=state.request.equipment_id,
            )
        except (OSError, ValueError, TypeError):
            raise HTTPException(503, "spatial_demo_unavailable") from None

    return router

