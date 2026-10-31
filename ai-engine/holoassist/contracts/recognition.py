"""Vision output contract without importing image-processing dependencies."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from holoassist.contracts.models import Contract, NonBlank


class RecognitionResult(Contract):
    status: Literal["matched", "unknown", "low_confidence"]
    reason: NonBlank
    equipment_id: NonBlank | None = None
    reference_kind: Literal["synthetic", "real"]
    good_matches: Annotated[int, Field(strict=True, ge=0)] = 0
    inliers: Annotated[int, Field(strict=True, ge=0)] = 0
    inlier_ratio: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] = 0.0
    corners: tuple[
        tuple[
            Annotated[float, Field(allow_inf_nan=False)],
            Annotated[float, Field(allow_inf_nan=False)],
        ],
        ...,
    ] = ()

    @model_validator(mode="after")
    def require_consistent_identity(self) -> Self:
        if self.inliers > self.good_matches:
            raise ValueError("inliers cannot exceed good matches")
        if self.status == "matched":
            if self.equipment_id is None or len(self.corners) != 4:
                raise ValueError("matched result requires equipment identity and four corners")
        elif self.equipment_id is not None or self.corners:
            raise ValueError("rejected result must not carry equipment identity or corners")
        return self
