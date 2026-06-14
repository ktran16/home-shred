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
        "name": "Main",
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
    assert body["name"] == "Main"
    assert body["is_active"] is True
    assert body["sex"] == "male"

    # second PUT updates the same row
    payload["weight_kg"] = 78.5
    r2 = await client.put("/api/profile", json=payload)
    assert r2.status_code == 200
    assert float(r2.json()["weight_kg"]) == 78.5


async def test_profile_management_create_switch_delete(client: AsyncClient) -> None:
    first = {
        "name": "Alice",
        "sex": "female",
        "age": 32,
        "height_cm": 165.0,
        "weight_kg": 62.0,
        "activity_level": "light",
        "experience_level": "beginner",
    }
    second = {
        "name": "Bob",
        "sex": "male",
        "age": 40,
        "height_cm": 178.0,
        "weight_kg": 84.0,
        "activity_level": "active",
        "experience_level": "advanced",
    }

    r1 = await client.post("/api/profile", json=first)
    assert r1.status_code == 201
    first_id = r1.json()["id"]
    r2 = await client.post("/api/profile", json=second)
    assert r2.status_code == 201
    second_id = r2.json()["id"]

    profiles = (await client.get("/api/profile/all")).json()
    assert [p["name"] for p in profiles] == ["Bob", "Alice"]
    assert [p["is_active"] for p in profiles] == [True, False]
    assert (await client.get("/api/profile")).json()["name"] == "Bob"

    switched = await client.patch(f"/api/profile/{first_id}/activate")
    assert switched.status_code == 200
    assert switched.json()["name"] == "Alice"
    assert (await client.get("/api/profile")).json()["id"] == first_id

    deleted = await client.delete(f"/api/profile/{first_id}")
    assert deleted.status_code == 204
    active = (await client.get("/api/profile")).json()
    assert active["id"] == second_id
    assert active["is_active"] is True

    cannot_delete_last = await client.delete(f"/api/profile/{second_id}")
    assert cannot_delete_last.status_code == 409


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
