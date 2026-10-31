"""Fail-closed plan gating, source pinning and instruction redaction."""

import json
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from holoassist.contracts.analysis import AnalysisState
from holoassist.contracts.safety import InstructionCatalog, SafetyReport, SafetyRequest
from holoassist.rag.chunking import chunk_document
from holoassist.safety import evaluate_plan
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "datasets/fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8-sig"))


@pytest.fixture
def state():
    return AnalysisState(
        request=load("analysis-request.json"),
        status="ready_for_diagnostic",
        evidence=chunk_document((FIXTURES / "synthetic-safety.json").read_bytes()),
    )


@pytest.fixture
def catalog():
    return load("instruction-catalog.json")


@pytest.fixture
def selection():
    return load("safety-information-request.json")


def select(selection, catalog, index):
    instruction = catalog["instructions"][index]
    selection["steps"] = [
        dict(
            step_id="one",
            instruction_id=instruction["instruction_id"],
            part_id=instruction["part_id"],
        )
    ]
    return selection


def test_source_bound_demo_card_can_be_displayed(state, selection, catalog):
    report = evaluate_plan(state, selection, catalog)
    assert report.status == "display_allowed"
    assert report.guidance_allowed is False
    assert report.source_kind == "synthetic"
    assert report.steps[0].display_text == catalog["instructions"][0]["text"]
    assert report.steps[0].citations[0].page == 1
    assert report.steps[0].citations[0].checksum == state.evidence[0].checksum
    assert SafetyReport.model_validate_json(report.model_dump_json()) == report
    assert evaluate_plan(state, selection, catalog) == report


def test_critical_instruction_always_needs_persistent_approval_and_hides_text(
    state, selection, catalog
):
    select(selection, catalog, 1)
    report = evaluate_plan(state, selection, catalog)
    assert report.status == "needs_approval"
    assert report.steps[0].reason_code == "persistent_approval_required"
    assert report.steps[0].display_text is None
    assert report.steps[0].citations[0].quote is None
    assert catalog["instructions"][1]["text"] not in report.model_dump_json()


@pytest.mark.parametrize("index", [2, 3])
def test_prohibited_or_unknown_risk_is_blocked(state, selection, catalog, index):
    select(selection, catalog, index)
    report = evaluate_plan(state, selection, catalog)
    assert report.status == "blocked"
    assert report.steps[0].reason_code == "risk_not_permitted"


def test_one_rejected_step_withholds_all_text_and_quotes(state, catalog):
    report = evaluate_plan(state, load("safety-mixed-request.json"), catalog)
    assert report.status == "needs_approval"
    assert report.steps[0].status == "display_allowed"
    assert all(item.display_text is None for item in report.steps)
    assert all(c.quote is None for item in report.steps for c in item.citations)


@pytest.mark.parametrize("tracking", ["lost", "unknown"])
def test_tracking_loss_prevents_display(state, selection, catalog, tracking):
    selection["tracking_status"] = tracking
    report = evaluate_plan(state, selection, catalog)
    assert report.status == "needs_information"
    assert report.steps[0].reason_code == "tracking_required"
    assert report.steps[0].display_text is None


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"instruction_id": "unregistered"}, "unknown_instruction"),
        ({"part_id": "different"}, "part_mismatch"),
    ],
)
def test_unknown_instruction_or_part_is_blocked(state, selection, catalog, change, reason):
    selection["steps"][0] |= change
    report = evaluate_plan(state, selection, catalog)
    assert report.status == "blocked"
    assert report.steps[0].reason_code == reason


@pytest.mark.parametrize(
    "change",
    [
        {"checksum": "a" * 64},
        {"page": 999},
        {"section": "wrong"},
        {"document_version": "wrong"},
        {"document_id": "wrong"},
    ],
)
def test_missing_source_binding_blocks(state, selection, catalog, change):
    catalog["instructions"][0]["sources"][0] |= change
    report = evaluate_plan(state, selection, catalog)
    assert report.status == "blocked"
    assert report.steps[0].reason_code == "source_binding_missing"


def test_unbound_text_is_not_accepted_by_catalog(state, selection, catalog):
    catalog["instructions"][0]["text"] = "invented instruction"
    with pytest.raises(ValidationError):
        evaluate_plan(state, selection, catalog)


def test_contradictory_source_blocks_instruction(state, selection, catalog):
    opposite = catalog["instructions"][0]["sources"][0].copy()
    opposite |= {"assertion_id": "opposite", "relation": "contradicts"}
    catalog["instructions"][0]["sources"].append(opposite)
    report = evaluate_plan(state, selection, catalog)
    assert report.status == "blocked"
    assert report.steps[0].reason_code == "contradictory_source"
    assert all(c.quote is None for c in report.steps[0].citations)


def test_missing_known_contrary_source_also_blocks(state, selection, catalog):
    opposite = catalog["instructions"][0]["sources"][0].copy()
    opposite |= {
        "assertion_id": "unretrieved-opposite",
        "quote": "unretrieved statement",
        "relation": "contradicts",
    }
    catalog["instructions"][0]["sources"].append(opposite)
    assert evaluate_plan(state, selection, catalog).steps[0].reason_code == "source_binding_missing"


