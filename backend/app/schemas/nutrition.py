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
