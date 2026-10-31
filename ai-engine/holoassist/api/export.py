"""Build a bounded, nonpersistent export from server-owned demo inputs."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Response

from holoassist.api.diagnostic import diagnostic_demo
from holoassist.api.sensors import sensor_demo
from holoassist.contracts.analysis import AnalysisState
from holoassist.contracts.export import (
    DemoExport,
    DemoSelection,
    DiagnosticScenario,
    SafetyScenario,
    SensorScenario,
)
from holoassist.contracts.safety import InstructionCatalog, SafetyRequest
from holoassist.safety.gate import evaluate_plan

SCENARIOS = {
    "information": ("demo-information", "demo-label", "tracked"),
    "critical": ("demo-critical", "demo-critical-part", "tracked"),
    "tracking": ("demo-information", "demo-label", "lost"),
    "unknown": ("demo-information", "unknown-part", "tracked"),
}


def export_router(state_json: str, catalog_json: str):
    router = APIRouter(tags=["synthetic demo export"])

    @router.get("/v1/demo/report", response_model=DemoExport)
    def download(
        response: Response,
        safety: SafetyScenario = "information",
        sensor: SensorScenario = "current",
        diagnostic: DiagnosticScenario = "complete",
    ):
        state = AnalysisState.model_validate_json(state_json)
        instruction, part, tracking = SCENARIOS[safety]
        selection = SafetyRequest(
            review_id=f"export-{safety}",
            analysis_request_id=state.request.request_id,
            tracking_status=tracking,
            steps=({"step_id": "step-1", "instruction_id": instruction, "part_id": part},),
        )
        now = datetime.now(UTC)
        result = DemoExport(
            export_id=uuid4(),
            generated_utc=now,
            selection=DemoSelection(safety=safety, sensor=sensor, diagnostic=diagnostic),
            safety=evaluate_plan(
                state, selection, InstructionCatalog.model_validate_json(catalog_json)
            ),
            sensor=sensor_demo(sensor),
            diagnostic=diagnostic_demo(diagnostic),
        )
        response.headers["Content-Disposition"] = (
            f'attachment; filename="holoassist-demo-{now:%Y%m%dT%H%M%SZ}.json"'
        )
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return result

    return router
