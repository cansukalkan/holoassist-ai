"""Three-node LangGraph prototype: guard, retrieve, validate, then stop."""

from collections.abc import Mapping
from typing import Protocol, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from holoassist.contracts.analysis import AnalysisRequest, AnalysisState, TraceEvent
from holoassist.rag.chunking import DocumentChunk

QUERY_TERMS = {
    "overheating": "temperature sıcaklık",
    "not_rotating": "current akım",
    "unusual_vibration": "vibration titreşim",
}


class Retriever(Protocol):
    def search(
        self, query: str, *, equipment_id: str, top_k: int = 3
    ) -> tuple[DocumentChunk, ...]: ...


class Envelope(TypedDict):
    analysis: AnalysisState


def transition(state: AnalysisState, node: str, code: str, **changes) -> Envelope:
    event = TraceEvent(step=len(state.trace) + 1, node=node, code=code)
    payload = state.model_dump() | changes | {"trace": (*state.trace, event)}
    return {"analysis": AnalysisState.model_validate(payload)}


def guard(envelope: Envelope) -> Envelope:
    state = envelope["analysis"]
    request = state.request
    recognition = request.recognition
    if recognition is None or recognition.status != "matched":
        return transition(
            state,
            "supervisor",
            "identity_required",
            status="needs_information",
            missing_information=("matched_equipment_reference",),
        )
    if recognition.equipment_id != request.equipment_id:
        return transition(
            state,
            "supervisor",
            "identity_mismatch",
            status="blocked",
            errors=({"node": "supervisor", "code": "identity_mismatch"},),
        )
    expected_kind = "synthetic" if request.mode == "demo" else "real"
    expected_data = "simulated" if request.mode == "demo" else "measured"
    if recognition.reference_kind != expected_kind:
        return transition(
            state,
            "supervisor",
            "reference_mode_mismatch",
            status="blocked",
            errors=({"node": "supervisor", "code": "reference_mode_mismatch"},),
        )
    for series in request.sensor_series:
        for item in series.observations:
            if item.equipment_id != request.equipment_id or item.provenance != expected_data:
                return transition(
                    state,
                    "supervisor",
                    "sensor_context_mismatch",
                    status="blocked",
                    errors=({"node": "supervisor", "code": "sensor_context_mismatch"},),
                )
            if item.quality != "valid":
                return transition(
                    state,
                    "supervisor",
                    "valid_sensor_data_required",
                    status="needs_information",
                    missing_information=("valid_sensor_data",),
                )
    if not request.symptom_codes:
        return transition(
            state,
            "supervisor",
            "symptoms_required",
            status="needs_information",
            missing_information=("symptom_codes",),
        )
    return transition(state, "supervisor", "retrieve_sources")


def build_graph(retriever: Retriever):
    def knowledge(envelope: Envelope) -> Envelope:
        state = envelope["analysis"]
        query = " ".join(QUERY_TERMS[code] for code in state.request.symptom_codes)
        try:
            raw = retriever.search(query, equipment_id=state.request.equipment_id, top_k=3)
        except Exception:
            # Do not expose exception text, paths, keys or external document instructions.
            return transition(
                state,
                "knowledge",
                "retrieval_failed",
                status="blocked",
                errors=({"node": "knowledge", "code": "retrieval_failed"},),
            )
        try:
            if not isinstance(raw, tuple | list) or len(raw) > 3:
                raise ValueError("retriever must return at most three validated chunks")
            chunks = tuple(DocumentChunk.model_validate(item.model_dump()) for item in raw)
            return transition(state, "knowledge", "sources_retrieved", evidence=chunks)
        except (ValueError, TypeError, AttributeError, ValidationError):
            return transition(
                state,
                "knowledge",
                "invalid_retrieval",
                status="blocked",
                errors=({"node": "knowledge", "code": "invalid_retrieval"},),
            )

    def validate(envelope: Envelope) -> Envelope:
        state = envelope["analysis"]
        if not state.evidence:
            return transition(
                state,
                "validation",
                "sources_required",
                status="needs_information",
                missing_information=("equipment_specific_sources",),
            )
        return transition(
            state, "validation", "diagnostic_handoff_ready", status="ready_for_diagnostic"
        )

    def route(envelope: Envelope) -> str:
        return "continue" if envelope["analysis"].status == "running" else "stop"

    builder = StateGraph(Envelope)
    builder.add_node("supervisor", guard)
    builder.add_node("knowledge", knowledge)
    builder.add_node("validation", validate)
    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges("supervisor", route, {"continue": "knowledge", "stop": END})
    builder.add_conditional_edges("knowledge", route, {"continue": "validation", "stop": END})
    builder.add_edge("validation", END)
    return builder.compile()


def run_analysis(request: AnalysisRequest | Mapping, retriever: Retriever) -> AnalysisState:
    """Start fresh; callers cannot inject evidence, trace, errors or approval state.

    Local adapter API, not authentication or proof that a recognition was measured.
    Graph is acyclic, makes at most one retrieval call, and has no automatic retries.
    """
    raw = request.model_dump() if isinstance(request, AnalysisRequest) else request
    validated = AnalysisRequest.model_validate(raw)
    initial = AnalysisState(request=validated)
    result = build_graph(retriever).invoke({"analysis": initial}, {"recursion_limit": 6})
    return AnalysisState.model_validate(result["analysis"].model_dump())
