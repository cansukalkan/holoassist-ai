"""Read-only evaluation of a saved synthetic analysis; no agent execution."""

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException

from holoassist.agents.diagnostic import evaluate_hypotheses, matches
from holoassist.contracts.analysis import AnalysisState
from holoassist.contracts.diagnostic import DiagnosticCatalog, DiagnosticReport

ANALYSIS_FILE = Path("docs/examples/diagnostic-analysis.json")
CATALOG_FILE = Path("datasets/fixtures/diagnostic-catalog.json")
router = APIRouter(prefix="/v1/demo/diagnostic", tags=["synthetic diagnostic evidence"])


def read_model(path, model):
    with path.open("rb") as source:
        raw = source.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("demo_input_too_large")
    return model.model_validate_json(raw)


@router.get("/{scenario}", response_model=DiagnosticReport)
def diagnostic_demo(scenario: Literal["complete", "missing_counter_evidence"]):
    try:
        state = read_model(ANALYSIS_FILE, AnalysisState)
        catalog = read_model(CATALOG_FILE, DiagnosticCatalog)
        if state.request.mode != "demo" or any(
            c.source_kind != "synthetic" for c in state.evidence
        ):
            raise ValueError("synthetic_analysis_required")
        if scenario == "missing_counter_evidence":
            contrary = [
                assertion
                for rule in catalog.rules
                for assertion in rule.assertions
                if assertion.relation == "contradicts"
            ]
            if not contrary:
                raise ValueError("counter_evidence_fixture_required")
            state = state.model_copy(
                update={
                    "evidence": tuple(
                        chunk
                        for chunk in state.evidence
                        if not any(matches(assertion, chunk) for assertion in contrary)
                    )
                }
            )
        return evaluate_hypotheses(state, catalog)
    except (ValueError, TypeError, OSError):
        raise HTTPException(503, "diagnostic_demo_unavailable") from None