@pytest.mark.parametrize(
    "change", [{"approval": True}, {"approval_reference": "fake"}, {"risk": "informational"}]
)
def test_caller_cannot_approve_or_downgrade_risk(selection, change):
    with pytest.raises(ValidationError):
        SafetyRequest.model_validate(selection | change)


def test_step_cannot_inject_risk_or_text(selection):
    selection["steps"][0] |= {"risk": "informational", "text": "injected"}
    with pytest.raises(ValidationError):
        SafetyRequest.model_validate(selection)


def test_request_must_belong_to_analysis(state, selection, catalog):
    selection["analysis_request_id"] = "another-analysis"
    assert (
        evaluate_plan(state, selection, catalog).steps[0].reason_code == "analysis_request_mismatch"
    )


def test_catalog_must_belong_to_equipment(state, selection, catalog):
    catalog["equipment_id"] = "another-equipment"
    assert (
        evaluate_plan(state, selection, catalog).steps[0].reason_code
        == "catalog_equipment_mismatch"
    )


def test_real_mode_never_authorizes_demo_instruction(state, selection, catalog):
    payload = state.model_dump()
    payload["request"]["mode"] = "real"
    payload["request"]["recognition"]["reference_kind"] = "real"
    for chunk in payload["evidence"]:
        chunk["source_kind"] = "manufacturer"
    report = evaluate_plan(payload, selection, catalog)
    assert report.steps[0].reason_code == "real_mode_not_supported"
    assert report.status == "blocked"


def test_nonready_analysis_is_blocked(state, selection, catalog):
    report = evaluate_plan(state.model_dump() | {"status": "running"}, selection, catalog)
    assert report.steps[0].reason_code == "analysis_not_ready"


def test_context_digest_changes_when_source_or_catalog_changes(state, selection, catalog):
    first = evaluate_plan(state, selection, catalog)
    catalog["catalog_version"] = "test-2"
    assert evaluate_plan(state, selection, catalog).context_digest != first.context_digest


@pytest.mark.parametrize(
    "change", [{"scope": "real"}, {"instructions": []}, {"schema_version": "2.0"}]
)
def test_invalid_catalog_is_rejected(catalog, change):
    with pytest.raises(ValidationError):
        InstructionCatalog.model_validate(catalog | change)


def test_request_rejects_empty_and_duplicate_steps(selection):
    for steps in ([], selection["steps"] * 2):
        with pytest.raises(ValidationError):
            SafetyRequest.model_validate(selection | {"steps": steps})


def test_report_rejects_physical_authorization(state, selection, catalog):
    report = evaluate_plan(state, selection, catalog).model_dump()
    with pytest.raises(ValidationError):
        SafetyReport.model_validate(report | {"guidance_allowed": True})


def test_report_rejects_instruction_quote_leakage_on_denied_plan(state, selection, catalog):
    select(selection, catalog, 1)
    report = evaluate_plan(state, selection, catalog).model_dump()
    report["steps"][0]["citations"][0]["quote"] = "withheld content"
    with pytest.raises(ValidationError, match="instruction quotes"):
        SafetyReport.model_validate(report)


def test_cli_rejection_does_not_echo_input(monkeypatch, capsys):
    from holoassist.safety.__main__ import main

    monkeypatch.setattr(
        "sys.argv", ["holoassist.safety", "--analysis", "a", "--request", "r", "--catalog", "c"]
    )
    with patch(
        "holoassist.safety.__main__.Path.open", return_value=BytesIO(b'{"secret":"do-not-log"}')
    ):
        assert main() == 2
    assert "do-not-log" not in capsys.readouterr().err


def test_report_cannot_downgrade_critical_plan_status(state, selection, catalog):
    select(selection, catalog, 1)
    report = evaluate_plan(state, selection, catalog).model_dump()
    with pytest.raises(ValidationError, match="most restrictive"):
        SafetyReport.model_validate(report | {"status": "needs_information"})


def test_real_chroma_and_supervisor_context_feed_gate(catalog, selection):
    chromadb = pytest.importorskip("chromadb")
    pytest.importorskip("langgraph")
    from uuid import uuid4

    from holoassist.agents.supervisor import run_analysis
    from holoassist.rag.store import ChromaKnowledgeStore

    store = ChromaKnowledgeStore(
        "unused",
        source_kind="synthetic",
        client=chromadb.EphemeralClient(
            settings=chromadb.config.Settings(anonymized_telemetry=False)
        ),
        collection_name="safety_" + uuid4().hex,
    )
    store.index_document((FIXTURES / "synthetic-safety.json").read_bytes())
    analysis = run_analysis(load("analysis-request.json"), store)
    assert analysis.status == "ready_for_diagnostic"
    report = evaluate_plan(analysis, selection, catalog)
    assert report.status == "display_allowed"
    assert report.guidance_allowed is False

