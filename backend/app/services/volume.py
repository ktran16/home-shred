"""Weekly training-volume aggregation (SPEC §9).

Weekly volume = Σ (reps × weight_kg) per primary muscle, grouped by ISO week.
For bodyweight sets (weight_kg null) we use a proxy:
    reps × (profile.weight_kg × muscle_factor),  muscle_factor defaults to 1.0.
This is a deliberate simplification (a bodyweight movement does not load a muscle
with the full body weight, but we have no per-exercise load data).
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Exercise, SetLog, WorkoutSession
from app.services.profile import get_profile

# rationale (SPEC §9): bodyweight proxy factor per muscle; default 1.0.
DEFAULT_MUSCLE_FACTOR = 1.0
MUSCLE_FACTORS: dict[str, float] = {}
# Fallback bodyweight if no profile is set yet (documented simplification).
FALLBACK_BODYWEIGHT_KG = 70.0


@dataclass
class VolumePoint:
    week: str  # ISO week, e.g. "2026-W24"
    muscle: str
    volume: float


def _iso_week(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


async def weekly_volume(
    db: AsyncSession, *, date_from: date | None = None, date_to: date | None = None
) -> list[VolumePoint]:
    profile = await get_profile(db)
    bodyweight = float(profile.weight_kg) if profile else FALLBACK_BODYWEIGHT_KG

    stmt = (
        select(SetLog, WorkoutSession.date, Exercise.primary_muscles)
        .join(WorkoutSession, SetLog.session_id == WorkoutSession.id)
        .join(Exercise, SetLog.exercise_id == Exercise.id)
        .where(WorkoutSession.completed.is_(True))
    )
    if date_from is not None:
        stmt = stmt.where(WorkoutSession.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(WorkoutSession.date <= date_to)

    totals: dict[tuple[str, str], float] = defaultdict(float)
    for log, sess_date, muscles in await db.execute(stmt):
        if log.weight_kg is not None:
            load = log.reps * float(log.weight_kg)
        else:
            factor = MUSCLE_FACTORS.get("", DEFAULT_MUSCLE_FACTOR)
            load = log.reps * (bodyweight * factor)
        week = _iso_week(sess_date)
        for muscle in muscles or []:
            totals[(week, muscle)] += load

    points = [
        VolumePoint(week=week, muscle=muscle, volume=round(volume, 1))
        for (week, muscle), volume in totals.items()
    ]
    points.sort(key=lambda p: (p.week, p.muscle))
    return points
