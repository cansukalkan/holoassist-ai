"""Execute deterministic synthetic verification across Vision, RAG+Cache, Diagnostic, and Safety."""

import hashlib
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from holoassist.agents.diagnostic import evaluate_hypotheses, matches
from holoassist.agents.supervisor import run_analysis
from holoassist.analytics.series import analyze_series
from holoassist.contracts.analysis import AnalysisRequest, AnalysisState
from holoassist.contracts.diagnostic import DiagnosticCatalog
from holoassist.contracts.evaluation import (
    DiagnosticBenchmarkSummary,
    OpenHardwareGate,
    RagBenchmarkSummary,
    SafetySpatialBenchmarkSummary,
    SyntheticBenchmarkReport,
    VisionBenchmarkSummary,
)
from holoassist.contracts.models import ObservationSeries
from holoassist.contracts.safety import InstructionCatalog, SafetyRequest
from holoassist.contracts.spatial import SpatialAnchorCatalog
from holoassist.rag.cache import CachedKnowledgeStore
from holoassist.rag.store import ChromaKnowledgeStore
from holoassist.safety.approvals import ApprovalError, ApprovalStore
from holoassist.safety.gate import evaluate_plan
from holoassist.spatial.projector import project_safety_to_anchors

FIXTURE_PATHS = (
    "datasets/fixtures/synthetic-guide.json",
    "datasets/fixtures/synthetic-diagnostic.json",
    "datasets/fixtures/synthetic-safety.json",
    "datasets/fixtures/instruction-catalog.json",
    "datasets/fixtures/spatial-anchor-catalog.json",
    "datasets/fixtures/diagnostic-catalog.json",
    "datasets/fixtures/analysis-request.json",
    "datasets/fixtures/sensor-current.json",
    "datasets/fixtures/sensor-temperature.json",
    "datasets/fixtures/sensor-vibration.json",
    "docs/examples/safety-analysis.json",
    "docs/examples/diagnostic-analysis.json",
)


def compute_fixture_digests(root: Path = Path(".")) -> dict[str, str]:
    digests: dict[str, str] = {}
    for relative in FIXTURE_PATHS:
        raw = (root / relative).read_bytes()
        digests[relative] = hashlib.sha256(raw).hexdigest()
    return digests


def _run_vision_benchmark() -> VisionBenchmarkSummary:
    import numpy as np

    from holoassist.vision.demo import synthetic_reference, synthetic_scene
    from holoassist.vision.reference import ReferenceMatcher

    reference = synthetic_reference(42)
    warped = synthetic_scene(reference)
    unknown = synthetic_reference(987)
    blank = np.full((620, 760), 220, dtype=np.uint8)
    matcher = ReferenceMatcher(
        reference, equipment_id="synthetic-rig", reference_kind="synthetic"
    )

    labeled_frames = (
        ("exact_reference", reference, True),
        ("perspective_warped", warped, True),
        ("unknown_seed_pattern", unknown, False),
        ("blank_low_feature", blank, False),
    )
    tp = tn = fp = fn = 0
    warped_error = 0.0
    expected_corners = np.float32([[95, 70], [650, 105], [615, 545], [65, 510]])

    for name, frame, expected_positive in labeled_frames:
        result = matcher.recognize(frame)
        predicted_positive = (
            result.status == "matched" and result.equipment_id == "synthetic-rig"
        )
        if expected_positive and predicted_positive:
            tp += 1
        elif not expected_positive and not predicted_positive and result.equipment_id is None:
            tn += 1
        elif not expected_positive and (predicted_positive or result.equipment_id is not None):
            fp += 1
        else:
            fn += 1
        if name == "perspective_warped" and result.corners:
            warped_error = float(
                np.max(np.linalg.norm(np.array(result.corners) - expected_corners, axis=1))
            )

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return VisionBenchmarkSummary(
        frames_evaluated=len(labeled_frames),
        true_positives=tp,
        true_negatives=tn,
        false_positives=fp,
        false_negatives=fn,
        precision=round(precision, 6),
        recall=round(recall, 6),
        f1=round(f1, 6),
        warped_max_corner_error_px=round(warped_error, 4),
    )


