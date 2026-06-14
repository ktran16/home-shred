"""SPEC §8 nutrition tests + §17.3 A1 adaptive TDEE."""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import ActivityLevel, Sex
from app.models import BodyMetric
from app.services.nutrition import (
    KCAL_PER_G_CARB,
    KCAL_PER_G_FAT,
    KCAL_PER_G_PROTEIN,
    adaptive_estimate,
    compute_targets,
    linear_slope,
)


def _macro_kcal(t) -> int:
    return t.protein_g * KCAL_PER_G_PROTEIN + t.carbs_g * KCAL_PER_G_CARB + t.fat_g * KCAL_PER_G_FAT


def test_male_vector() -> None:
    # male, 80kg, 180cm, 30y, moderate (×1.55)
    t = compute_targets(
        sex=Sex.MALE, weight_kg=80, height_cm=180, age=30, activity_level=ActivityLevel.MODERATE
    )
    assert t.tdee_kcal == 2759
    assert t.target_kcal == 2207
    assert t.protein_g == 160
    assert t.fat_g == 64
    assert abs(_macro_kcal(t) - t.target_kcal) / t.target_kcal <= 0.02


def test_female_vector() -> None:
    # female, 60kg, 165cm, 28y, light (×1.375)
    t = compute_targets(
        sex=Sex.FEMALE, weight_kg=60, height_cm=165, age=28, activity_level=ActivityLevel.LIGHT
    )
    assert t.target_kcal == 1463
    assert t.protein_g == 120
    assert t.fat_g == 48
    assert abs(_macro_kcal(t) - t.target_kcal) / t.target_kcal <= 0.02


@pytest.mark.parametrize("sex", [Sex.MALE, Sex.FEMALE])
@pytest.mark.parametrize("activity", list(ActivityLevel))
def test_macro_kcal_within_tolerance(sex: Sex, activity: ActivityLevel) -> None:
    t = compute_targets(sex=sex, weight_kg=75, height_cm=175, age=35, activity_level=activity)
    assert abs(_macro_kcal(t) - t.target_kcal) / t.target_kcal <= 0.02
    assert t.carbs_g >= 0


PROFILE = {
    "sex": "male",
    "age": 30,
    "height_cm": 180.0,
    "weight_kg": 80.0,
    "activity_level": "moderate",
    "experience_level": "intermediate",
}


async def test_targets_404_then_recompute_on_profile_put(client: AsyncClient) -> None:
    assert (await client.get("/api/nutrition/targets")).status_code == 404
    # PUT profile triggers recompute (SPEC §8)
    await client.put("/api/profile", json=PROFILE)
    r = await client.get("/api/nutrition/targets")
    assert r.status_code == 200
    assert r.json()["target_kcal"] == 2207


async def test_recompute_endpoint_409_without_profile(client: AsyncClient) -> None:
    assert (await client.post("/api/nutrition/recompute")).status_code == 409


# --- §17.3 A1 adaptive TDEE ---


def test_linear_slope() -> None:
    assert linear_slope([0, 1, 2, 3], [0, 2, 4, 6]) == 2.0
    assert linear_slope([0, 7, 14], [80.0, 80.0, 80.0]) == 0.0


def test_adaptive_estimate_weight_loss_raises_tdee_above_intake() -> None:
    # 0.5 kg/week loss while eating 2207 → real TDEE ≈ intake + 550
    points = [(date(2026, 1, 1) + timedelta(days=7 * i), 80.0 - 0.5 * i) for i in range(5)]
    est = adaptive_estimate(
        static_tdee_kcal=2759,
        static_target_kcal=2207,
        weight_points=points,
        intake_kcals=[2207],
        latest_weight_kg=78.0,
    )
    assert est is not None
    assert est.estimated_tdee_kcal == 2757  # 2207 + 0.5/7*7700
    assert est.weight_change_kg_per_week == -0.5
    assert est.assumed_intake_kcal == 2207
    assert est.clamped is False
    assert est.targets.target_kcal == 2206  # round(2757 * 0.80)


def test_adaptive_estimate_clamps_implausible_trend() -> None:
    # absurd 0.3 kg/day loss would imply a wild TDEE → clamped to +25%
    points = [(date(2026, 1, 1) + timedelta(days=7 * i), 80.0 - 2.1 * i) for i in range(4)]
    est = adaptive_estimate(
        static_tdee_kcal=2759,
        static_target_kcal=2207,
        weight_points=points,
        intake_kcals=[2207],
        latest_weight_kg=72.0,
    )
    assert est is not None and est.clamped is True
    assert est.estimated_tdee_kcal == round(2759 * 1.25)


def test_adaptive_estimate_insufficient_samples() -> None:
    points = [(date(2026, 1, 1), 80.0), (date(2026, 1, 20), 79.0)]  # only 2
    assert (
        adaptive_estimate(
            static_tdee_kcal=2759,
            static_target_kcal=2207,
            weight_points=points,
            intake_kcals=[2207],
            latest_weight_kg=79.0,
        )
        is None
    )


def test_adaptive_estimate_insufficient_span() -> None:
    points = [(date(2026, 1, 1) + timedelta(days=2 * i), 80.0 - 0.1 * i) for i in range(5)]
    assert (
        adaptive_estimate(  # spans 8 days < 14
            static_tdee_kcal=2759,
            static_target_kcal=2207,
            weight_points=points,
            intake_kcals=[2207],
            latest_weight_kg=79.6,
        )
        is None
    )


async def test_adaptive_endpoint_not_enough_data(client: AsyncClient) -> None:
    await client.put("/api/profile", json=PROFILE)
    r = await client.get("/api/nutrition/adaptive")
    assert r.status_code == 200
    assert r.json()["enough_data"] is False


async def test_adaptive_endpoint_404_without_profile(client: AsyncClient) -> None:
    assert (await client.get("/api/nutrition/adaptive")).status_code == 404


async def test_adaptive_flow_with_history(client: AsyncClient, db: AsyncSession) -> None:
    await client.put("/api/profile", json=PROFILE)  # creates a target row (intake proxy)
    # 4 weigh-ins over 21 days, steady 0.5 kg/week loss
    today = date.today()
    for i in range(4):
        db.add(BodyMetric(date=today - timedelta(days=21 - 7 * i), weight_kg=80.0 - 0.5 * i))
    await db.commit()

    preview = (await client.get("/api/nutrition/adaptive")).json()
    assert preview["enough_data"] is True
    assert preview["samples"] == 4
    assert preview["estimated_tdee_kcal"] > preview["assumed_intake_kcal"]  # losing → TDEE>intake
    assert preview["suggested"]["target_kcal"] > 0

    applied = await client.post("/api/nutrition/adaptive/apply")
    assert applied.status_code == 200
    assert applied.json()["target_kcal"] == preview["suggested"]["target_kcal"]
    # latest target now reflects the adaptive value
    latest = (await client.get("/api/nutrition/targets")).json()
    assert latest["target_kcal"] == preview["suggested"]["target_kcal"]
