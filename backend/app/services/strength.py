"""Personal records & estimated-1RM strength trend (SPEC §18).

Pure read/aggregation over completed sessions' set logs — no new tables, no
rule-engine change. Estimated 1RM uses Epley; bodyweight sets (null weight) have
no e1RM and instead track top-set reps as the strength signal.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import MovementPattern
from app.models import Exercise, SetLog, WorkoutSession


def epley_1rm(reps: int, weight_kg: float | None) -> float | None:
    """Estimated 1RM (Epley). None for bodyweight / zero load."""
    if weight_kg is None or weight_kg <= 0:
        return None
    return round(weight_kg * (1 + reps / 30), 1)


@dataclass
class StrengthPoint:
    date: date_type
    e1rm: float | None
    top_weight: float | None
    top_reps: int


@dataclass
class ExerciseStrength:
    exercise_id: int
    exercise_name: str
    pattern: MovementPattern | None
    weighted: bool
    best_e1rm: float | None
    best_weight: float | None
    best_reps: int
    latest_is_pr: bool
    points: list[StrengthPoint] = field(default_factory=list)


@dataclass
class _SessionAgg:
    """Best lifts within a single session for one exercise."""

    date: date_type
    session_id: int
    e1rm: float | None = None
    top_weight: float | None = None
    top_reps: int = 0

    def add(self, reps: int, weight_kg: float | None) -> None:
        self.top_reps = max(self.top_reps, reps)
        if weight_kg is not None and weight_kg > 0:
            self.top_weight = max(self.top_weight or 0.0, weight_kg)
            est = epley_1rm(reps, weight_kg)
            if est is not None:
                self.e1rm = max(self.e1rm or 0.0, est)


async def exercise_strength(db: AsyncSession) -> list[ExerciseStrength]:
    stmt = (
        select(
            SetLog.exercise_id,
            Exercise.name,
            Exercise.pattern,
            WorkoutSession.id,
            WorkoutSession.date,
            SetLog.reps,
            SetLog.weight_kg,
        )
        .join(WorkoutSession, SetLog.session_id == WorkoutSession.id)
        .join(Exercise, SetLog.exercise_id == Exercise.id)
        .where(WorkoutSession.completed.is_(True))
        .order_by(WorkoutSession.date, WorkoutSession.id)
    )

    # exercise_id -> session_id -> aggregate (preserves chronological insertion order)
    grouped: dict[int, dict[int, _SessionAgg]] = defaultdict(dict)
    meta: dict[int, tuple[str, MovementPattern | None]] = {}
    for ex_id, name, pattern, sess_id, sess_date, reps, weight in await db.execute(stmt):
        meta[ex_id] = (name, pattern)
        sessions = grouped[ex_id]
        agg = sessions.get(sess_id)
        if agg is None:
            agg = _SessionAgg(date=sess_date, session_id=sess_id)
            sessions[sess_id] = agg
        agg.add(reps, float(weight) if weight is not None else None)

    results: list[ExerciseStrength] = []
    for ex_id, sessions in grouped.items():
        aggs = list(sessions.values())  # already chronological
        points = [
            StrengthPoint(
                date=a.date, e1rm=a.e1rm, top_weight=a.top_weight, top_reps=a.top_reps
            )
            for a in aggs
        ]
        e1rms = [p.e1rm for p in points if p.e1rm is not None]
        weights = [p.top_weight for p in points if p.top_weight is not None]
        weighted = bool(e1rms)
        best_e1rm = max(e1rms) if e1rms else None
        best_weight = max(weights) if weights else None
        best_reps = max((p.top_reps for p in points), default=0)

        last = points[-1]
        if weighted:
            prior_best = max((p.e1rm for p in points[:-1] if p.e1rm is not None), default=None)
            latest_is_pr = last.e1rm is not None and (
                prior_best is None or last.e1rm > prior_best
            )
        else:
            prior_best_reps = max((p.top_reps for p in points[:-1]), default=0)
            latest_is_pr = len(points) > 0 and last.top_reps > prior_best_reps

        name, pattern = meta[ex_id]
        results.append(
            ExerciseStrength(
                exercise_id=ex_id,
                exercise_name=name,
                pattern=pattern,
                weighted=weighted,
                best_e1rm=best_e1rm,
                best_weight=best_weight,
                best_reps=best_reps,
                latest_is_pr=latest_is_pr,
                points=points,
            )
        )

    # most-recently-trained first
    results.sort(key=lambda r: r.points[-1].date, reverse=True)
    return results
