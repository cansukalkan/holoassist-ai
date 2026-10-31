"""Read-only endpoint serving reproducible synthetic benchmark telemetry."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from holoassist.contracts.evaluation import SyntheticBenchmarkReport
from holoassist.evaluation.benchmark import compute_fixture_digests, run_synthetic_benchmark

SAVED_BENCHMARK_FILE = Path("docs/examples/synthetic-benchmark-report.json")
router = APIRouter(prefix="/v1/demo/evaluation", tags=["synthetic benchmark evaluation"])

_cached_report_json: str | None = None
_cached_digests: dict[str, str] | None = None


def clear_evaluation_cache() -> None:
    global _cached_report_json, _cached_digests
    _cached_report_json = None
    _cached_digests = None


@router.get("", response_model=SyntheticBenchmarkReport)
def evaluation_demo() -> SyntheticBenchmarkReport:
    global _cached_report_json, _cached_digests
    try:
        current_digests = compute_fixture_digests(Path("."))
        if _cached_report_json is not None and _cached_digests == current_digests:
            return SyntheticBenchmarkReport.model_validate_json(_cached_report_json)
        try:
            report = run_synthetic_benchmark(Path("."))
        except ImportError:
            # Minimal API-only containers without optional cv2/chromadb may serve the
            # saved report only when every fixture SHA-256 matches the current files.
            with SAVED_BENCHMARK_FILE.open("rb") as source:
                raw = source.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError("benchmark_report_too_large") from None
            report = SyntheticBenchmarkReport.model_validate_json(raw)
            if report.fixture_digests != current_digests:
                raise ValueError("saved_benchmark_digest_mismatch") from None
        _cached_report_json = report.model_dump_json()
        _cached_digests = current_digests
        return report
    except (OSError, ValueError, TypeError):
        raise HTTPException(503, "evaluation_demo_unavailable") from None

