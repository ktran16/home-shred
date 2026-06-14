"""Tests for personal records & e1RM strength trend (SPEC §18)."""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import MovementPattern
from app.models import Exercise, SetLog, WorkoutSession
from app.seed.seed_exercises import build_rows
from app.services.strength import epley_1rm, exercise_strength


@pytest.fixture
async def seeded(db: AsyncSession) -> None:
    for row in build_rows():
        db.add(Exercise(**row))
    await db.commit()


async def _exercise_id(db: AsyncSession, *, weighted: bool) -> int:
    """A dumbbell (weighted) or bodyweight exercise id from the seed."""
    stmt = select(Exercise)
    if weighted:
        stmt = stmt.where(Exercise.pattern == MovementPattern.SQUAT)
    else:
        stmt = stmt.where(Exercise.pattern == MovementPattern.HORIZONTAL_PUSH)
    return (await db.scalars(stmt)).first().id


async def _session(
    db: AsyncSession,
    *,
    exercise_id: int,
    on_date: date,
    sets: list[tuple[int, int, float | None]],  # (set_number, reps, weight)
    completed: bool = True,
) -> None:
    session = WorkoutSession(date=on_date, completed=completed)
    db.add(session)
    await db.flush()
    for set_number, reps, weight in sets:
        db.add(
            SetLog(
                session_id=session.id,
                exercise_id=exercise_id,
                set_number=set_number,
                reps=reps,
                weight_kg=weight,
            )
        )
    await db.commit()


def test_epley_formula() -> None:
    assert epley_1rm(10, 20.0) == 26.7  # 20 * (1 + 10/30)
    assert epley_1rm(5, 40.0) == round(40.0 * (1 + 5 / 30), 1)  # 46.7
    assert epley_1rm(12, None) is None
    assert epley_1rm(12, 0) is None


async def test_weighted_prs_and_trend(db: AsyncSession, seeded: None) -> None:
    ex_id = await _exercise_id(db, weighted=True)
    today = date.today()
    await _session(db, exercise_id=ex_id, on_date=today - timedelta(days=14), sets=[(1, 10, 20.0)])
    await _session(db, exercise_id=ex_id, on_date=today - timedelta(days=7), sets=[(1, 8, 25.0)])
    await _session(db, exercise_id=ex_id, on_date=today, sets=[(1, 10, 25.0), (2, 6, 25.0)])

    [result] = [r for r in await exercise_strength(db) if r.exercise_id == ex_id]
    assert result.weighted is True
    assert result.best_weight == 25.0
    assert result.best_e1rm == epley_1rm(10, 25.0)  # 33.3, the latest session
    assert [p.date for p in result.points] == sorted(p.date for p in result.points)  # chronological
    assert len(result.points) == 3
    assert result.latest_is_pr is True  # last session is a new e1RM best


async def test_latest_not_pr_when_below_prior(db: AsyncSession, seeded: None) -> None:
    ex_id = await _exercise_id(db, weighted=True)
    today = date.today()
    await _session(db, exercise_id=ex_id, on_date=today - timedelta(days=7), sets=[(1, 10, 30.0)])
    await _session(db, exercise_id=ex_id, on_date=today, sets=[(1, 8, 20.0)])  # weaker

    [result] = [r for r in await exercise_strength(db) if r.exercise_id == ex_id]
    assert result.latest_is_pr is False
    assert result.best_e1rm == epley_1rm(10, 30.0)


async def test_bodyweight_tracks_reps(db: AsyncSession, seeded: None) -> None:
    ex_id = await _exercise_id(db, weighted=False)
    today = date.today()
    await _session(db, exercise_id=ex_id, on_date=today - timedelta(days=7), sets=[(1, 12, None)])
    await _session(db, exercise_id=ex_id, on_date=today, sets=[(1, 15, None), (2, 13, None)])

    [result] = [r for r in await exercise_strength(db) if r.exercise_id == ex_id]
    assert result.weighted is False
    assert result.best_e1rm is None
    assert result.best_reps == 15
    assert result.latest_is_pr is True  # 15 > prior 12


async def test_excludes_incomplete_and_empty(db: AsyncSession, seeded: None) -> None:
    ex_id = await _exercise_id(db, weighted=True)
    await _session(
        db, exercise_id=ex_id, on_date=date.today(), sets=[(1, 5, 99.0)], completed=False
    )
    assert await exercise_strength(db) == []


async def test_strength_endpoint(client: AsyncClient, db: AsyncSession, seeded: None) -> None:
    ex_id = await _exercise_id(db, weighted=True)
    await _session(db, exercise_id=ex_id, on_date=date.today(), sets=[(1, 10, 22.5)])

    r = await client.get("/api/progress/strength")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    entry = body[0]
    assert entry["exercise_id"] == ex_id
    assert entry["weighted"] is True
    assert entry["best_e1rm"] == epley_1rm(10, 22.5)
    assert len(entry["points"]) == 1
