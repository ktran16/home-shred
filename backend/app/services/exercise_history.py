"""Per-exercise training history for the workout runner.

Returns the most recent *completed* sessions in which a given exercise was logged,
most-recent-first, with that exercise's set logs. Unlike progression (which reads
history for one plan_day), this is exercise-scoped so it follows substitutions and
shows the same movement wherever it appears in a plan.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import SetLog, WorkoutSession

DEFAULT_SESSIONS = 3  # how many recent sessions to surface in the runner


async def recent_history(
    db: AsyncSession, exercise_id: int, *, sessions: int = DEFAULT_SESSIONS
) -> list[WorkoutSession]:
    """Completed sessions containing `exercise_id`, newest first, limited to `sessions`."""
    session_ids = (
        select(SetLog.session_id)
        .join(WorkoutSession, WorkoutSession.id == SetLog.session_id)
        .where(SetLog.exercise_id == exercise_id, WorkoutSession.completed.is_(True))
        .group_by(SetLog.session_id)
    )
    stmt = (
        select(WorkoutSession)
        .where(WorkoutSession.id.in_(session_ids))
        .order_by(WorkoutSession.date.desc(), WorkoutSession.id.desc())
        .options(selectinload(WorkoutSession.set_logs))
        .limit(sessions)
    )
    return list((await db.scalars(stmt)).all())
