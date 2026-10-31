# ruff: noqa: E402 -- orchestration is an optional dependency
"""Guard rails and deterministic routing on an actual LangGraph execution."""

import json
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

pytest.importorskip("langgraph")

from holoassist.agents.supervisor import run_analysis
from holoassist.contracts.analysis import AnalysisRequest, AnalysisState
from holoassist.contracts.recognition import RecognitionResult
from holoassist.rag.chunking import DocumentChunk, chunk_document

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def request_payload():
    return json.loads(
        (ROOT / "datasets/fixtures/analysis-request.json").read_text(encoding="utf-8-sig")
    )


@pytest.fixture
def evidence():
    return chunk_document((ROOT / "datasets/fixtures/synthetic-guide.json").read_bytes())[1]


@pytest.fixture
def retriever(evidence):
    return Mock(search=Mock(return_value=(evidence,)))


def test_valid_request_has_bounded_trace_and_no_guidance(request_payload, retriever, evidence):
    result = run_analysis(request_payload, retriever)
    assert result.status == "ready_for_diagnostic"
    assert result.guidance_allowed is False
    assert result.evidence == (evidence,)
    assert [(x.step, x.node) for x in result.trace] == [
        (1, "supervisor"),
        (2, "knowledge"),
        (3, "validation"),
    ]
    retriever.search.assert_called_once_with(
        "temperature sıcaklık", equipment_id="synthetic-rig", top_k=3
    )
    assert AnalysisState.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize(
    "recognition",
    [
        None,
        {"status": "unknown", "reason": "no_features", "reference_kind": "synthetic"},
        {"status": "low_confidence", "reason": "weak_geometry", "reference_kind": "synthetic"},
    ],
)
def test_rejected_identity_stops_before_retrieval(request_payload, retriever, recognition):
    result = run_analysis(request_payload | {"recognition": recognition}, retriever)
    assert result.status == "needs_information"
    assert result.missing_information == ("matched_equipment_reference",)
    assert len(result.trace) == 1
    assert not result.evidence
    retriever.search.assert_not_called()


def test_missing_symptoms_stops_before_retrieval(request_payload, retriever):
    result = run_analysis(request_payload | {"symptom_codes": []}, retriever)
    assert result.status == "needs_information"
    assert result.missing_information == ("symptom_codes",)
    retriever.search.assert_not_called()


@pytest.mark.parametrize(
    "change,code",
    [
        ({"equipment_id": "another"}, "identity_mismatch"),
        ({"reference_kind": "real"}, "reference_mode_mismatch"),
    ],
)
def test_identity_context_mismatch_blocks(request_payload, retriever, change, code):
    request_payload["recognition"] |= change
    result = run_analysis(request_payload, retriever)
    assert result.status == "blocked"
    assert result.errors[0].code == code
    retriever.search.assert_not_called()


def test_real_mode_rejects_synthetic_reference(request_payload, retriever):
    result = run_analysis(request_payload | {"mode": "real"}, retriever)
    assert result.status == "blocked"
    assert result.errors[0].code == "reference_mode_mismatch"


@pytest.mark.parametrize(
    "change,expected",
    [
        ({"provenance": "measured"}, "blocked"),
        ({"equipment_id": "another"}, "blocked"),
        ({"quality": "suspect"}, "needs_information"),
        ({"quality": "invalid"}, "needs_information"),
        ({}, "ready_for_diagnostic"),
    ],
)
def test_sensor_context_is_checked(request_payload, retriever, change, expected):
    observation = (
        dict(
            equipment_id="synthetic-rig",
            sensor_id="synthetic-sensor",
            timestamp_utc="2026-10-21T10:00:00Z",
            quantity="temperature",
            value=25.0,
            unit="degC",
            provenance="simulated",
            quality="valid",
        )
        | change
    )
    request_payload["sensor_series"] = [{"observations": [observation]}]
    result = run_analysis(request_payload, retriever)
    assert result.status == expected
    if expected != "ready_for_diagnostic":
        retriever.search.assert_not_called()


def test_empty_sources_request_more_information(request_payload, retriever):
    retriever.search.return_value = ()
    result = run_analysis(request_payload, retriever)
    assert result.status == "needs_information"
    assert result.missing_information == ("equipment_specific_sources",)
    assert len(result.trace) == 3


def test_retrieval_exception_is_sanitized_and_not_retried(request_payload, retriever):
    retriever.search.side_effect = RuntimeError("private-key-and-path-not-for-output")
    result = run_analysis(request_payload, retriever)
    assert result.status == "blocked"
    assert result.errors[0].code == "retrieval_failed"
    assert "private-key" not in result.model_dump_json()
    assert len(result.trace) == 2
    retriever.search.assert_called_once()


@pytest.mark.parametrize("change", [{"source_kind": "manufacturer"}, {"equipment_id": "another"}])
def test_mismatched_retrieved_evidence_is_blocked(request_payload, retriever, evidence, change):
    retriever.search.return_value = (DocumentChunk.model_validate(evidence.model_dump() | change),)
    result = run_analysis(request_payload, retriever)
    assert result.status == "blocked"
    assert result.errors[0].code == "invalid_retrieval"
    assert not result.evidence


