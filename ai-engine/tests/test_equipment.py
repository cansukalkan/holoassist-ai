"""Metadata intake never claims that a physical rig is ready."""

import json
from pathlib import Path

import pytest
from holoassist.contracts.equipment import EquipmentIntake, EquipmentIntakeReport
from holoassist.equipment.__main__ import check_intake, main
from pydantic import ValidationError


def complete_metadata():
    return dict(
        equipment_id="test-only-rig",
        manufacturer="test-only-brand",
        model="test-only-model",
        manufacturer_document=dict(
            document_id="test-only-document",
            document_version="test-only-version",
            source_uri="metadata-only-no-network",
            checksum="a" * 64,
            license="test-only-license",
            permission_reference="test-only-permission",
        ),
        power_supply_notes="test-only-not-validated",
        reference_image_notes="test-only-not-validated",
        sensor_notes="test-only-not-validated",
    )


def test_empty_template_explicitly_missing():
    profile = EquipmentIntake.model_validate_json(
        Path("docs/equipment-intake.template.json").read_bytes()
    )
    report = check_intake(profile)
    assert report.status == "needs_information"
    assert set(report.missing_information) == {
        "equipment_id",
        "manufacturer",
        "model",
        "manufacturer_document",
        "power_supply_notes",
        "reference_image_notes",
        "sensor_notes",
    }
    assert report.real_device_ready is False
    assert report.guidance_allowed is False


def test_complete_metadata_still_requires_physical_and_source_checks():
    report = check_intake(EquipmentIntake.model_validate(complete_metadata()))
    assert report.status == "metadata_recorded" and not report.missing_information
    assert "physical_rig_validation" in report.pending_checks
    assert "manufacturer_source_review" in report.pending_checks
    assert report.real_device_ready is False and report.guidance_allowed is False
    assert EquipmentIntakeReport.model_validate_json(report.model_dump_json()) == report


@pytest.mark.parametrize("field", ["model", "manufacturer", "equipment_id"])
def test_missing_field_reported(field):
    payload = complete_metadata() | {field: None}
    assert check_intake(EquipmentIntake.model_validate(payload)).missing_information == (field,)


@pytest.mark.parametrize(
    "payload",
    [
        {"model": " "},
        {"scope": "mains_ac"},
        {"approval": True},
        {"manufacturer_document": {"document_id": "no-version-or-permission"}},
    ],
)
def test_invalid_metadata_or_approval_rejected(payload):
    with pytest.raises(ValidationError):
        EquipmentIntake.model_validate(payload)


def test_inconsistent_report_rejected():
    with pytest.raises(ValidationError):
        EquipmentIntakeReport(
            status="metadata_recorded", equipment_id=None, missing_information=("model",)
        )


def test_cli_missing_metadata_is_valid_report(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv", ["equipment", "--profile", "docs/equipment-intake.template.json"]
    )
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["status"] == "needs_information"


@pytest.mark.parametrize(
    "content", ["secret-invalid-json", "x" * (65536 + 1)], ids=["bad-json", "oversized"]
)
def test_cli_bad_input_sanitized(content, tmp_path, monkeypatch, capsys):
    path = tmp_path / "profile.json"
    path.write_text(content)
    monkeypatch.setattr("sys.argv", ["equipment", "--profile", str(path)])
    assert main() == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert "secret-invalid-json" not in captured.err
    assert "invalid_or_unavailable_profile" in captured.err
