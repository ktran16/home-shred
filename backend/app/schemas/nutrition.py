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
