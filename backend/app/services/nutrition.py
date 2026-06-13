"""Nutrition targets (SPEC §8): Mifflin-St Jeor BMR → TDEE → shred macros.

`compute_targets` is pure for unit testing; `recompute` persists a dated row.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import ACTIVITY_FACTORS, ActivityLevel, Sex
from app.models import NutritionTarget
from app.services.profile import get_profile

# rationale (SPEC §8): shred = 20% deficit; protein 2.0 g/kg to preserve muscle in a
# deficit; fat 0.8 g/kg; remaining calories → carbs.
DEFICIT_FACTOR = 0.80
PROTEIN_G_PER_KG = 2.0
FAT_G_PER_KG = 0.8
KCAL_PER_G_PROTEIN = 4
KCAL_PER_G_CARB = 4
KCAL_PER_G_FAT = 9


@dataclass
class NutritionTargets:
    tdee_kcal: int
    target_kcal: int
    protein_g: int
    carbs_g: int
    fat_g: int


def compute_targets(
    *, sex: Sex, weight_kg: float, height_cm: float, age: int, activity_level: ActivityLevel
) -> NutritionTargets:
    # Mifflin-St Jeor BMR.
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    bmr = base + (5 if sex == Sex.MALE else -161)
    tdee = bmr * ACTIVITY_FACTORS[activity_level]

    target = round(tdee * DEFICIT_FACTOR)
    protein = round(PROTEIN_G_PER_KG * weight_kg)
    fat = round(FAT_G_PER_KG * weight_kg)
    remaining = target - (protein * KCAL_PER_G_PROTEIN + fat * KCAL_PER_G_FAT)
    carbs = max(0, round(remaining / KCAL_PER_G_CARB))

    return NutritionTargets(
        tdee_kcal=round(tdee),
        target_kcal=target,
        protein_g=protein,
        carbs_g=carbs,
        fat_g=fat,
    )


async def recompute(db: AsyncSession) -> NutritionTarget | None:
    """Recompute targets from the current profile and persist a row dated today."""
    profile = await get_profile(db)
    if profile is None:
        return None

    targets = compute_targets(
        sex=profile.sex,
        weight_kg=float(profile.weight_kg),
        height_cm=float(profile.height_cm),
        age=profile.age,
        activity_level=profile.activity_level,
    )

    today = date.today()
    existing = await db.scalar(select(NutritionTarget).where(NutritionTarget.date == today))
    if existing is None:
        existing = NutritionTarget(date=today)
        db.add(existing)
    existing.tdee_kcal = targets.tdee_kcal
    existing.target_kcal = targets.target_kcal
    existing.protein_g = targets.protein_g
    existing.carbs_g = targets.carbs_g
    existing.fat_g = targets.fat_g
    await db.commit()
    await db.refresh(existing)
    return existing


async def latest(db: AsyncSession) -> NutritionTarget | None:
    stmt = select(NutritionTarget).order_by(NutritionTarget.date.desc(), NutritionTarget.id.desc())
    return await db.scalar(stmt.limit(1))
