"""Allowlisted read-only fixture analytics; no client file paths or sensor writes."""

import hashlib
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException

from holoassist.analytics.series import analyze_series
from holoassist.contracts.analytics import SensorDemoResult
from holoassist.contracts.models import ObservationSeries

FIXTURE_DIRECTORY = Path("datasets/fixtures")
router = APIRouter(prefix="/v1/demo/sensors", tags=["simulated sensor data"])


@router.get("/{sensor}", response_model=SensorDemoResult)
def sensor_demo(sensor: Literal["current", "temperature", "vibration"]):
    try:
        with (FIXTURE_DIRECTORY / f"sensor-{sensor}.json").open("rb") as source:
            raw = source.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("demo_fixture_too_large")
        series = ObservationSeries.model_validate_json(raw)
        return SensorDemoResult(
            fixture_id=sensor,
            fixture_checksum=hashlib.sha256(raw).hexdigest(),
            series=series,
            report=analyze_series(series),
        )
    except (OSError, ValueError, TypeError):
        raise HTTPException(503, "sensor_demo_unavailable") from None
