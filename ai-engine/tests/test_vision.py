# ruff: noqa: E402 -- optional dependencies must be checked before module imports
"""Exercise actual OpenCV matches on reproducible synthetic image pairs."""

from unittest.mock import patch

import pytest

cv2 = pytest.importorskip("cv2", reason="install .[vision] for vision tests")
np = pytest.importorskip("numpy")

from holoassist.vision.demo import synthetic_reference, synthetic_scene
from holoassist.vision.reference import (
    RecognitionResult,
    ReferenceMatcher,
    VisionConfig,
    grayscale,
)


@pytest.fixture
def matcher():
    return ReferenceMatcher(
        synthetic_reference(), equipment_id="synthetic-rig", reference_kind="synthetic"
    )


def test_perspective_reference_is_identified_with_expected_corners(matcher):
    result = matcher.recognize(synthetic_scene(synthetic_reference()))
    assert result.status == "matched"
    assert result.equipment_id == "synthetic-rig"
    assert result.reference_kind == "synthetic"
    assert result.inliers >= 12
    expected = np.float32([[95, 70], [650, 105], [615, 545], [65, 510]])
    assert np.max(np.linalg.norm(np.array(result.corners) - expected, axis=1)) < 12
    assert RecognitionResult.model_validate_json(result.model_dump_json()) == result


def test_exact_reference_and_bgr_frame_are_supported(matcher):
    result = matcher.recognize(cv2.cvtColor(synthetic_reference(), cv2.COLOR_GRAY2BGR))
    assert result.status == "matched"


@pytest.mark.parametrize("image", [np.zeros((420, 540), dtype=np.uint8), synthetic_reference(987)])
def test_unknown_has_no_equipment_identity(matcher, image):
    result = matcher.recognize(image)
    assert result.status in ("unknown", "low_confidence")
    assert result.equipment_id is None
    assert result.corners == ()


def test_low_confidence_does_not_leak_identity():
    matcher = ReferenceMatcher(
        synthetic_reference(),
        equipment_id="synthetic-rig",
        reference_kind="synthetic",
        config=VisionConfig(min_inliers=2000),
    )
    result = matcher.recognize(synthetic_scene(synthetic_reference()))
    assert result.status == "low_confidence"
    assert result.equipment_id is None
    assert result.corners == ()


def test_invalid_homography_is_rejected(matcher):
    with patch("holoassist.vision.reference.cv2.findHomography", return_value=(None, None)):
        result = matcher.recognize(synthetic_reference())
    assert result.status == "low_confidence"
    assert result.reason == "invalid_homography"


def test_outside_frame_projection_is_rejected(matcher):
    with patch(
        "holoassist.vision.reference.cv2.perspectiveTransform",
        return_value=np.float32([[[9999, 9999]]] * 4),
    ):
        result = matcher.recognize(synthetic_reference())
    assert result.status == "low_confidence"
    assert result.reason == "invalid_projection"
    assert result.equipment_id is None


@pytest.mark.parametrize(
    "image",
    [
        None,
        np.zeros((20, 20), dtype=np.uint8),
        np.zeros((50, 50), dtype=np.float32),
        np.zeros((50, 50, 4), dtype=np.uint8),
        np.zeros((2001, 2000), dtype=np.uint8),
    ],
)
def test_invalid_images_are_rejected(image):
    with pytest.raises(ValueError):
        grayscale(image)


def test_featureless_reference_is_rejected():
    with pytest.raises(ValueError, match="features"):
        ReferenceMatcher(
            np.zeros((300, 300), dtype=np.uint8), equipment_id="test", reference_kind="synthetic"
        )


@pytest.mark.parametrize(
    "config",
    [
        {"min_matches": 3},
        {"min_inliers": True},
        {"ratio_test": 1},
        {"min_inlier_ratio": float("nan")},
    ],
)
def test_invalid_threshold_configuration(config):
    with pytest.raises(ValueError):
        VisionConfig(**config)


def test_unrelated_noise_is_unknown(matcher):
    noise = np.random.default_rng(12345).integers(0, 256, (420, 540), dtype=np.uint8)
    result = matcher.recognize(noise)
    assert result.status == "unknown"
    assert result.equipment_id is None
