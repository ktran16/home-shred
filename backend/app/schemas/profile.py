from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.enums import ActivityLevel, Level, Sex

ProfileLimitation = Literal["shoulder", "knee", "lower_back", "wrist", "pull_up"]
LIMITATIONS: set[str] = {"shoulder", "knee", "lower_back", "wrist", "pull_up"}


class ProfileIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    sex: Sex
    age: int = Field(ge=14, le=100)
    height_cm: Decimal = Field(gt=0, le=300, decimal_places=1)
    weight_kg: Decimal = Field(gt=0, le=500, decimal_places=1)
    activity_level: ActivityLevel
    experience_level: Level
    limitations: list[ProfileLimitation] = Field(default_factory=list)

    @field_validator("limitations")
    @classmethod
    def unique_limitations(cls, value: list[ProfileLimitation]) -> list[ProfileLimitation]:
        seen: set[str] = set()
        return [item for item in value if not (item in seen or seen.add(item))]


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
    limitations: list[ProfileLimitation]
    updated_at: datetime
