"""Recognize one registered reference in an image; does not activate a camera."""

import argparse
import sys

from holoassist.vision.reference import ReferenceMatcher, load_image


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--equipment-id", required=True)
    parser.add_argument("--reference-kind", choices=["synthetic", "real"], required=True)
    args = parser.parse_args()
    try:
        matcher = ReferenceMatcher(
            load_image(args.reference),
            equipment_id=args.equipment_id,
            reference_kind=args.reference_kind,
        )
        result = matcher.recognize(load_image(args.image))
    except (ValueError, OSError) as error:
        print(f"Image rejected: {error}", file=sys.stderr)
        return 2
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
