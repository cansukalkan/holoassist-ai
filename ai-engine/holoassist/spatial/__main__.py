"""CLI verification helper for synthetic 3D anchor binding."""

import argparse
from pathlib import Path

from holoassist.contracts.analysis import AnalysisState
from holoassist.contracts.safety import InstructionCatalog, SafetyRequest
from holoassist.contracts.spatial import SpatialAnchorCatalog
from holoassist.safety.gate import evaluate_plan
from holoassist.spatial.projector import project_safety_to_anchors

SCENARIOS = {
    "information": ("demo-information", "demo-label", "tracked"),
    "critical": ("demo-critical", "demo-critical-part", "tracked"),
    "tracking": ("demo-information", "demo-label", "lost"),
    "unknown": ("demo-information", "unknown-part", "tracked"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate synthetic spatial anchor projection.")
    parser.add_argument(
        "--scenario",
        choices=tuple(SCENARIOS.keys()),
        default="information",
    )
    args = parser.parse_args()
    state = AnalysisState.model_validate_json(
        Path("docs/examples/safety-analysis.json").read_bytes()
    )
    instruction_catalog = InstructionCatalog.model_validate_json(
        Path("datasets/fixtures/instruction-catalog.json").read_bytes()
    )
    anchor_catalog = SpatialAnchorCatalog.model_validate_json(
        Path("datasets/fixtures/spatial-anchor-catalog.json").read_bytes()
    )
    instruction_id, part_id, tracking = SCENARIOS[args.scenario]
    request = SafetyRequest(
        review_id=f"spatial-{args.scenario}",
        analysis_request_id=state.request.request_id,
        tracking_status=tracking,
        steps=({"step_id": "step-1", "instruction_id": instruction_id, "part_id": part_id},),
    )
    safety = evaluate_plan(state, request, instruction_catalog)
    projection = project_safety_to_anchors(
        safety,
        tracking_status=tracking,
        anchor_catalog=anchor_catalog,
        equipment_id=state.request.equipment_id,
    )
    print(projection.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
