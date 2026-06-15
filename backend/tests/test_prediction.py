"""Tests for per-exercise load / readiness forecast (SPEC §17.3 A2)."""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import MovementPattern
from app.models import Exercise, SetLog, WorkoutSession
from app.seed.seed_exercises import build_rows
from app.services.prediction import (
    MIN_SESSIONS_FOR_PREDICTION,
    confidence_for,
    exercise_predictions,
    forecast_next,
    readiness_from,
)


@pytest.fixture
async def seeded(db: AsyncSession) -> None:
    for row in build_rows():
        db.add(Exercise(**row))
    await db.commit()


async def _weighted_exercise_id(db: AsyncSession) -> int:
    stmt = select(Exercise).where(Exercise.pattern == MovementPattern.SQUAT)
    return (await db.scalars(stmt)).first().id


async def _session(
    db: AsyncSession,
    *,
    exercise_id: int,
    on_date: date,
    reps: int,
    weight: float | None,
    rpe: float | None = None,
    completed: bool = True,
) -> None:
    session = WorkoutSession(date=on_date, completed=completed)
    db.add(session)
    await db.flush()
    db.add(
        SetLog(
            session_id=session.id,
            exercise_id=exercise_id,
            set_number=1,
            reps=reps,
            weight_kg=weight,
            rpe=rpe,
        )
    )
    await db.commit()


# --- pure helpers ---------------------------------------------------------------


def test_forecast_next_linear_trend() -> None:
    predicted, slope = forecast_next([10.0, 12.0, 14.0, 16.0])
    assert slope == 2.0
    assert predicted == 18.0  # one step beyond the last point


def test_forecast_next_too_few() -> None:
    assert forecast_next([5.0]) == (None, None)
    assert forecast_next([]) == (None, None)


def test_readiness_from() -> None:
    assert readiness_from(None, None) == "insufficient"
    assert readiness_from(2.0, 7.0) == "progress"
    assert readiness_from(2.0, 9.5) == "hold"  # too fatigued to push
    assert readiness_from(-1.0, 6.0) == "hold"  # flat/declining trend
    assert readiness_from(2.0, None) == "progress"


def test_confidence_for() -> None:
    assert confidence_for(MIN_SESSIONS_FOR_PREDICTION - 1) == 0.0
    assert confidence_for(4) == 0.43
    assert confidence_for(8) == 1.0
    assert confidence_for(20) == 1.0


# --- DB-backed service ----------------------------------------------------------


async def test_predicts_rising_trend(db: AsyncSession, seeded: None) -> None:
    ex_id = await _weighted_exercise_id(db)
    today = date.today()
    for i, weight in enumerate([20.0, 22.5, 25.0, 27.5]):
        await _session(
            db,
            exercise_id=ex_id,
            on_date=today - timedelta(days=21 - i * 7),
            reps=8,
            weight=weight,
            rpe=7.0,
        )

    [pred] = [p for p in await exercise_predictions(db) if p.exercise_id == ex_id]
    assert pred.weighted is True
    assert pred.sessions == 4
    assert pred.predicted_next is not None
    assert pred.trend_per_session is not None and pred.trend_per_session > 0
    assert pred.readiness == "progress"
    assert pred.confidence == confidence_for(4)


async def test_hold_when_recent_rpe_high(db: AsyncSession, seeded: None) -> None:
    ex_id = await _weighted_exercise_id(db)
    today = date.today()
    for i, weight in enumerate([20.0, 22.5, 25.0, 27.5]):
        rpe = 9.5 if i >= 2 else 7.0  # recent sessions are maximal
        await _session(
            db,
            exercise_id=ex_id,
            on_date=today - timedelta(days=21 - i * 7),
            reps=8,
            weight=weight,
            rpe=rpe,
        )

    [pred] = [p for p in await exercise_predictions(db) if p.exercise_id == ex_id]
    assert pred.avg_recent_rpe is not None and pred.avg_recent_rpe >= 9.0
    assert pred.readiness == "hold"


async def test_insufficient_history(db: AsyncSession, seeded: None) -> None:
    ex_id = await _weighted_exercise_id(db)
    await _session(db, exercise_id=ex_id, on_date=date.today(), reps=8, weight=20.0)

    [pred] = [p for p in await exercise_predictions(db) if p.exercise_id == ex_id]
    assert pred.readiness == "insufficient"
    assert pred.predicted_next is None
    assert pred.confidence == 0.0


async def test_prediction_endpoint(client: AsyncClient, db: AsyncSession, seeded: None) -> None:
    ex_id = await _weighted_exercise_id(db)
    today = date.today()
    for i, weight in enumerate([20.0, 22.5, 25.0, 27.5]):
        await _session(
            db, exercise_id=ex_id, on_date=today - timedelta(days=21 - i * 7), reps=8, weight=weight
        )

    r = await client.get("/api/progress/prediction")
    assert r.status_code == 200
    body = r.json()
    entry = next(e for e in body if e["exercise_id"] == ex_id)
    assert entry["sessions"] == 4
    assert entry["predicted_next"] is not None
    assert entry["readiness"] in {"progress", "hold"}
