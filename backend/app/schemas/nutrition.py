from datetime import date as date_type

from pydantic import BaseModel, ConfigDict


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
