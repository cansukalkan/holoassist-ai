"""Downloadable independent demo sections; never an end-to-end diagnosis."""

from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, model_validator

from holoassist.contracts.analytics import SensorDemoResult
from holoassist.contracts.diagnostic import DiagnosticReport
from holoassist.contracts.models import Contract
from holoassist.contracts.safety import SafetyReport

SafetyScenario = Literal["information", "critical", "tracking", "unknown"]
SensorScenario = Literal["current", "temperature", "vibration"]
DiagnosticScenario = Literal["complete", "missing_counter_evidence"]


class DemoSelection(Contract):
    safety: SafetyScenario
    sensor: SensorScenario
    diagnostic: DiagnosticScenario


class DemoExport(Contract):
    export_id: UUID
    generated_utc: AwareDatetime
    scope: Literal["synthetic_demo"] = "synthetic_demo"
    independent_sections: Literal[True] = True
    guidance_allowed: Literal[False] = False
    selection: DemoSelection
    safety: SafetyReport
    sensor: SensorDemoResult
    diagnostic: DiagnosticReport

    @model_validator(mode="after")
    def require_selected_sections(self) -> Self:
        if self.sensor.fixture_id != self.selection.sensor:
            raise ValueError("export sensor selection mismatch")
        if self.safety.review_id != f"export-{self.selection.safety}":
            raise ValueError("export safety selection mismatch")
        return self
