"""Phase 4 API tests: session create (with suggestions), set logging, complete."""

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


async def _make_plan(client: AsyncClient) -> dict:
    await client.put("/api/profile", json=PROFILE)
    return (await client.post("/api/plans", json={"days_per_week": 4})).json()


async def test_create_session_returns_suggestions(client: AsyncClient, seeded: None) -> None:
    plan = await _make_plan(client)
    day = plan["days"][0]
    r = await client.post("/api/sessions", json={"plan_day_id": day["id"]})
    assert r.status_code == 201
    body = r.json()
    assert body["completed"] is False
    # one suggestion per exercise in the day
    assert len(body["suggested_targets"]) == len(day["exercises"])
    ex_ids = {pe["exercise_id"] for pe in day["exercises"]}
    assert {t["exercise_id"] for t in body["suggested_targets"]} == ex_ids
    for t in body["suggested_targets"]:
        assert t["sets"] >= 2


async def test_log_sets_and_complete(client: AsyncClient, seeded: None) -> None:
    plan = await _make_plan(client)
    day = plan["days"][0]
    sess = (await client.post("/api/sessions", json={"plan_day_id": day["id"]})).json()
    ex_id = day["exercises"][0]["exercise_id"]

    for set_no in (1, 2, 3):
        r = await client.post(
            f"/api/sessions/{sess['id']}/sets",
            json={"exercise_id": ex_id, "set_number": set_no, "reps": 10, "weight_kg": 20.0},
        )
        assert r.status_code == 201

    detail = (await client.get(f"/api/sessions/{sess['id']}")).json()
    assert len(detail["set_logs"]) == 3

    done = await client.patch(
        f"/api/sessions/{sess['id']}/complete",
        json={"notes": "Tags: felt strong\n\nGood session."},
    )
    assert done.status_code == 200 and done.json()["completed"] is True
    assert "felt strong" in done.json()["notes"]


async def test_complete_records_impression(client: AsyncClient, seeded: None) -> None:
    plan = await _make_plan(client)
    day = plan["days"][0]
    sess = (await client.post("/api/sessions", json={"plan_day_id": day["id"]})).json()

    # impression defaults to null until set on completion (SPEC §19.8 W4)
    assert sess["impression"] is None
    done = await client.patch(
        f"/api/sessions/{sess['id']}/complete",
        json={"impression": "good"},
    )
    assert done.status_code == 200
    assert done.json()["impression"] == "good"
    # it survives a re-fetch
    assert (await client.get(f"/api/sessions/{sess['id']}")).json()["impression"] == "good"


async def test_progression_applies_next_session(client: AsyncClient, seeded: None) -> None:
    """After a completed session at top-of-range with weight, next suggestion bumps weight."""
    plan = await _make_plan(client)
    day = plan["days"][0]
    # find a compound (weighted) target: reps 6-10
    pe = next(
        p for p in day["exercises"] if (p["target_reps_min"], p["target_reps_max"]) == (6, 10)
    )
    ex_id = pe["exercise_id"]

    s1 = (await client.post("/api/sessions", json={"plan_day_id": day["id"]})).json()
    for set_no in range(1, pe["sets"] + 1):
        await client.post(
            f"/api/sessions/{s1['id']}/sets",
            json={"exercise_id": ex_id, "set_number": set_no, "reps": 10, "weight_kg": 20.0},
        )
    await client.patch(f"/api/sessions/{s1['id']}/complete")

    s2 = (await client.post("/api/sessions", json={"plan_day_id": day["id"]})).json()
    target = next(t for t in s2["suggested_targets"] if t["exercise_id"] == ex_id)
    assert target["suggested_weight_kg"] == 22.5


async def test_create_session_missing_plan_day_404(client: AsyncClient) -> None:
    assert (await client.post("/api/sessions", json={"plan_day_id": 999})).status_code == 404


async def test_log_set_missing_session_404(client: AsyncClient) -> None:
    r = await client.post(
        "/api/sessions/999/sets",
        json={"exercise_id": 1, "set_number": 1, "reps": 5},
    )
    assert r.status_code == 404
