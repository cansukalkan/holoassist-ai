"""Check hardware metadata: python -m holoassist.equipment --profile file.json."""

import argparse
import sys
from pathlib import Path

from holoassist.contracts.equipment import EquipmentIntake, EquipmentIntakeReport


def check_intake(profile: EquipmentIntake) -> EquipmentIntakeReport:
    # Revalidate even when called with an existing model instance.
    profile = EquipmentIntake.model_validate(profile.model_dump())
    required = (
        "equipment_id",
        "manufacturer",
        "model",
        "manufacturer_document",
        "power_supply_notes",
        "reference_image_notes",
        "sensor_notes",
    )
    missing = tuple(name for name in required if getattr(profile, name) is None)
    return EquipmentIntakeReport(
        equipment_id=profile.equipment_id,
        status="needs_information" if missing else "metadata_recorded",
        missing_information=missing,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.profile.open("rb") as source:
            raw = source.read(64 * 1024 + 1)
        if len(raw) > 64 * 1024:
            raise ValueError("input_too_large")
        report = check_intake(EquipmentIntake.model_validate_json(raw))
    except (ValueError, OSError, TypeError):
        print("Equipment intake rejected: invalid_or_unavailable_profile", file=sys.stderr)
        return 2
    print(report.model_dump_json(indent=2))
    # An incomplete intake is a valid report, not an authorization or device test.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
