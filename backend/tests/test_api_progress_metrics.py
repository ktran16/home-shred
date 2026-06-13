"""Phase 5 tests: weekly volume aggregation and body metrics."""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Exercise, SetLog, WorkoutSession

PROFILE = {
    "sex": "male",
    "age": 30,
    "height_cm": 180.0,
    "weight_kg": 80.0,
    "activity_level": "moderate",
    "experience_level": "intermediate",
}


@pytest.fixture
async def exercise(db: AsyncSession) -> Exercise:
    ex = Exercise(
        name="Test Press",
        slug="test_press",
        equipment="dumbbell",
        pattern="horizontal_push",
        category="push",
        primary_muscles=["chest", "triceps"],
        secondary_muscles=[],
        level="intermediate",
        is_compound=True,
        instructions=[],
    )
    db.add(ex)
    await db.commit()
    await db.refresh(ex)
    return ex


async def test_weekly_volume_weighted(
    client: AsyncClient, db: AsyncSession, exercise: Exercise
) -> None:
    sess = WorkoutSession(date=date(2026, 6, 1), completed=True)
    db.add(sess)
    await db.flush()
    # 3 sets × 10 reps × 20 kg = 600 per muscle
    for n in range(1, 4):
        db.add(
            SetLog(session_id=sess.id, exercise_id=exercise.id, set_number=n, reps=10, weight_kg=20)
        )
    await db.commit()

    r = await client.get("/api/progress/volume")
    assert r.status_code == 200
    data = {(p["muscle"]): p["volume"] for p in r.json()}
    assert data["chest"] == 600.0
    assert data["triceps"] == 600.0
    assert all(p["week"] == "2026-W23" for p in r.json())


async def test_weekly_volume_bodyweight_proxy(
    client: AsyncClient, db: AsyncSession, exercise: Exercise
) -> None:
    await client.put("/api/profile", json=PROFILE)  # bodyweight 80kg
    sess = WorkoutSession(date=date(2026, 6, 1), completed=True)
    db.add(sess)
    await db.flush()
    db.add(
        SetLog(session_id=sess.id, exercise_id=exercise.id, set_number=1, reps=10, weight_kg=None)
    )
    await db.commit()

    r = await client.get("/api/progress/volume")
    # 10 reps × (80 × 1.0) = 800
    data = {p["muscle"]: p["volume"] for p in r.json()}
    assert data["chest"] == 800.0


async def test_incomplete_sessions_excluded(
    client: AsyncClient, db: AsyncSession, exercise: Exercise
) -> None:
    sess = WorkoutSession(date=date(2026, 6, 1), completed=False)
    db.add(sess)
    await db.flush()
    db.add(SetLog(session_id=sess.id, exercise_id=exercise.id, set_number=1, reps=10, weight_kg=20))
    await db.commit()
    assert (await client.get("/api/progress/volume")).json() == []


async def test_body_metrics_upsert_and_list(client: AsyncClient) -> None:
    r = await client.post(
        "/api/body-metrics", json={"date": "2026-06-01", "weight_kg": 80.0, "waist_cm": 85.0}
    )
    assert r.status_code == 201

    # same date upserts (no duplicate, value updated)
    r2 = await client.post("/api/body-metrics", json={"date": "2026-06-01", "weight_kg": 79.5})
    assert r2.status_code == 201

    rows = (await client.get("/api/body-metrics")).json()
    assert len(rows) == 1
    assert float(rows[0]["weight_kg"]) == 79.5


async def test_body_metrics_range_filter(client: AsyncClient) -> None:
    for d, w in [("2026-05-01", 82.0), ("2026-06-01", 80.0), ("2026-07-01", 78.0)]:
        await client.post("/api/body-metrics", json={"date": d, "weight_kg": w})
    rows = (
        await client.get("/api/body-metrics", params={"from": "2026-06-01", "to": "2026-06-30"})
    ).json()
    assert [r["date"] for r in rows] == ["2026-06-01"]
