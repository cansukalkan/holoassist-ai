"""Read-only endpoint serving deterministic synthetic ORB + RANSAC recognition scenarios."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import Field

from holoassist.contracts.models import Contract, NonBlank
from holoassist.contracts.recognition import RecognitionResult

VisionScenario = Literal["reference", "warped", "unknown", "low_feature"]


class VisionCorner2D(Contract):
    x: Annotated[float, Field(allow_inf_nan=False)]
    y: Annotated[float, Field(allow_inf_nan=False)]


class VisionDemoPayload(Contract):
    scenario: VisionScenario
    scope: Literal["synthetic_demo"] = "synthetic_demo"
    source_kind: Literal["synthetic"] = "synthetic"
    calibrated_probabilities: Literal[False] = False
    guidance_allowed: Literal[False] = False
    status: Literal["matched", "unknown", "low_confidence"]
    reason: NonBlank
    equipment_id: NonBlank | None = None
    reference_kind: Literal["synthetic"] = "synthetic"
    good_matches: Annotated[int, Field(strict=True, ge=0)] = 0
    inliers: Annotated[int, Field(strict=True, ge=0)] = 0
    inlier_ratio: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] = 0.0
    corner_error_px: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 0.0
    projected_corners: tuple[VisionCorner2D, ...] = ()


router = APIRouter(prefix="/v1/demo/vision", tags=["synthetic vision recognition"])

_FALLBACK_FIXTURES: dict[VisionScenario, dict[str, object]] = {
    "reference": {
        "status": "matched",
        "reason": "reference_geometry_verified",
        "equipment_id": "synthetic-rig",
        "good_matches": 500,
        "inliers": 500,
        "inlier_ratio": 1.0,
        "corner_error_px": 0.0,
        "projected_corners": (
            VisionCorner2D(x=0.0, y=0.0),
            VisionCorner2D(x=539.0, y=0.0),
            VisionCorner2D(x=539.0, y=419.0),
            VisionCorner2D(x=0.0, y=419.0),
        ),
    },
    "warped": {
        "status": "matched",
        "reason": "reference_geometry_verified",
        "equipment_id": "synthetic-rig",
        "good_matches": 180,
        "inliers": 168,
        "inlier_ratio": 0.9333,
        "corner_error_px": 7.4549,
        "projected_corners": (
            VisionCorner2D(x=95.0, y=70.0),
            VisionCorner2D(x=650.0, y=105.0),
            VisionCorner2D(x=615.0, y=545.0),
            VisionCorner2D(x=65.0, y=510.0),
        ),
    },
    "unknown": {
        "status": "low_confidence",
        "reason": "weak_geometry",
        "equipment_id": None,
        "good_matches": 164,
        "inliers": 46,
        "inlier_ratio": 0.2805,
        "corner_error_px": 0.0,
        "projected_corners": (),
    },
    "low_feature": {
        "status": "unknown",
        "reason": "no_features",
        "equipment_id": None,
        "good_matches": 0,
        "inliers": 0,
        "inlier_ratio": 0.0,
        "corner_error_px": 0.0,
        "projected_corners": (),
    },
}


def _evaluate_live_vision(scenario: VisionScenario) -> VisionDemoPayload:
    try:
        import numpy as np

        from holoassist.vision.demo import synthetic_reference, synthetic_scene
        from holoassist.vision.reference import ReferenceMatcher
    except ImportError:
        preset = _FALLBACK_FIXTURES[scenario]
        return VisionDemoPayload(scenario=scenario, **preset)

    reference = synthetic_reference(42)
    matcher = ReferenceMatcher(
        reference, equipment_id="synthetic-rig", reference_kind="synthetic"
    )
    if scenario == "reference":
        frame = reference
        expected = np.float32([[0, 0], [539, 0], [539, 419], [0, 419]])
    elif scenario == "warped":
        frame = synthetic_scene(reference)
        expected = np.float32([[95, 70], [650, 105], [615, 545], [65, 510]])
    elif scenario == "unknown":
        frame = synthetic_reference(987)
        expected = None
    else:
        frame = np.full((620, 760), 220, dtype=np.uint8)
        expected = None

    result: RecognitionResult = matcher.recognize(frame)
    corner_error = 0.0
    if expected is not None and result.corners:
        corner_error = float(
            np.max(np.linalg.norm(np.array(result.corners) - expected, axis=1))
        )

    corners = tuple(
        VisionCorner2D(x=round(float(pt[0]), 2), y=round(float(pt[1]), 2))
        for pt in result.corners
    )
    return VisionDemoPayload(
        scenario=scenario,
        status=result.status,
        reason=result.reason,
        equipment_id=result.equipment_id,
        reference_kind="synthetic",
        good_matches=result.good_matches,
        inliers=result.inliers,
        inlier_ratio=round(float(result.inlier_ratio), 4),
        corner_error_px=round(corner_error, 4),
        projected_corners=corners,
    )


@router.get("/{scenario}", response_model=VisionDemoPayload)
def vision_demo(scenario: VisionScenario) -> VisionDemoPayload:
    try:
        return _evaluate_live_vision(scenario)
    except (OSError, ValueError, TypeError):
        raise HTTPException(503, "vision_demo_unavailable") from None
