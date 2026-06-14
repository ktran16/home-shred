from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.enums import ActivityLevel, Level, Sex


class ProfileIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    sex: Sex
    age: int = Field(ge=14, le=100)
    height_cm: Decimal = Field(gt=0, le=300, decimal_places=1)
    weight_kg: Decimal = Field(gt=0, le=500, decimal_places=1)
    activity_level: ActivityLevel
    experience_level: Level


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_active: bool
    sex: Sex
    age: int
    height_cm: Decimal
    weight_kg: Decimal
    activity_level: ActivityLevel
    experience_level: Level
    updated_at: datetime
