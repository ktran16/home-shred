from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MeasurementTypeIn(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    unit: str = Field(default="cm", min_length=1, max_length=16)

    @field_validator("label", "unit")
    @classmethod
    def _strip(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class MeasurementTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    label: str
    unit: str
    builtin: bool


class MeasurementEntryIn(BaseModel):
    type_id: int
    date: date_type | None = None
    value: Decimal = Field(gt=0, le=1000, decimal_places=2)


class MeasurementEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type_id: int
    date: date_type
    value: Decimal


class MeasurementSeriesPointOut(BaseModel):
    date: date_type
    value: Decimal


class MeasurementSeriesOut(BaseModel):
    """One measurement type plus its chronological points (for /progress charts)."""

    type: MeasurementTypeOut
    points: list[MeasurementSeriesPointOut]
    latest: Decimal | None
    change: Decimal | None  # latest − first within the window
