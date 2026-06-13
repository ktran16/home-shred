"""Rule-based double-progression & deload (SPEC §7).

`suggest_next_targets` is pure (operates on plain objects), so it is unit-testable
without a DB. The session service feeds it the plan exercise, the recent completed
sessions' logs for that exercise, and the current mesocycle week.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Protocol

# rationale (SPEC §7): tunable progression constants.
WEIGHT_INCREMENT_KG = 2.5  # adjustable dumbbell step
BODYWEIGHT_REP_INCREMENT = 2
BODYWEIGHT_REP_CAP_FACTOR = 1.5  # cap added reps at +50% of original max
DELOAD_WEIGHT_FACTOR = 0.9  # -10% on stall
MESOCYCLE_WEEKS = 4  # deload every 4th week
MESOCYCLE_DELOAD_LOAD_FACTOR = 0.6
STALL_SESSIONS = 2  # consecutive stalled sessions that trigger a deload
SETS_FLOOR = 2


class PlanExerciseLike(Protocol):
    sets: int
    target_reps_min: int
    target_reps_max: int


class SetLogLike(Protocol):
    reps: int
    weight_kg: float | None


@dataclass
class SuggestedTargets:
    sets: int
    reps_min: int
    reps_max: int
    suggested_weight_kg: float | None


def week_number(plan_created: date, on: date) -> int:
    """1-based mesocycle week (SPEC §7): floor(days since plan start / 7) + 1."""
    return max(0, (on - plan_created).days) // 7 + 1


def _session_weight(logs: list[SetLogLike]) -> float | None:
    weights = [float(log.weight_kg) for log in logs if log.weight_kg is not None]
    return max(weights) if weights else None


def _all_at_or_above(logs: list[SetLogLike], target: int, min_sets: int) -> bool:
    return len(logs) >= min_sets and all(log.reps >= target for log in logs)


def _all_at_or_below(logs: list[SetLogLike], target: int) -> bool:
    return bool(logs) and all(log.reps <= target for log in logs)


def suggest_next_targets(
    plan_exercise: PlanExerciseLike,
    recent_sessions: list[list[SetLogLike]],
    week: int = 1,
) -> SuggestedTargets:
    """Suggest defaults for the next session.

    `recent_sessions` holds this exercise's set logs grouped by completed session,
    most-recent first.
    """
    base = SuggestedTargets(
        sets=plan_exercise.sets,
        reps_min=plan_exercise.target_reps_min,
        reps_max=plan_exercise.target_reps_max,
        suggested_weight_kg=None,
    )
    last = recent_sessions[0] if recent_sessions else []
    last_weight = _session_weight(last)
    base.suggested_weight_kg = last_weight

    # Rule 3 — mesocycle deload week overrides everything (SPEC §7.3).
    if week % MESOCYCLE_WEEKS == 0:
        base.sets = max(SETS_FLOOR, plan_exercise.sets - 1)
        if last_weight is not None:
            base.suggested_weight_kg = round(last_weight * MESOCYCLE_DELOAD_LOAD_FACTOR, 1)
        return base

    if not last:
        return base

    # Rule 1 — hit the top of the range on ALL sets last time (SPEC §7.1).
    if _all_at_or_above(last, plan_exercise.target_reps_max, plan_exercise.sets):
        if last_weight is not None:
            base.suggested_weight_kg = round(last_weight + WEIGHT_INCREMENT_KG, 1)
            # reset reps to the bottom of the range (range itself unchanged)
        else:
            cap = math.floor(plan_exercise.target_reps_max * BODYWEIGHT_REP_CAP_FACTOR)
            base.reps_max = min(plan_exercise.target_reps_max + BODYWEIGHT_REP_INCREMENT, cap)
        return base

    # Rule 2 — stalled at/below the bottom for 2+ consecutive sessions (SPEC §7.2).
    stalled = recent_sessions[:STALL_SESSIONS]
    if len(stalled) >= STALL_SESSIONS and all(
        _all_at_or_below(s, plan_exercise.target_reps_min) for s in stalled
    ):
        if last_weight is not None:
            base.suggested_weight_kg = round(last_weight * DELOAD_WEIGHT_FACTOR, 1)
        else:
            base.sets = max(SETS_FLOOR, plan_exercise.sets - 1)
        return base

    return base