def _run_rag_and_diagnostic_benchmark(
    root: Path,
) -> tuple[RagBenchmarkSummary, DiagnosticBenchmarkSummary]:
    import chromadb
    from chromadb.config import Settings

    client = chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))
    base_store = ChromaKnowledgeStore(
        "unused",
        source_kind="synthetic",
        client=client,
        collection_name="bench_" + uuid4().hex,
    )
    cached_store = CachedKnowledgeStore(base_store, capacity=32)

    doc_files = (
        root / "datasets/fixtures/synthetic-guide.json",
        root / "datasets/fixtures/synthetic-diagnostic.json",
        root / "datasets/fixtures/synthetic-safety.json",
    )
    chunks_indexed = 0
    for doc_path in doc_files:
        chunks_indexed += cached_store.index_document(doc_path.read_bytes())

    t0 = time.perf_counter()
    cold_temp = cached_store.search("temperature sıcaklık", equipment_id="synthetic-rig", top_k=3)
    cold_curr = cached_store.search("current akım", equipment_id="synthetic-rig", top_k=3)
    cold_ms = (time.perf_counter() - t0) * 1000.0

    leakage_hits = cached_store.search(
        "temperature sıcaklık", equipment_id="unregistered-rig", top_k=3
    )

    t1 = time.perf_counter()
    warm_temp = cached_store.search("sıcaklık temperature", equipment_id="synthetic-rig", top_k=3)
    warm_curr = cached_store.search("akım current", equipment_id="synthetic-rig", top_k=3)
    warm_ms = (time.perf_counter() - t1) * 1000.0

    all_hits = (*cold_temp, *cold_curr, *warm_temp, *warm_curr)
    located = [
        chunk
        for chunk in all_hits
        if (chunk.page is not None or chunk.section is not None)
        and bool(chunk.checksum)
        and bool(chunk.document_version)
        and chunk.source_kind == "synthetic"
    ]
    locator_rate = (len(located) / len(all_hits)) if all_hits else 0.0
    unsupported_claims = len(all_hits) - len(located)
    stats = cached_store.stats()

    # Supervisor + sensor + diagnostic checks
    sensor_verified = 0
    for sensor_name in ("current", "temperature", "vibration"):
        series = ObservationSeries.model_validate_json(
            (root / f"datasets/fixtures/sensor-{sensor_name}.json").read_bytes()
        )
        report = analyze_series(series)
        if (
            report.provenance == "simulated"
            and report.status == "summary_available"
            and report.sample_count >= 2
        ):
            sensor_verified += 1

    request = AnalysisRequest.model_validate_json(
        (root / "datasets/fixtures/analysis-request.json").read_bytes()
    )
    supervisor_state = run_analysis(request, cached_store)
    supervisor_ready = (
        supervisor_state.status == "ready_for_diagnostic" and len(supervisor_state.evidence) >= 1
    )

    diag_state = AnalysisState.model_validate_json(
        (root / "docs/examples/diagnostic-analysis.json").read_bytes()
    )
    diag_catalog = DiagnosticCatalog.model_validate_json(
        (root / "datasets/fixtures/diagnostic-catalog.json").read_bytes()
    )
    complete_report = evaluate_hypotheses(diag_state, diag_catalog)
    contradiction_preserved = any(
        item.relation == "contradicts" for item in complete_report.assertion_matches
    )

    contrary = [
        assertion
        for rule in diag_catalog.rules
        for assertion in rule.assertions
        if assertion.relation == "contradicts"
    ]
    missing_state = diag_state.model_copy(
        update={
            "evidence": tuple(
                chunk
                for chunk in diag_state.evidence
                if not any(matches(assertion, chunk) for assertion in contrary)
            )
        }
    )
    missing_report = evaluate_hypotheses(missing_state, diag_catalog)
    missing_abstained = len(missing_report.hypotheses) == 0

    return (
        RagBenchmarkSummary(
            documents_indexed=len(doc_files),
            chunks_indexed=chunks_indexed,
            queries_executed=5,
            citation_locator_rate=round(locator_rate, 6),
            unsupported_claim_count=unsupported_claims,
            cross_equipment_leakage_count=len(leakage_hits),
            cache_hits=stats.hits,
            cache_misses=stats.misses,
            cold_query_ms=round(cold_ms, 3),
            warm_query_ms=round(warm_ms, 3),
            corpus_digest=stats.corpus_digest,
        ),
        DiagnosticBenchmarkSummary(
            sensor_series_verified=sensor_verified,
            supervisor_handoff_ready=supervisor_ready,
            contradiction_preserved=contradiction_preserved,
            missing_counter_evidence_abstained=missing_abstained,
        ),
    )


