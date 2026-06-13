"""SPEC §8 nutrition tests: known-input vectors + macro/kcal consistency (±2%)."""

import pytest
from httpx import AsyncClient

from app.enums import ActivityLevel, Sex
from app.services.nutrition import (
    KCAL_PER_G_CARB,
    KCAL_PER_G_FAT,
    KCAL_PER_G_PROTEIN,
    compute_targets,
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
