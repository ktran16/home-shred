"""Per-exercise load / readiness forecast (SPEC §17.3 A2).

A deliberately small, dependency-free forecaster: a least-squares trend over each
exercise's per-session strength signal (e1RM for weighted lifts, top-set reps for
bodyweight) projected one session ahead, tempered by recent RPE. No scikit-learn /
LightGBM yet — a solo user is data-starved (SPEC §17.3 A2), and this baseline reuses
the same least-squares maths as the adaptive-TDEE trend (§17.3 A1). The service layer
(`exercise_strength`) is reused so there is one source of truth for the e1RM series;
swapping in a trained regressor later means replacing `forecast_next` only.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SetLog, WorkoutSession
from app.services.nutrition import linear_slope
from app.services.strength import exercise_strength

# rationale (SPEC §17.3 A2): need a few sessions before a trend means anything;
# below this we report "insufficient" rather than forecast noise.
MIN_SESSIONS_FOR_PREDICTION = 4
# confidence ramps to 1.0 once this many sessions of history exist.
CONFIDENCE_FULL_SESSIONS = 8
# average RPE at or above this on the latest session = hold, don't push load.
HOLD_RPE_THRESHOLD = 9.0
# only the most recent sessions feed the "recent RPE" signal.
RPE_RECENT_SESSIONS = 2


@dataclass
class LoadPrediction:
    exercise_id: int
    exercise_name: str
    weighted: bool
    sessions: int
    current: float | None  # latest e1RM (weighted) or latest top-set reps
    predicted_next: float | None  # one-session-ahead forecast
    trend_per_session: float | None  # change per session (same unit as `current`)
    avg_recent_rpe: float | None
    readiness: str  # "progress" | "hold" | "insufficient"
    confidence: float  # 0..1 heuristic


def forecast_next(values: list[float]) -> tuple[float | None, float | None]:
    """One-step-ahead least-squares forecast over evenly spaced values.

    Returns (predicted_next, slope_per_step) rounded to 0.1, or (None, None) when
    there are fewer than two points. Pure / unit-testable.
    """
    n = len(values)
    if n < 2:
        return None, None
    xs = [float(i) for i in range(n)]
    slope = linear_slope(xs, values)
    mean_x = (n - 1) / 2
    mean_y = sum(values) / n
    predicted = mean_y + slope * (n - mean_x)  # value at the next index, x = n
    return round(predicted, 1), round(slope, 2)


def readiness_from(slope: float | None, avg_recent_rpe: float | None) -> str:
    """Translate trend + recent RPE into a coaching verdict (SPEC §16 R3 philosophy)."""
    if slope is None:
        return "insufficient"
    if avg_recent_rpe is not None and avg_recent_rpe >= HOLD_RPE_THRESHOLD:
        return "hold"
    if slope <= 0:
        return "hold"
    return "progress"


def confidence_for(sessions: int) -> float:
    """Heuristic 0..1 confidence: more history → more trust. Capped at 1.0."""
    if sessions < MIN_SESSIONS_FOR_PREDICTION:
        return 0.0
    return round(min(1.0, (sessions - 1) / (CONFIDENCE_FULL_SESSIONS - 1)), 2)


async def _recent_avg_rpe(db: AsyncSession) -> dict[int, float]:
    """Average RPE over each exercise's most recent completed sessions (RPE_RECENT_SESSIONS)."""
    stmt = (
        select(SetLog.exercise_id, WorkoutSession.id, WorkoutSession.date, SetLog.rpe)
        .join(WorkoutSession, SetLog.session_id == WorkoutSession.id)
        .where(WorkoutSession.completed.is_(True), SetLog.rpe.is_not(None))
        .order_by(WorkoutSession.date.desc(), WorkoutSession.id.desc())
    )
    # exercise_id -> {session_id: [rpe, ...]} keeping newest sessions first.
    by_ex: dict[int, dict[int, list[float]]] = {}
    for ex_id, sess_id, _date, rpe in await db.execute(stmt):
        sessions = by_ex.setdefault(ex_id, {})
        if sess_id not in sessions and len(sessions) >= RPE_RECENT_SESSIONS:
            continue
        sessions.setdefault(sess_id, []).append(float(rpe))

    out: dict[int, float] = {}
    for ex_id, sessions in by_ex.items():
        rpes = [r for vals in sessions.values() for r in vals]
        if rpes:
            out[ex_id] = round(sum(rpes) / len(rpes), 1)
    return out


async def exercise_predictions(db: AsyncSession) -> list[LoadPrediction]:
    """Forecast next-session load / readiness per exercise (SPEC §17.3 A2).

    Built on top of `exercise_strength` so the e1RM series has a single source of
    truth; ordering (most-recently-trained first) is inherited from it.
    """
    strengths = await exercise_strength(db)
    rpe_map = await _recent_avg_rpe(db)

    out: list[LoadPrediction] = []
    for s in strengths:
        if s.weighted:
            values = [p.e1rm for p in s.points if p.e1rm is not None]
        else:
            values = [float(p.top_reps) for p in s.points]
        sessions = len(values)
        current = values[-1] if values else None
        avg_rpe = rpe_map.get(s.exercise_id)

        if sessions < MIN_SESSIONS_FOR_PREDICTION:
            out.append(
                LoadPrediction(
                    exercise_id=s.exercise_id,
                    exercise_name=s.exercise_name,
                    weighted=s.weighted,
                    sessions=sessions,
                    current=current,
                    predicted_next=None,
                    trend_per_session=None,
                    avg_recent_rpe=avg_rpe,
                    readiness="insufficient",
                    confidence=0.0,
                )
            )
            continue

        predicted, slope = forecast_next(values)
        out.append(
            LoadPrediction(
                exercise_id=s.exercise_id,
                exercise_name=s.exercise_name,
                weighted=s.weighted,
                sessions=sessions,
                current=current,
                predicted_next=predicted,
                trend_per_session=slope,
                avg_recent_rpe=avg_rpe,
                readiness=readiness_from(slope, avg_rpe),
                confidence=confidence_for(sessions),
            )
        )
    return out
