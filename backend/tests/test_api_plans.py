"""Phase 3 API tests: plan generation, persistence, activation, 409 without profile."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Exercise
from app.seed.seed_exercises import build_rows

PROFILE = {
    "sex": "male",
    "age": 30,
    "height_cm": 180.0,
    "weight_kg": 80.0,
    "activity_level": "moderate",
    "experience_level": "intermediate",
}


@pytest.fixture
async def seeded(db: AsyncSession) -> None:
    for row in build_rows():
        db.add(Exercise(**row))
    await db.commit()


async def test_create_plan_requires_profile(client: AsyncClient, seeded: None) -> None:
    r = await client.post("/api/plans", json={"days_per_week": 4})
    assert r.status_code == 409


async def test_create_and_get_plan(client: AsyncClient, seeded: None) -> None:
    await client.put("/api/profile", json=PROFILE)
    r = await client.post("/api/plans", json={"days_per_week": 4})
    assert r.status_code == 201
    plan = r.json()
    assert plan["is_active"] is True
    assert len(plan["days"]) == 4
    # every selected exercise honours the equipment constraint (SPEC §1)
    for day in plan["days"]:
        assert day["exercises"]
        for pe in day["exercises"]:
            assert pe["exercise"]["equipment"] in {"bodyweight", "dumbbell", "pull_up_bar"}

    got = await client.get(f"/api/plans/{plan['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == plan["id"]


async def test_only_one_active_plan(client: AsyncClient, seeded: None) -> None:
    await client.put("/api/profile", json=PROFILE)
    p1 = (await client.post("/api/plans", json={"days_per_week": 3})).json()
    p2 = (await client.post("/api/plans", json={"days_per_week": 5})).json()

    plans = (await client.get("/api/plans")).json()
    active = [p for p in plans if p["is_active"]]
    assert len(active) == 1 and active[0]["id"] == p2["id"]

    # reactivate the first one
    r = await client.patch(f"/api/plans/{p1['id']}/activate")
    assert r.status_code == 200 and r.json()["is_active"] is True
    plans = (await client.get("/api/plans")).json()
    assert [p["id"] for p in plans if p["is_active"]] == [p1["id"]]


async def test_get_missing_plan_404(client: AsyncClient) -> None:
    assert (await client.get("/api/plans/123456")).status_code == 404
