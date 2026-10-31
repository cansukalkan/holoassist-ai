"""ORB matching with RANSAC geometry checks; not a general equipment classifier."""

from pathlib import Path
from typing import Annotated, Literal

import cv2
import numpy as np
from pydantic import Field

from holoassist.contracts.models import Contract
from holoassist.contracts.recognition import RecognitionResult as RecognitionResult


class VisionConfig(Contract):
    min_matches: Annotated[int, Field(strict=True, ge=4)] = 16
    min_inliers: Annotated[int, Field(strict=True, ge=4)] = 12
    min_inlier_ratio: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] = 0.6
    ratio_test: Annotated[float, Field(gt=0, lt=1, allow_inf_nan=False)] = 0.75
    min_reference_coverage: Annotated[float, Field(gt=0, le=1)] = 0.1


def grayscale(image: np.ndarray) -> np.ndarray:
    if not isinstance(image, np.ndarray) or image.dtype != np.uint8:
        raise ValueError("image must be a uint8 NumPy array")
    if image.ndim not in (2, 3) or (image.ndim == 3 and image.shape[2] != 3):
        raise ValueError("expected grayscale or three-channel BGR image")
    h, w = image.shape[:2]
    if min(h, w) < 32 or h * w > 4_000_000:
        raise ValueError("image must be at least 32x32 and at most 4 million pixels")
    return image.copy() if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def load_image(path: str | Path) -> np.ndarray:
    with Path(path).open("rb") as source:
        raw = source.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024:
        raise ValueError("encoded image exceeds 10 MiB")
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError("image could not be decoded")
    return grayscale(image)


class ReferenceMatcher:
    def __init__(
        self,
        reference: np.ndarray,
        *,
        equipment_id: str,
        reference_kind: Literal["synthetic", "real"],
        config: VisionConfig | None = None,
    ):
        if not isinstance(equipment_id, str) or not equipment_id.strip():
            raise ValueError("equipment_id must be nonblank")
        if reference_kind not in ("synthetic", "real"):
            raise ValueError("reference_kind must be synthetic or real")
        self.equipment_id = equipment_id.strip()
        self.reference_kind = reference_kind
        self.config = config or VisionConfig()
        self.reference = grayscale(reference)
        self.orb = cv2.ORB_create(nfeatures=2000)
        self.keypoints, self.descriptors = self.orb.detectAndCompute(self.reference, None)
        if self.descriptors is None or len(self.keypoints) < self.config.min_matches:
            raise ValueError("reference has insufficient distinctive features")

    def recognize(self, frame: np.ndarray) -> RecognitionResult:
        image = grayscale(frame)
        points, descriptors = self.orb.detectAndCompute(image, None)
        metrics = {"reference_kind": self.reference_kind}
        if descriptors is None or len(points) < 2:
            return RecognitionResult(status="unknown", reason="no_features", **metrics)
        pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(self.descriptors, descriptors, k=2)
        good = [
            pair[0]
            for pair in pairs
            if len(pair) == 2 and pair[0].distance < self.config.ratio_test * pair[1].distance
        ]
        # A scene feature can support only one correspondence.
        unique = {}
        for match in sorted(good, key=lambda item: item.distance):
            unique.setdefault(match.trainIdx, match)
        good = list(unique.values())
        metrics["good_matches"] = len(good)
        if len(good) < self.config.min_matches:
            return RecognitionResult(status="unknown", reason="insufficient_matches", **metrics)
        src = np.float32([self.keypoints[item.queryIdx].pt for item in good]).reshape(-1, 1, 2)
        dst = np.float32([points[item.trainIdx].pt for item in good]).reshape(-1, 1, 2)
        matrix, mask = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
        if matrix is None or mask is None or not np.isfinite(matrix).all():
            return RecognitionResult(
                status="low_confidence", reason="invalid_homography", **metrics
            )
        inliers = int(mask.sum())
        metrics |= {"inliers": inliers, "inlier_ratio": inliers / len(good)}
        if (
            inliers < self.config.min_inliers
            or metrics["inlier_ratio"] < self.config.min_inlier_ratio
        ):
            return RecognitionResult(status="low_confidence", reason="weak_geometry", **metrics)
        h, w = self.reference.shape
        covered = cv2.contourArea(cv2.convexHull(src[mask.ravel().astype(bool)])) / (h * w)
        if covered < self.config.min_reference_coverage:
            return RecognitionResult(status="low_confidence", reason="limited_coverage", **metrics)
        rectangle = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]]).reshape(-1, 1, 2)
        corners = cv2.perspectiveTransform(rectangle, matrix).reshape(4, 2)
        fh, fw = image.shape
        area = abs(cv2.contourArea(corners))
        valid = (
            np.isfinite(corners).all()
            and cv2.isContourConvex(corners)
            and 0.01 * fh * fw <= area <= 1.01 * fh * fw
            and np.all(corners[:, 0] >= -0.05 * fw)
            and np.all(corners[:, 0] <= 1.05 * fw)
            and np.all(corners[:, 1] >= -0.05 * fh)
            and np.all(corners[:, 1] <= 1.05 * fh)
        )
        if not valid:
            return RecognitionResult(
                status="low_confidence", reason="invalid_projection", **metrics
            )
        return RecognitionResult(
            status="matched",
            reason="reference_geometry_verified",
            equipment_id=self.equipment_id,
            corners=tuple(tuple(float(v) for v in point) for point in corners),
            **metrics,
        )
