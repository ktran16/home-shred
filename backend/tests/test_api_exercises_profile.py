"""Phase 2 API tests: exercises listing/filtering and profile upsert."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Exercise
from app.seed.seed_exercises import build_rows


@pytest.fixture
async def seeded(db: AsyncSession) -> None:
    for row in build_rows():
        db.add(Exercise(**row))
    await db.flush()


async def test_list_exercises(client: AsyncClient, seeded: None) -> None:
    r = await client.get("/api/exercises")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 54
    assert {e["equipment"] for e in data} <= {"bodyweight", "dumbbell", "pull_up_bar"}


async def test_filter_exercises_by_pattern(client: AsyncClient, seeded: None) -> None:
    r = await client.get("/api/exercises", params={"pattern": "vertical_pull"})
    assert r.status_code == 200
    data = r.json()
    assert data and all(e["pattern"] == "vertical_pull" for e in data)


async def test_get_exercise_404(client: AsyncClient, seeded: None) -> None:
    assert (await client.get("/api/exercises/999999")).status_code == 404


async def test_profile_404_then_upsert(client: AsyncClient) -> None:
    assert (await client.get("/api/profile")).status_code == 404
    payload = {
        "sex": "male",
        "age": 30,
        "height_cm": 180.0,
        "weight_kg": 80.0,
        "activity_level": "moderate",
        "experience_level": "intermediate",
    }
    r = await client.put("/api/profile", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == 1
    assert body["sex"] == "male"

    # second PUT updates the same row
    payload["weight_kg"] = 78.5
    r2 = await client.put("/api/profile", json=payload)
    assert r2.status_code == 200
    assert float(r2.json()["weight_kg"]) == 78.5


async def test_profile_validation_422(client: AsyncClient) -> None:
    bad = {
        "sex": "male",
        "age": 5,  # below min
        "height_cm": 180.0,
        "weight_kg": 80.0,
        "activity_level": "moderate",
        "experience_level": "intermediate",
    }
    assert (await client.put("/api/profile", json=bad)).status_code == 422