def test_real_mode_cannot_accept_synthetic_sources(request_payload, retriever):
    request_payload["mode"] = "real"
    request_payload["recognition"]["reference_kind"] = "real"
    assert run_analysis(request_payload, retriever).status == "blocked"


@pytest.mark.parametrize("raw", [None, "not chunks", [None], iter(())])
def test_malformed_retrieval_is_blocked(request_payload, retriever, raw):
    retriever.search.return_value = raw
    result = run_analysis(request_payload, retriever)
    assert result.status == "blocked"
    assert result.errors[0].code == "invalid_retrieval"


def test_duplicate_evidence_is_blocked(request_payload, retriever, evidence):
    retriever.search.return_value = (evidence, evidence)
    assert run_analysis(request_payload, retriever).errors[0].code == "invalid_retrieval"


def test_conflicting_document_revision_is_blocked(request_payload, retriever, evidence):
    second = DocumentChunk.model_validate(
        evidence.model_dump()
        | {
            "evidence_id": "different-chunk",
            "document_version": "conflicting-version",
            "checksum": "b" * 64,
        }
    )
    retriever.search.return_value = (evidence, second)
    assert run_analysis(request_payload, retriever).errors[0].code == "invalid_retrieval"


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": "2.0"},
        {"symptom_codes": ["invented"]},
        {"symptom_codes": ["overheating", "overheating"]},
        {"request_id": " "},
        {"mode": "unknown"},
        {"evidence": []},
        {"status": "ready_for_diagnostic"},
        {"guidance_allowed": True},
        {"approval": True},
    ],
)
def test_invalid_or_injected_request_fields_are_rejected(request_payload, retriever, change):
    with pytest.raises(ValidationError):
        run_analysis(request_payload | change, retriever)
    retriever.search.assert_not_called()


@pytest.mark.parametrize(
    "change",
    [
        {"guidance_allowed": True},
        {"status": "ready_for_diagnostic"},
        {"status": "needs_information"},
        {"status": "blocked"},
        {"trace": [{"step": 2, "node": "supervisor", "code": "bad"}]},
    ],
)
def test_invalid_states_are_rejected(request_payload, change):
    with pytest.raises(ValidationError):
        AnalysisState.model_validate({"request": request_payload} | change)


def test_fresh_invocations_do_not_reuse_trace_or_evidence(request_payload, retriever):
    first = run_analysis(request_payload, retriever)
    retriever.search.return_value = ()
    second = run_analysis(request_payload, retriever)
    assert first.status == "ready_for_diagnostic"
    assert second.status == "needs_information"
    assert not second.evidence
    assert len(second.trace) == 3


@pytest.mark.parametrize(
    "change", [{"good_matches": -1}, {"inliers": 21}, {"corners": [[float("nan"), 0]] * 4}]
)
def test_recognition_rejects_invalid_cross_module_data(request_payload, change):
    with pytest.raises(ValidationError):
        RecognitionResult.model_validate(request_payload["recognition"] | change)


def test_vision_and_chroma_connect_to_real_langgraph(request_payload):
    cv2 = pytest.importorskip("cv2")
    chromadb = pytest.importorskip("chromadb")
    from holoassist.rag.store import ChromaKnowledgeStore
    from holoassist.vision.demo import synthetic_reference, synthetic_scene
    from holoassist.vision.reference import ReferenceMatcher

    assert cv2 is not None
    reference = synthetic_reference()
    recognition = ReferenceMatcher(
        reference, equipment_id="synthetic-rig", reference_kind="synthetic"
    ).recognize(synthetic_scene(reference))
    request_payload["recognition"] = recognition.model_dump()
    client = chromadb.EphemeralClient(settings=chromadb.config.Settings(anonymized_telemetry=False))
    store = ChromaKnowledgeStore(
        "unused", source_kind="synthetic", client=client, collection_name="graph_" + uuid4().hex
    )
    store.index_document((ROOT / "datasets/fixtures/synthetic-guide.json").read_bytes())
    result = run_analysis(AnalysisRequest.model_validate(request_payload), store)
    assert result.status == "ready_for_diagnostic"
    assert result.evidence[0].page == 2
    assert result.guidance_allowed is False
    assert result.request.recognition.reference_kind == "synthetic"


def test_contract_and_supervisor_imports_do_not_require_vision_or_chroma():
    import subprocess
    import sys

    code = (
        "import sys; from holoassist.agents.supervisor import run_analysis; "
        'assert "cv2" not in sys.modules; assert "chromadb" not in sys.modules'
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, check=False)
    assert result.returncode == 0, result.stderr


def test_cli_validation_error_does_not_echo_untrusted_payload(monkeypatch, capsys):
    from io import BytesIO

    from holoassist.agents.__main__ import main

    monkeypatch.setattr("sys.argv", ["holoassist.agents", "--request", "test-request.json"])
    invalid = b'{"unexpected_secret": "private-value-must-not-be-logged"}'
    with patch("holoassist.agents.__main__.Path.open", return_value=BytesIO(invalid)):
        assert main() == 2
    captured = capsys.readouterr()
    assert "invalid_request_or_unavailable_data" in captured.err
    assert "private-value" not in captured.err
