"""Weekly training-volume aggregation (SPEC §9).

Weekly volume = Σ (reps × weight_kg) per primary muscle, grouped by ISO week.
For bodyweight sets (weight_kg null) we use a proxy:
    reps × (profile.weight_kg × exercise.bodyweight_load_factor),
where the per-exercise load factor (SPEC §16 R4) estimates the fraction of bodyweight
borne by the prime movers (e.g. push-up ≈ 0.64, pull-up ≈ 1.0). Still an
approximation, but far better than counting full bodyweight on every movement.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Exercise, SetLog, WorkoutSession
from app.services.profile import get_profile

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
        select(
            SetLog,
            WorkoutSession.date,
            Exercise.primary_muscles,
            Exercise.bodyweight_load_factor,
        )
        .join(WorkoutSession, SetLog.session_id == WorkoutSession.id)
        .join(Exercise, SetLog.exercise_id == Exercise.id)
        .where(WorkoutSession.completed.is_(True))
    )
    if date_from is not None:
        stmt = stmt.where(WorkoutSession.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(WorkoutSession.date <= date_to)

    totals: dict[tuple[str, str], float] = defaultdict(float)
    for log, sess_date, muscles, load_factor in await db.execute(stmt):
        if log.weight_kg is not None:
            load = log.reps * float(log.weight_kg)
        else:
            # bodyweight proxy scaled by the per-exercise load factor (SPEC §16 R4)
            load = log.reps * (bodyweight * load_factor)
        week = _iso_week(sess_date)
        for muscle in muscles or []:
            totals[(week, muscle)] += load

    points = [
        VolumePoint(week=week, muscle=muscle, volume=round(volume, 1))
        for (week, muscle), volume in totals.items()
    ]
    points.sort(key=lambda p: (p.week, p.muscle))
    return points
