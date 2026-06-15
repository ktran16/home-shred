from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.enums import FoodLogSource


class NutritionTargetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    tdee_kcal: int
    target_kcal: int
    protein_g: int
    carbs_g: int
    fat_g: int


class SuggestedTargets(BaseModel):
    target_kcal: int
    protein_g: int
    carbs_g: int
    fat_g: int


class FoodFactsOut(BaseModel):
    """Macros for a scanned barcode, per 100 g (SPEC §17.5 B2b)."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str | None
    brand: str | None
    serving_size: str | None
    kcal_per_100g: float | None
    protein_per_100g: float | None
    carbs_per_100g: float | None
    fat_per_100g: float | None


class FoodLogIn(BaseModel):
    date: date_type | None = None
    name: str = Field(min_length=1, max_length=160)
    grams: Decimal = Field(gt=0, le=10000, decimal_places=1)
    kcal: int = Field(ge=0, le=20000)
    protein_g: Decimal = Field(ge=0, le=2000, decimal_places=1)
    carbs_g: Decimal = Field(ge=0, le=2000, decimal_places=1)
    fat_g: Decimal = Field(ge=0, le=2000, decimal_places=1)
    source: FoodLogSource = FoodLogSource.MANUAL
    barcode: str | None = Field(default=None, max_length=32)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Name cannot be blank")
        return stripped

    @field_validator("barcode")
    @classmethod
    def strip_barcode(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class FoodLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    name: str
    grams: Decimal
    kcal: int
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal
    source: FoodLogSource
    barcode: str | None
    created_at: datetime


class FoodLogRecentOut(BaseModel):
    name: str
    grams: Decimal
    kcal: int
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal
    source: FoodLogSource
    barcode: str | None
    last_logged_on: date_type


class FoodLogCopyDayIn(BaseModel):
    from_date: date_type
    to_date: date_type

    @model_validator(mode="after")
    def dates_must_differ(self) -> "FoodLogCopyDayIn":
        if self.from_date == self.to_date:
            raise ValueError("from_date and to_date must differ")
        return self


class FoodLogTotalsOut(BaseModel):
    kcal: int
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal


class DailyFoodLogOut(BaseModel):
    date: date_type
    entries: list[FoodLogOut]
    totals: FoodLogTotalsOut
    target: NutritionTargetOut | None
    remaining_kcal: int | None
    remaining_protein_g: Decimal | None
    remaining_carbs_g: Decimal | None
    remaining_fat_g: Decimal | None


class NutritionHistoryDayOut(BaseModel):
    date: date_type
    logged: bool
    kcal: int
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal
    target_kcal: int | None
    target_protein_g: int | None
    target_carbs_g: int | None
    target_fat_g: int | None
    kcal_adherent: bool


class NutritionHistoryOut(BaseModel):
    start_date: date_type
    end_date: date_type
    days: list[NutritionHistoryDayOut]
    logged_days: int
    target_days: int
    adherent_days: int
    adherence_pct: int


class AdaptiveTDEEOut(BaseModel):
    """Adaptive TDEE preview (SPEC §17.3 A1). When `enough_data` is false the estimate
    fields are null and `reason` explains why."""

    enough_data: bool
    samples: int = 0
    days_span: int = 0
    reason: str | None = None
    static_tdee_kcal: int | None = None
    estimated_tdee_kcal: int | None = None
    assumed_intake_kcal: int | None = None
    weight_change_kg_per_week: float | None = None
    clamped: bool = False
    suggested: SuggestedTargets | None = None
