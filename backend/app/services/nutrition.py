"""Nutrition targets (SPEC §8): Mifflin-St Jeor BMR → TDEE → shred macros.
Adaptive TDEE (SPEC §17.3 A1) estimates real maintenance from the bodyweight trend.

`compute_targets` / `adaptive_estimate` are pure for unit testing; `recompute` /
`apply_adaptive` persist a dated row.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import ACTIVITY_FACTORS, ActivityLevel, Sex
from app.models import BodyMetric, NutritionTarget
from app.services.profile import get_profile

# rationale (SPEC §8): shred = 20% deficit; protein 2.0 g/kg to preserve muscle in a
# deficit; fat 0.8 g/kg; remaining calories → carbs.
DEFICIT_FACTOR = 0.80
PROTEIN_G_PER_KG = 2.0
FAT_G_PER_KG = 0.8
KCAL_PER_G_PROTEIN = 4
KCAL_PER_G_CARB = 4
KCAL_PER_G_FAT = 9

# rationale (SPEC §17.3 A1): adaptive TDEE. ~7700 kcal ≈ energy in 1 kg of body-mass
# change, so observed weight trend reveals real maintenance:
#   estimated_TDEE = mean_intake − (kg/day trend × 7700)
# Intake is assumed to equal the target in effect (no food log yet — documented
# simplification, like §9's bodyweight proxy). Guardrails keep noisy data from swinging
# the estimate wildly.
KCAL_PER_KG = 7700
ADAPTIVE_WINDOW_DAYS = 28  # how far back to look for metrics/targets
ADAPTIVE_MIN_SAMPLES = 4  # need ≥4 weigh-ins
ADAPTIVE_MIN_DAYS_SPAN = 14  # spanning ≥2 weeks
ADAPTIVE_TDEE_CLAMP = 0.25  # estimate stays within ±25% of static TDEE


@dataclass
class NutritionTargets:
    tdee_kcal: int
    target_kcal: int
    protein_g: int
    carbs_g: int
    fat_g: int


def _targets_from_tdee(tdee: float, weight_kg: float) -> NutritionTargets:
    """Shred deficit + macro split for a given TDEE and bodyweight (SPEC §8)."""
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


def compute_targets(
    *, sex: Sex, weight_kg: float, height_cm: float, age: int, activity_level: ActivityLevel
) -> NutritionTargets:
    # Mifflin-St Jeor BMR.
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    bmr = base + (5 if sex == Sex.MALE else -161)
    tdee = bmr * ACTIVITY_FACTORS[activity_level]
    return _targets_from_tdee(tdee, weight_kg)


def linear_slope(xs: list[float], ys: list[float]) -> float:
    """Least-squares slope (units of y per unit x). Robust trend over noisy daily data."""
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    var = sum((x - mean_x) ** 2 for x in xs)
    if var == 0:
        return 0.0
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    return cov / var


@dataclass
class AdaptiveEstimate:
    static_tdee_kcal: int
    estimated_tdee_kcal: int
    assumed_intake_kcal: int
    weight_change_kg_per_week: float
    samples: int
    days_span: int
    clamped: bool
    targets: NutritionTargets


def adaptive_estimate(
    *,
    static_tdee_kcal: int,
    static_target_kcal: int,
    weight_points: list[tuple[date, float]],
    intake_kcals: list[int],
    latest_weight_kg: float,
) -> AdaptiveEstimate | None:
    """Estimate real TDEE from the bodyweight trend (SPEC §17.3 A1). Pure/testable.

    `weight_points` must be sorted by date. `intake_kcals` are the target_kcal values in
    effect over the window (assumed intake); if empty, falls back to the static target.
    Returns None when there isn't enough history to trust a trend.
    """
    if len(weight_points) < ADAPTIVE_MIN_SAMPLES:
        return None
    first_day, last_day = weight_points[0][0], weight_points[-1][0]
    days_span = (last_day - first_day).days
    if days_span < ADAPTIVE_MIN_DAYS_SPAN:
        return None

    xs = [float((d - first_day).days) for d, _ in weight_points]
    ys = [w for _, w in weight_points]
    slope_kg_per_day = linear_slope(xs, ys)

    mean_intake = (
        round(sum(intake_kcals) / len(intake_kcals)) if intake_kcals else static_target_kcal
    )
    raw_tdee = mean_intake - slope_kg_per_day * KCAL_PER_KG

    lo = static_tdee_kcal * (1 - ADAPTIVE_TDEE_CLAMP)
    hi = static_tdee_kcal * (1 + ADAPTIVE_TDEE_CLAMP)
    clamped = raw_tdee < lo or raw_tdee > hi
    estimated_tdee = round(min(max(raw_tdee, lo), hi))

    return AdaptiveEstimate(
        static_tdee_kcal=static_tdee_kcal,
        estimated_tdee_kcal=estimated_tdee,
        assumed_intake_kcal=mean_intake,
        weight_change_kg_per_week=round(slope_kg_per_day * 7, 3),
        samples=len(weight_points),
        days_span=days_span,
        clamped=clamped,
        targets=_targets_from_tdee(estimated_tdee, latest_weight_kg),
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


async def adaptive_targets(db: AsyncSession) -> AdaptiveEstimate | None:
    """Adaptive TDEE estimate from recent body metrics + targets (SPEC §17.3 A1).

    Returns None when there's no profile or not enough weigh-in history.
    """
    profile = await get_profile(db)
    if profile is None:
        return None
    static = compute_targets(
        sex=profile.sex,
        weight_kg=float(profile.weight_kg),
        height_cm=float(profile.height_cm),
        age=profile.age,
        activity_level=profile.activity_level,
    )

    since = date.today() - timedelta(days=ADAPTIVE_WINDOW_DAYS)
    metrics = list(
        await db.scalars(
            select(BodyMetric).where(BodyMetric.date >= since).order_by(BodyMetric.date)
        )
    )
    targets = list(await db.scalars(select(NutritionTarget).where(NutritionTarget.date >= since)))

    weight_points = [(m.date, float(m.weight_kg)) for m in metrics]
    latest_weight = weight_points[-1][1] if weight_points else float(profile.weight_kg)

    return adaptive_estimate(
        static_tdee_kcal=static.tdee_kcal,
        static_target_kcal=static.target_kcal,
        weight_points=weight_points,
        intake_kcals=[t.target_kcal for t in targets],
        latest_weight_kg=latest_weight,
    )


async def apply_adaptive(db: AsyncSession) -> NutritionTarget | None:
    """Persist today's targets using the adaptive TDEE estimate. None if not enough data."""
    est = await adaptive_targets(db)
    if est is None:
        return None
    today = date.today()
    existing = await db.scalar(select(NutritionTarget).where(NutritionTarget.date == today))
    if existing is None:
        existing = NutritionTarget(date=today)
        db.add(existing)
    existing.tdee_kcal = est.targets.tdee_kcal
    existing.target_kcal = est.targets.target_kcal
    existing.protein_g = est.targets.protein_g
    existing.carbs_g = est.targets.carbs_g
    existing.fat_g = est.targets.fat_g
    await db.commit()
    await db.refresh(existing)
    return existing
