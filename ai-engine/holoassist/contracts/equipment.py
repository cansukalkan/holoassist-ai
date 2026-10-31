"""Hardware intake metadata; completeness never grants physical authorization."""

from typing import Literal, Self

from pydantic import model_validator

from holoassist.contracts.models import Checksum, Contract, NonBlank


class ManufacturerDocumentReference(Contract):
    document_id: NonBlank
    document_version: NonBlank
    source_uri: NonBlank
    checksum: Checksum
    license: NonBlank
    permission_reference: NonBlank


class EquipmentIntake(Contract):
    scope: Literal["low_voltage_dc_educational"] = "low_voltage_dc_educational"
    equipment_id: NonBlank | None = None
    manufacturer: NonBlank | None = None
    model: NonBlank | None = None
    manufacturer_document: ManufacturerDocumentReference | None = None
    power_supply_notes: NonBlank | None = None
    reference_image_notes: NonBlank | None = None
    sensor_notes: NonBlank | None = None


class EquipmentIntakeReport(Contract):
    status: Literal["needs_information", "metadata_recorded"]
    equipment_id: NonBlank | None
    missing_information: tuple[NonBlank, ...]
    pending_checks: tuple[NonBlank, ...] = (
        "manufacturer_source_review",
        "hardware_limits_review",
        "reference_image_validation",
        "physical_rig_validation",
    )
    real_device_ready: Literal[False] = False
    guidance_allowed: Literal[False] = False

    @model_validator(mode="after")
    def require_consistent_status(self) -> Self:
        if (self.status == "needs_information") != bool(self.missing_information):
            raise ValueError("intake status must reflect missing metadata")
        return self
