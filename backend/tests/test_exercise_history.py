"""Tests for per-exercise runner history (service + REST endpoint).

Only completed sessions count, newest-first; each session exposes that exercise's
set logs ordered by set_number; bodyweight (null weight) is preserved.
"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Exercise, SetLog, WorkoutSession
from app.seed.seed_exercises import build_rows
from app.services.exercise_history import recent_history


@pytest.fixture
async def seeded(db: AsyncSession) -> None:
    for row in build_rows():
        db.add(Exercise(**row))
    await db.commit()


async def _exercise_id(db: AsyncSession) -> int:
    return (await db.scalars(select(Exercise))).first().id


async def _session_with_sets(
    db: AsyncSession,
    *,
    exercise_id: int,
    on_date: date,
    sets: list[tuple[int, int, float | None, float | None]],
    completed: bool = True,
) -> WorkoutSession:
    session = WorkoutSession(date=on_date, completed=completed)
    db.add(session)
    await db.flush()
    for set_number, reps, weight, rpe in sets:
        db.add(
            SetLog(
                session_id=session.id,
                exercise_id=exercise_id,
                set_number=set_number,
                reps=reps,
                weight_kg=weight,
                rpe=rpe,
            )
        )
    await db.commit()
    return session


# --- service ---------------------------------------------------------------


async def test_recent_history_newest_first_completed_only(db: AsyncSession, seeded: None) -> None:
    ex_id = await _exercise_id(db)
    today = date.today()
    old = await _session_with_sets(
        db, exercise_id=ex_id, on_date=today - timedelta(days=7), sets=[(1, 10, 20.0, 8.0)]
    )
    new = await _session_with_sets(
        db, exercise_id=ex_id, on_date=today, sets=[(1, 12, 22.5, 7.0)]
    )
    # incomplete session must be ignored
    await _session_with_sets(
        db, exercise_id=ex_id, on_date=today, sets=[(1, 5, 99.0, None)], completed=False
    )

    history = await recent_history(db, ex_id)
    assert [s.id for s in history] == [new.id, old.id]


async def test_recent_history_respects_limit(db: AsyncSession, seeded: None) -> None:
    ex_id = await _exercise_id(db)
    today = date.today()
    for i in range(4):
        await _session_with_sets(
            db, exercise_id=ex_id, on_date=today - timedelta(days=i), sets=[(1, 10, 20.0, 8.0)]
        )
    assert len(await recent_history(db, ex_id, sessions=2)) == 2


async def test_recent_history_empty_for_unlogged(db: AsyncSession, seeded: None) -> None:
    ex_id = await _exercise_id(db)
    assert await recent_history(db, ex_id) == []


# --- REST endpoint ---------------------------------------------------------


async def test_history_endpoint_shape(client: AsyncClient, db: AsyncSession, seeded: None) -> None:
    ex_id = await _exercise_id(db)
    today = date.today()
    await _session_with_sets(
        db,
        exercise_id=ex_id,
        on_date=today,
        sets=[(2, 12, 22.5, 7.0), (1, 12, 22.5, 8.0)],  # intentionally out of order
    )

    r = await client.get(f"/api/exercises/{ex_id}/history")
    assert r.status_code == 200
    body = r.json()
    assert body["exercise_id"] == ex_id
    assert len(body["sessions"]) == 1
    sets = body["sessions"][0]["sets"]
    assert [s["set_number"] for s in sets] == [1, 2]  # sorted by set_number
    assert sets[0]["reps"] == 12
    assert float(sets[0]["weight_kg"]) == 22.5


async def test_history_endpoint_bodyweight_null_weight(
    client: AsyncClient, db: AsyncSession, seeded: None
) -> None:
    ex_id = await _exercise_id(db)
    await _session_with_sets(
        db, exercise_id=ex_id, on_date=date.today(), sets=[(1, 15, None, None)]
    )
    r = await client.get(f"/api/exercises/{ex_id}/history")
    s = r.json()["sessions"][0]["sets"][0]
    assert s["weight_kg"] is None
    assert s["rpe"] is None


async def test_history_endpoint_unlogged_returns_empty(
    client: AsyncClient, db: AsyncSession, seeded: None
) -> None:
    ex_id = await _exercise_id(db)
    r = await client.get(f"/api/exercises/{ex_id}/history")
    assert r.status_code == 200
    assert r.json()["sessions"] == []


async def test_history_endpoint_missing_exercise_404(client: AsyncClient, seeded: None) -> None:
    assert (await client.get("/api/exercises/999999/history")).status_code == 404
