"""Fail-closed synthetic instruction catalog gate, independent of the agent graph."""

import hashlib
import json
from collections.abc import Mapping

from holoassist.agents.diagnostic import matches
from holoassist.contracts.analysis import AnalysisState
from holoassist.contracts.safety import InstructionCatalog, SafetyReport, SafetyRequest


def evaluate_plan(
    analysis: AnalysisState | Mapping,
    request: SafetyRequest | Mapping,
    catalog: InstructionCatalog | Mapping,
) -> SafetyReport:
    state = AnalysisState.model_validate(
        analysis.model_dump() if isinstance(analysis, AnalysisState) else analysis
    )
    selection = SafetyRequest.model_validate(
        request.model_dump() if isinstance(request, SafetyRequest) else request
    )
    allowed_catalog = InstructionCatalog.model_validate(
        catalog.model_dump() if isinstance(catalog, InstructionCatalog) else catalog
    )
    payload = {
        "analysis": state.model_dump(mode="json"),
        "request": selection.model_dump(mode="json"),
        "catalog": allowed_catalog.model_dump(mode="json"),
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    known = {item.instruction_id: item for item in allowed_catalog.instructions}
    global_error = None
    if state.request.mode != "demo":
        global_error = "real_mode_not_supported"
    elif state.request.equipment_id != allowed_catalog.equipment_id:
        global_error = "catalog_equipment_mismatch"
    elif selection.analysis_request_id != state.request.request_id:
        global_error = "analysis_request_mismatch"
    elif state.status != "ready_for_diagnostic":
        global_error = "analysis_not_ready"
    decisions = []
    for step in selection.steps:
        instruction = known.get(step.instruction_id)
        result = dict(
            step_id=step.step_id,
            instruction_id=step.instruction_id,
            part_id=step.part_id,
            risk=instruction.risk if instruction else "unknown",
            status="blocked",
            reason_code=global_error or "unknown_instruction",
            citations=(),
            display_text=None,
        )
        if global_error:
            decisions.append(result)
            continue
        if instruction is None:
            decisions.append(result)
            continue
        if instruction.part_id != step.part_id:
            result["reason_code"] = "part_mismatch"
        elif instruction.risk in ("unknown", "prohibited"):
            result["reason_code"] = "risk_not_permitted"
        else:
            citations = []
            missing = False
            contradiction = False
            for assertion in instruction.sources:
                found = [chunk for chunk in state.evidence if matches(assertion, chunk)]
                if not found:
                    missing = True
                if assertion.relation == "contradicts" and found:
                    contradiction = True
                for chunk in sorted(found, key=lambda item: item.evidence_id):
                    citations.append(assertion.model_dump() | {"evidence_id": chunk.evidence_id})
            if contradiction:
                result["reason_code"] = "contradictory_source"
            elif missing:
                result["reason_code"] = "source_binding_missing"
            elif selection.tracking_status != "tracked":
                result |= dict(status="needs_information", reason_code="tracking_required")
            elif instruction.risk == "critical":
                result |= dict(status="needs_approval", reason_code="persistent_approval_required")
            else:
                result |= dict(
                    status="display_allowed",
                    reason_code="synthetic_information_only",
                    display_text=instruction.text,
                )
            result["citations"] = tuple(citations)
        decisions.append(result)
    priority = {"display_allowed": 0, "needs_information": 1, "needs_approval": 2, "blocked": 3}
    status = max((item["status"] for item in decisions), key=priority.__getitem__)
    if status != "display_allowed":
        for item in decisions:
            item["display_text"] = None
            for citation in item["citations"]:
                citation["quote"] = None
    return SafetyReport(
        review_id=selection.review_id,
        analysis_request_id=selection.analysis_request_id,
        catalog_id=allowed_catalog.catalog_id,
        catalog_version=allowed_catalog.catalog_version,
        context_digest=digest,
        status=status,
        reason_code="synthetic_information_only"
        if status == "display_allowed"
        else "plan_not_displayable",
        steps=tuple(decisions),
    )
