"""Generate reproducible synthetic vision fixtures, not motor photographs."""

import argparse
from pathlib import Path

import cv2
import numpy as np


def synthetic_reference(seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    image = np.full((420, 540), 245, dtype=np.uint8)
    for _ in range(140):
        center = (int(rng.integers(25, 515)), int(rng.integers(25, 395)))
        cv2.circle(image, center, int(rng.integers(2, 10)), int(rng.integers(0, 180)), -1)
    cv2.putText(image, "SYNTHETIC TEST", (30, 210), cv2.FONT_HERSHEY_SIMPLEX, 1.2, 0, 3)
    cv2.rectangle(image, (12, 12), (527, 407), 0, 3)
    return image


def synthetic_scene(reference: np.ndarray) -> np.ndarray:
    h, w = reference.shape
    source = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])
    target = np.float32([[95, 70], [650, 105], [615, 545], [65, 510]])
    transform = cv2.getPerspectiveTransform(source, target)
    return cv2.warpPerspective(reference, transform, (760, 620), borderValue=220)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/vision-demo"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    reference = synthetic_reference()
    for name, image in [
        ("reference", reference),
        ("scene", synthetic_scene(reference)),
        ("unknown", synthetic_reference(987)),
        ("blank", np.full((620, 760), 220, dtype=np.uint8)),
    ]:
        ok, encoded = cv2.imencode(".png", image)
        if not ok:
            raise ValueError("PNG encoding failed")
        (args.output / f"{name}.png").write_bytes(encoded.tobytes())
    from holoassist.vision.reference import ReferenceMatcher

    scene = synthetic_scene(reference)
    result = ReferenceMatcher(
        reference, equipment_id="synthetic-rig", reference_kind="synthetic"
    ).recognize(scene)
    (args.output / "recognition.json").write_text(
        result.model_dump_json(indent=2), encoding="utf-8"
    )
    if result.status == "matched":
        preview = cv2.cvtColor(scene, cv2.COLOR_GRAY2BGR)
        cv2.polylines(preview, [np.int32(result.corners).reshape(-1, 1, 2)], True, (0, 180, 0), 3)
        ok, encoded = cv2.imencode(".png", preview)
        if not ok:
            raise ValueError("PNG encoding failed")
        (args.output / "recognized.png").write_bytes(encoded.tobytes())
    print(f"Synthetic test images saved in {args.output}")


if __name__ == "__main__":
    main()
