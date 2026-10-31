# ruff: noqa: E402 -- optional orchestration must be available before integration imports
"""Source binding and abstention for deterministic diagnostic demo hypotheses."""

import json
from pathlib import Path

import pytest
from holoassist.agents.diagnostic import evaluate_hypotheses
from holoassist.contracts.analysis import AnalysisState
from holoassist.contracts.diagnostic import DiagnosticCatalog, DiagnosticReport, Hypothesis
from holoassist.rag.chunking import chunk_document
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "datasets/fixtures"


@pytest.fixture
def catalog():
    return json.loads((FIXTURES / "diagnostic-catalog.json").read_text(encoding="utf-8-sig"))


@pytest.fixture
def state():
    request = json.loads((FIXTURES / "analysis-request.json").read_text(encoding="utf-8-sig"))
    return AnalysisState(
        request=request,
        status="ready_for_diagnostic",
        evidence=chunk_document((FIXTURES / "synthetic-diagnostic.json").read_bytes()),
    )


def test_supported_and_contradicted_hypotheses_are_separate(state, catalog):
    result = evaluate_hypotheses(state, catalog)
    assert result.status == "hypotheses_available"
    assert result.guidance_allowed is False
    assert result.source_kind == "synthetic"
    by_code = {item.code: item for item in result.hypotheses}
    assert by_code["demo_load_state"].uncertainty == "conflicting_evidence"
    assert by_code["demo_load_state"].contradicting_evidence_ids == (state.evidence[1].evidence_id,)
    assert by_code["demo_environment_state"].uncertainty == "unverified"
    assert all(item.missing_information for item in result.hypotheses)
    assert len(result.assertion_matches) == 3
    assert DiagnosticReport.model_validate_json(result.model_dump_json()) == result
    for citation in result.assertion_matches:
        chunk = next(item for item in state.evidence if item.evidence_id == citation.evidence_id)
        assert citation.quote in chunk.excerpt


def test_missing_contradiction_withholds_all_hypotheses(state, catalog):
    changed = AnalysisState.model_validate(state.model_dump() | {"evidence": [state.evidence[0]]})
    result = evaluate_hypotheses(changed, catalog)
    assert result.status == "needs_information"
    assert not result.hypotheses
    assert not result.assertion_matches
    assert "source_for:demo_load_state:load-contradiction" in result.missing_information


@pytest.mark.parametrize(
    "change",
    [
        {"checksum": "a" * 64},
        {"document_version": "wrong"},
        {"page": 999},
        {"section": "wrong"},
        {"document_id": "wrong"},
        {"quote": "nonexistent source statement"},
    ],
)
def test_unbound_citation_cannot_support_hypothesis(state, catalog, change):
    catalog["rules"][0]["assertions"][0] |= change
    result = evaluate_hypotheses(state, catalog)
    assert result.status == "needs_information"
    assert not result.hypotheses


def test_unavailable_symptom_catalog_requests_information(state, catalog):
    payload = state.model_dump()
    payload["request"]["symptom_codes"] = ["not_rotating"]
    result = evaluate_hypotheses(payload, catalog)
    assert result.status == "needs_information"
    assert result.missing_information == ("catalog_for:not_rotating",)


@pytest.mark.parametrize(
    "status,updates",
    [
        ("running", {}),
        ("blocked", {"errors": [{"node": "knowledge", "code": "test_error"}]}),
        ("needs_information", {"missing_information": ["sources"]}),
    ],
)
def test_nonready_state_cannot_be_diagnosed(state, catalog, status, updates):
    result = evaluate_hypotheses(state.model_dump() | {"status": status} | updates, catalog)
    assert result.status == "blocked"
    assert result.reason_code == "analysis_not_ready"
    assert not result.hypotheses


def test_catalog_equipment_mismatch_blocks(state, catalog):
    catalog["equipment_id"] = "another-rig"
    assert evaluate_hypotheses(state, catalog).status == "blocked"


def test_real_mode_is_never_evaluated_using_demo_catalog(state, catalog):
    payload = state.model_dump()
    payload["request"]["mode"] = "real"
    payload["request"]["recognition"]["reference_kind"] = "real"
    for chunk in payload["evidence"]:
        chunk["source_kind"] = "manufacturer"
    result = evaluate_hypotheses(payload, catalog)
    assert result.status == "blocked"
    assert result.reason_code == "catalog_context_mismatch"


