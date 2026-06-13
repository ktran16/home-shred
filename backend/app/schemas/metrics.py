from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BodyMetricIn(BaseModel):
    date: date_type | None = None
    weight_kg: Decimal = Field(gt=0, le=500)
    body_fat_pct: Decimal | None = Field(default=None, ge=0, le=100)
    waist_cm: Decimal | None = Field(default=None, gt=0, le=300)


class BodyMetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    weight_kg: Decimal
    body_fat_pct: Decimal | None
    waist_cm: Decimal | None


class VolumePoint(BaseModel):
    week: str
    muscle: str
    volume: float
