"""Workout sessions: create (with progression-based suggestions), log sets, complete."""

from datetime import UTC, date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import PlanDay, SetLog, WorkoutSession
from app.schemas.session import SetLogIn, SuggestedTargetOut
from app.services.progression import suggest_next_targets, week_number

_RECENT_SESSIONS = 3  # how many completed sessions of history feed progression


class PlanDayNotFoundError(Exception):
    """Raised when creating a session for a missing plan_day (router → 404)."""


async def _load_session(db: AsyncSession, session_id: int) -> WorkoutSession | None:
    stmt = (
        select(WorkoutSession)
        .where(WorkoutSession.id == session_id)
        .options(selectinload(WorkoutSession.set_logs))
    )
    return await db.scalar(stmt)


async def _recent_completed(db: AsyncSession, plan_day_id: int) -> list[WorkoutSession]:
    stmt = (
        select(WorkoutSession)
        .where(
            WorkoutSession.plan_day_id == plan_day_id,
            WorkoutSession.completed.is_(True),
        )
        .order_by(WorkoutSession.date.desc(), WorkoutSession.id.desc())
        .options(selectinload(WorkoutSession.set_logs))
        .limit(_RECENT_SESSIONS)
    )
    return list((await db.scalars(stmt)).all())


async def create_session(
    db: AsyncSession, *, plan_day_id: int, on_date: date | None = None
) -> tuple[WorkoutSession, list[SuggestedTargetOut]]:
    stmt = (
        select(PlanDay)
        .where(PlanDay.id == plan_day_id)
        .options(selectinload(PlanDay.exercises), selectinload(PlanDay.plan))
    )
    plan_day = await db.scalar(stmt)
    if plan_day is None:
        raise PlanDayNotFoundError

    session = WorkoutSession(plan_day_id=plan_day_id, date=on_date or date.today())
    db.add(session)
    await db.commit()

    history = await _recent_completed(db, plan_day_id)
    plan_start = plan_day.plan.created_at.astimezone(UTC).date()
    week = week_number(plan_start, session.date)

    suggestions: list[SuggestedTargetOut] = []
    for pe in plan_day.exercises:
        per_exercise = [
            [log for log in s.set_logs if log.exercise_id == pe.exercise_id] for s in history
        ]
        per_exercise = [logs for logs in per_exercise if logs]  # drop sessions w/o this exercise
        targets = suggest_next_targets(pe, per_exercise, week)
        suggestions.append(
            SuggestedTargetOut(
                exercise_id=pe.exercise_id,
                sets=targets.sets,
                reps_min=targets.reps_min,
                reps_max=targets.reps_max,
                suggested_weight_kg=targets.suggested_weight_kg,
            )
        )

    loaded = await _load_session(db, session.id)
    assert loaded is not None
    return loaded, suggestions


async def add_set_log(db: AsyncSession, session_id: int, data: SetLogIn) -> SetLog | None:
    session = await db.get(WorkoutSession, session_id)
    if session is None:
        return None
    log = SetLog(session_id=session_id, **data.model_dump())
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def complete_session(
    db: AsyncSession, session_id: int, notes: str | None = None
) -> WorkoutSession | None:
    session = await db.get(WorkoutSession, session_id)
    if session is None:
        return None
    if notes is not None:
        session.notes = notes
    session.completed = True
    await db.commit()
    return await _load_session(db, session_id)


async def get_session(db: AsyncSession, session_id: int) -> WorkoutSession | None:
    return await _load_session(db, session_id)


async def list_sessions(
    db: AsyncSession, *, date_from: date | None = None, date_to: date | None = None
) -> list[WorkoutSession]:
    stmt = select(WorkoutSession).options(selectinload(WorkoutSession.set_logs))
    if date_from is not None:
        stmt = stmt.where(WorkoutSession.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(WorkoutSession.date <= date_to)
    stmt = stmt.order_by(WorkoutSession.date.desc(), WorkoutSession.id.desc())
    return list((await db.scalars(stmt)).all())