def test_input_order_does_not_change_hypothesis_order(state, catalog):
    first = evaluate_hypotheses(state, catalog)
    catalog["rules"].reverse()
    second = evaluate_hypotheses(state, catalog)
    assert first.hypotheses == second.hypotheses


@pytest.mark.parametrize(
    "change", [{"scope": "real"}, {"schema_version": "2.0"}, {"rules": []}, {"approval": True}]
)
def test_invalid_catalogs_are_rejected(catalog, change):
    with pytest.raises(ValidationError):
        DiagnosticCatalog.model_validate(catalog | change)


def test_rule_without_support_is_rejected(catalog):
    catalog["rules"][0]["assertions"] = [catalog["rules"][0]["assertions"][1]]
    with pytest.raises(ValidationError):
        DiagnosticCatalog.model_validate(catalog)


def test_duplicate_rules_are_rejected(catalog):
    catalog["rules"].append(catalog["rules"][0])
    with pytest.raises(ValidationError):
        DiagnosticCatalog.model_validate(catalog)


@pytest.mark.parametrize(
    "change",
    [
        {"supporting_evidence_ids": []},
        {"uncertainty": "conflicting_evidence"},
        {"supporting_evidence_ids": ["one", "one"]},
        {"probability": 0.9},
    ],
)
def test_hypothesis_contract_rejects_unsupported_certainty(change):
    payload = (
        dict(
            code="demo",
            explanation="test",
            supporting_evidence_ids=["one"],
            uncertainty="unverified",
            missing_information=["sensor_data"],
        )
        | change
    )
    with pytest.raises(ValidationError):
        Hypothesis.model_validate(payload)


def test_reference_document_tampering_breaks_catalog_binding(state, catalog):
    document = json.loads((FIXTURES / "synthetic-diagnostic.json").read_text(encoding="utf-8-sig"))
    document["blocks"][0]["text"] += " changed"
    new_chunks = chunk_document(json.dumps(document).encode())
    changed = AnalysisState.model_validate(state.model_dump() | {"evidence": new_chunks})
    assert evaluate_hypotheses(changed, catalog).status == "needs_information"


def test_real_chroma_and_supervisor_handoff_are_evaluated(catalog):
    chromadb = pytest.importorskip("chromadb")
    pytest.importorskip("langgraph")
    from uuid import uuid4

    from holoassist.agents.supervisor import run_analysis
    from holoassist.rag.store import ChromaKnowledgeStore

    request = json.loads((FIXTURES / "analysis-request.json").read_text(encoding="utf-8-sig"))
    store = ChromaKnowledgeStore(
        "unused",
        source_kind="synthetic",
        client=chromadb.EphemeralClient(
            settings=chromadb.config.Settings(anonymized_telemetry=False)
        ),
        collection_name="diagnostic_" + uuid4().hex,
    )
    store.index_document((FIXTURES / "synthetic-diagnostic.json").read_bytes())
    analysis = run_analysis(request, store)
    assert analysis.status == "ready_for_diagnostic"
    report = evaluate_hypotheses(analysis, catalog)
    assert report.status == "hypotheses_available"
    assert len(report.hypotheses) == 2


def test_generic_source_cannot_be_used_to_invent_a_diagnosis(state, catalog):
    generic = chunk_document((FIXTURES / "synthetic-guide.json").read_bytes())
    result = evaluate_hypotheses(state.model_dump() | {"evidence": generic}, catalog)
    assert result.status == "needs_information"
    assert not result.hypotheses


def test_report_rejects_dangling_hypothesis_citations(state, catalog):
    result = evaluate_hypotheses(state, catalog).model_dump()
    result["hypotheses"][0]["supporting_evidence_ids"] = ["missing-evidence"]
    with pytest.raises(ValidationError, match="citation relations"):
        DiagnosticReport.model_validate(result)


def test_report_rejects_unknown_hypothesis_in_assertion_match(state, catalog):
    result = evaluate_hypotheses(state, catalog).model_dump()
    result["assertion_matches"][0]["rule_code"] = "not-in-report"
    with pytest.raises(ValidationError, match="unknown hypothesis"):
        DiagnosticReport.model_validate(result)