def _run_safety_spatial_benchmark(root: Path) -> SafetySpatialBenchmarkSummary:
    state = AnalysisState.model_validate_json(
        (root / "docs/examples/safety-analysis.json").read_bytes()
    )
    instruction_catalog = InstructionCatalog.model_validate_json(
        (root / "datasets/fixtures/instruction-catalog.json").read_bytes()
    )
    anchor_catalog = SpatialAnchorCatalog.model_validate_json(
        (root / "datasets/fixtures/spatial-anchor-catalog.json").read_bytes()
    )

    checks_passed = 0
    checks_total = 8

    # 1. Informational cited step -> display_allowed + card_and_highlight
    req_info = SafetyRequest(
        review_id="bench-info",
        analysis_request_id=state.request.request_id,
        tracking_status="tracked",
        steps=(
            {
                "step_id": "step-1",
                "instruction_id": "demo-information",
                "part_id": "demo-label",
            },
        ),
    )
    rep_info = evaluate_plan(state, req_info, instruction_catalog)
    proj_info = project_safety_to_anchors(
        rep_info, tracking_status="tracked", anchor_catalog=anchor_catalog
    )
    if (
        rep_info.status == "display_allowed"
        and rep_info.guidance_allowed is False
        and proj_info.active_anchor_count == 1
        and proj_info.cards[0].render_mode == "card_and_highlight"
    ):
        checks_passed += 1

    # 2. Critical step without approval -> needs_approval + redacted text + amber highlight
    req_crit = SafetyRequest(
        review_id="bench-critical",
        analysis_request_id=state.request.request_id,
        tracking_status="tracked",
        steps=(
            {
                "step_id": "step-1",
                "instruction_id": "demo-critical",
                "part_id": "demo-critical-part",
            },
        ),
    )
    rep_crit = evaluate_plan(state, req_crit, instruction_catalog)
    proj_crit = project_safety_to_anchors(
        rep_crit, tracking_status="tracked", anchor_catalog=anchor_catalog
    )
    if (
        rep_crit.status == "needs_approval"
        and rep_crit.steps[0].display_text is None
        and proj_crit.cards[0].render_mode == "highlight_needs_approval"
        and proj_crit.cards[0].display_text is None
    ):
        checks_passed += 1

    # 3. Prohibited step -> blocked + suppressed
    req_proh = SafetyRequest(
        review_id="bench-prohibited",
        analysis_request_id=state.request.request_id,
        tracking_status="tracked",
        steps=(
            {
                "step_id": "step-1",
                "instruction_id": "demo-prohibited",
                "part_id": "demo-prohibited-part",
            },
        ),
    )
    rep_proh = evaluate_plan(state, req_proh, instruction_catalog)
    proj_proh = project_safety_to_anchors(
        rep_proh, tracking_status="tracked", anchor_catalog=anchor_catalog
    )
    if rep_proh.status == "blocked" and proj_proh.active_anchor_count == 0:
        checks_passed += 1

    # 4. Tracking lost -> needs_information + all anchors suppressed
    req_lost = SafetyRequest(
        review_id="bench-lost",
        analysis_request_id=state.request.request_id,
        tracking_status="lost",
        steps=(
            {
                "step_id": "step-1",
                "instruction_id": "demo-information",
                "part_id": "demo-label",
            },
        ),
    )
    rep_lost = evaluate_plan(state, req_lost, instruction_catalog)
    proj_lost = project_safety_to_anchors(
        rep_lost, tracking_status="lost", anchor_catalog=anchor_catalog
    )
    tracking_loss_suppressed = (
        rep_lost.status == "needs_information" and proj_lost.active_anchor_count == 0
    )
    if tracking_loss_suppressed:
        checks_passed += 1

    # 5. Unknown anchor part -> blocked + suppressed
    req_unk = SafetyRequest(
        review_id="bench-unknown",
        analysis_request_id=state.request.request_id,
        tracking_status="tracked",
        steps=(
            {
                "step_id": "step-1",
                "instruction_id": "demo-information",
                "part_id": "unknown-part",
            },
        ),
    )
    rep_unk = evaluate_plan(state, req_unk, instruction_catalog)
    proj_unk = project_safety_to_anchors(
        rep_unk, tracking_status="tracked", anchor_catalog=anchor_catalog
    )
    unknown_anchor_suppressed = (
        rep_unk.status == "blocked" and proj_unk.active_anchor_count == 0
    )
    if unknown_anchor_suppressed:
        checks_passed += 1

    # 6. Mixed plan -> atomic redaction of all steps
    req_mixed = SafetyRequest.model_validate_json(
        (root / "datasets/fixtures/safety-mixed-request.json").read_bytes()
    )
    rep_mixed = evaluate_plan(state, req_mixed, instruction_catalog)
    if rep_mixed.status == "needs_approval" and all(
        step.display_text is None for step in rep_mixed.steps
    ):
        checks_passed += 1

    # 7 & 8. Persistent SQLite ApprovalStore: digest tamper rejection & one-time token consumption
    digest_tamper_rejected = False
    replay_token_rejected = False
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = ApprovalStore(
            Path(tmp_dir) / "bench_approvals.sqlite3",
            authorized_reviewers=("bench-reviewer",),
        )
        record = store.open_review(state, req_crit, instruction_catalog)
        try:
            store.decide(
                record.approval_id,
                authenticated_reviewer="bench-reviewer",
                decision="approve",
                expected_context_digest="0" * 64,
            )
        except ApprovalError as exc:
            if str(exc) == "review_context_mismatch":
                digest_tamper_rejected = True
                checks_passed += 1

        approved = store.decide(
            record.approval_id,
            authenticated_reviewer="bench-reviewer",
            decision="approve",
            expected_context_digest=record.context_digest,
        )
        receipt = store.resume_demo(approved.approval_id, state, req_crit, instruction_catalog)
        try:
            store.resume_demo(approved.approval_id, state, req_crit, instruction_catalog)
        except ApprovalError as exc:
            if str(exc) == "approval_not_approved" and receipt.guidance_allowed is False:
                replay_token_rejected = True
                checks_passed += 1

    return SafetySpatialBenchmarkSummary(
        checks_total=checks_total,
        checks_passed=checks_passed,
        safety_violations=checks_total - checks_passed,
        tracking_loss_suppressed=tracking_loss_suppressed,
        unknown_anchor_suppressed=unknown_anchor_suppressed,
        replay_token_rejected=replay_token_rejected,
        digest_tamper_rejected=digest_tamper_rejected,
    )


def run_synthetic_benchmark(root: Path = Path(".")) -> SyntheticBenchmarkReport:
    started = time.perf_counter()
    digests = compute_fixture_digests(root)
    vision = _run_vision_benchmark()
    rag, diagnostic = _run_rag_and_diagnostic_benchmark(root)
    safety_spatial = _run_safety_spatial_benchmark(root)
    duration_ms = (time.perf_counter() - started) * 1000.0

    all_passed = (
        vision.false_positives == 0
        and vision.false_negatives == 0
        and rag.unsupported_claim_count == 0
        and rag.cross_equipment_leakage_count == 0
        and rag.citation_locator_rate == 1.0
        and diagnostic.supervisor_handoff_ready
        and diagnostic.contradiction_preserved
        and diagnostic.missing_counter_evidence_abstained
        and safety_spatial.safety_violations == 0
    )

    return SyntheticBenchmarkReport(
        all_synthetic_gates_passed=all_passed,
        total_duration_ms=round(duration_ms, 3),
        vision=vision,
        rag=rag,
        diagnostic=diagnostic,
        safety_spatial=safety_spatial,
        fixture_digests=digests,
        open_hardware_gates=(
            OpenHardwareGate(
                gate_id="T01_real_dc_motor_and_licensed_manual",
                summary=(
                    "Fiziksel düşük voltajlı DC motor eğitim düzeneği seçimi ve yeniden "
                    "dağıtım izinli üretici kılavuzu (AGENTS.md donanım kapısı)."
                ),
            ),
            OpenHardwareGate(
                gate_id="T13_physical_ar_tracking_measurement",
                summary=(
                    "Fiziksel kamera ve iPhone/ARKit ortamında milimetre/piksel hizalama "
                    "ve takip kaybı ölçümü (cihaz olmadan başarı iddiası yapılmaz)."
                ),
            ),
            OpenHardwareGate(
                gate_id="live_llm_single_vs_multi_agent_comparison",
                summary=(
                    "İzinli gerçek teknik doküman eklendiğinde tek ajanlı ve çok ajanlı "
                    "LLM akışlarının p50/p95 gecikme ve doğruluk karşılaştırması."
                ),
            ),
        ),
    )
