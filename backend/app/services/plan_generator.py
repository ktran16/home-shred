"""Rule-based plan generator (SPEC §6) — the core module.

All tunable rules live in module-level config dicts so they are data-driven, not
buried in code. The generator is pure: it takes the candidate exercises as input
(`ExerciseLike`), so it is unit-testable without a DB or HTTP. The API layer loads
exercises from the DB and persists the returned `PlanDraft`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Protocol

from app.enums import Equipment, Focus, Goal, Level, MovementPattern

P = MovementPattern

# rationale (SPEC §6.2): split templates by days/week.
SPLITS: dict[int, list[Focus]] = {
    3: [Focus.FULL_BODY, Focus.FULL_BODY, Focus.FULL_BODY],
    4: [Focus.UPPER, Focus.LOWER, Focus.UPPER, Focus.LOWER],
    5: [Focus.PUSH, Focus.PULL, Focus.LEGS, Focus.UPPER, Focus.CONDITIONING],
}

_SPLIT_LABELS = {3: "Full Body", 4: "Upper/Lower", 5: "PPL + Upper + Conditioning"}

# A slot is a movement pattern (or alternatives rotated per day) plus a role that
# drives selection preference and prescription.
Role = str  # "compound" | "accessory" | "core" | "conditioning"


@dataclass(frozen=True)
class Slot:
    patterns: tuple[MovementPattern, ...]  # >1 => rotate by day_index
    role: Role


def _c(pattern: MovementPattern) -> Slot:
    return Slot((pattern,), "compound")


def _a(pattern: MovementPattern) -> Slot:
    return Slot((pattern,), "accessory")


_CORE = Slot((P.CORE,), "core")
_COND = Slot((P.CONDITIONING,), "conditioning")

# rationale (SPEC §6.3): pattern slots per focus. Compounds first, then accessories,
# then core, then optional conditioning (added later per §6.5). Tuples = alternate
# per day via day_index (SPEC §6.3 "alternate per day").
FOCUS_PATTERNS: dict[Focus, list[Slot]] = {
    Focus.FULL_BODY: [
        Slot((P.SQUAT, P.HINGE), "compound"),
        Slot((P.HORIZONTAL_PUSH, P.VERTICAL_PUSH), "compound"),
        Slot((P.VERTICAL_PULL, P.HORIZONTAL_PULL), "compound"),
        _CORE,
    ],
    Focus.UPPER: [
        _c(P.HORIZONTAL_PUSH),
        _c(P.VERTICAL_PULL),
        _a(P.VERTICAL_PUSH),
        _a(P.HORIZONTAL_PULL),
        _CORE,
    ],
    Focus.LOWER: [_c(P.SQUAT), _c(P.HINGE), _a(P.SQUAT), _CORE],
    Focus.LEGS: [_c(P.SQUAT), _c(P.HINGE), _a(P.SQUAT), _CORE],
    Focus.PUSH: [_c(P.HORIZONTAL_PUSH), _c(P.VERTICAL_PUSH), _a(P.HORIZONTAL_PUSH), _CORE],
    Focus.PULL: [_c(P.VERTICAL_PULL), _c(P.HORIZONTAL_PULL), _a(P.VERTICAL_PULL), _CORE],
    Focus.CONDITIONING: [_COND, _COND, _COND],
}

# rationale (SPEC §6.4): shred = hypertrophy + metabolic stress in a deficit →
# moderate-high reps, short rests. (sets, reps_min, reps_max, rest_seconds).
PRESCRIPTION: dict[Role, dict[str, object]] = {
    "compound": {"sets": 4, "reps": (6, 10), "rest": 75},
    "accessory": {"sets": 3, "reps": (10, 15), "rest": 60},
    "core": {"sets": 3, "reps": (12, 20), "rest": 45},
    # reps=0 → time-based; sets = rounds for the FE interval timer (SPEC §6.7).
    "conditioning": {"sets": 3, "reps": (0, 0), "rest": 45},
}

# rationale (SPEC §6.4): applied to sets, floor 2.
LEVEL_SET_MODIFIER: dict[Level, int] = {
    Level.BEGINNER: -1,
    Level.INTERMEDIATE: 0,
    Level.ADVANCED: +1,
}

# beginner < intermediate < advanced; a user may use exercises at or below level.
_LEVEL_RANK: dict[Level, int] = {Level.BEGINNER: 0, Level.INTERMEDIATE: 1, Level.ADVANCED: 2}

# rationale (SPEC §6.6 step 4): stable placeholder so regeneration is reproducible.
_PLAN_SEED_PLACEHOLDER = 0


class ExerciseLike(Protocol):
    id: int
    pattern: MovementPattern | None
    equipment: Equipment
    level: Level | None
    is_compound: bool


@dataclass
class PlanExerciseDraft:
    exercise_id: int
    order_index: int
    sets: int
    target_reps_min: int
    target_reps_max: int
    rest_seconds: int
    is_conditioning: bool


@dataclass
class PlanDayDraft:
    day_index: int
    focus: Focus
    exercises: list[PlanExerciseDraft] = field(default_factory=list)


@dataclass
class PlanDraft:
    name: str
    goal: Goal
    days_per_week: int
    experience_level: Level
    days: list[PlanDayDraft] = field(default_factory=list)


def _level_allows(user: Level, ex_level: Level | None) -> bool:
    if ex_level is None:
        return True
    return _LEVEL_RANK[ex_level] <= _LEVEL_RANK[user]


def _prescription_for(role: Role, level: Level) -> dict[str, int]:
    spec = PRESCRIPTION[role]
    reps: tuple[int, int] = spec["reps"]  # type: ignore[assignment]
    sets = max(2, int(spec["sets"]) + LEVEL_SET_MODIFIER[level])  # floor 2
    return {
        "sets": sets,
        "reps_min": reps[0],
        "reps_max": reps[1],
        "rest_seconds": int(spec["rest"]),
    }


def _select(
    candidates: list[ExerciseLike],
    role: Role,
    rng: random.Random,
    used_in_plan: set[int],
    used_in_day: set[int],
) -> ExerciseLike | None:
    """Pick one exercise honouring no-duplicate rules and compound preference (§6.6)."""
    if not candidates:
        return None
    # SPEC §6.6.3: avoid plan-wide duplicates; if exhausted, only avoid intraday.
    pool = [e for e in candidates if e.id not in used_in_plan]
    if not pool:
        pool = [e for e in candidates if e.id not in used_in_day]
    if not pool:
        pool = list(candidates)

    # SPEC §6.6.2: compound slots prefer compounds; accessory slots prefer accessories.
    if role == "compound":
        preferred = [e for e in pool if e.is_compound] or pool
    elif role == "accessory":
        preferred = [e for e in pool if not e.is_compound] or pool
    else:
        preferred = pool

    preferred = sorted(preferred, key=lambda e: e.id)  # deterministic ordering
    return rng.choice(preferred)


def generate_plan(
    goal: Goal,
    days_per_week: int,
    level: Level,
    available_equipment: set[Equipment],
    exercises: list[ExerciseLike],
) -> PlanDraft:
    if days_per_week not in SPLITS:
        raise ValueError(f"unsupported days_per_week: {days_per_week} (expected 3, 4 or 5)")

    focuses = SPLITS[days_per_week]
    cond_days = _conditioning_days(focuses)

    # index exercises by pattern, pre-filtered to allowed equipment (SPEC §1 hard rule).
    by_pattern: dict[MovementPattern, list[ExerciseLike]] = {p: [] for p in MovementPattern}
    for ex in exercises:
        if ex.pattern is not None and ex.equipment in available_equipment:
            by_pattern[ex.pattern].append(ex)

    name = f"Shred — {days_per_week}-day {_SPLIT_LABELS[days_per_week]}"
    draft = PlanDraft(name=name, goal=goal, days_per_week=days_per_week, experience_level=level)

    used_in_plan: set[int] = set()
    for day_index, focus in enumerate(focuses, start=1):
        slots = list(FOCUS_PATTERNS[focus])
        if day_index in cond_days:
            slots.append(_COND)

        day = PlanDayDraft(day_index=day_index, focus=focus)
        used_in_day: set[int] = set()
        order = 0
        for slot_index, slot in enumerate(slots):
            pattern = slot.patterns[(day_index - 1) % len(slot.patterns)]
            candidates = [c for c in by_pattern[pattern] if _level_allows(level, c.level)]
            seed = hash((_PLAN_SEED_PLACEHOLDER, day_index, slot_index))
            rng = random.Random(seed)
            chosen = _select(candidates, slot.role, rng, used_in_plan, used_in_day)
            if chosen is None:
                continue  # no exercise available for this pattern at this level
            used_in_plan.add(chosen.id)
            used_in_day.add(chosen.id)
            rx = _prescription_for(slot.role, level)
            day.exercises.append(
                PlanExerciseDraft(
                    exercise_id=chosen.id,
                    order_index=order,
                    sets=rx["sets"],
                    target_reps_min=rx["reps_min"],
                    target_reps_max=rx["reps_max"],
                    rest_seconds=rx["rest_seconds"],
                    is_conditioning=slot.role == "conditioning",
                )
            )
            order += 1
        draft.days.append(day)

    return draft


def _conditioning_days(focuses: list[Focus]) -> set[int]:
    """Extra conditioning blocks per SPEC §6.5 (1-based day indices)."""
    n = len(focuses)
    if n == 3:
        return {2, 3}  # add to the 2nd and 3rd full-body days
    if n == 4:
        return {i + 1 for i, f in enumerate(focuses) if f == Focus.LOWER}  # after lower days
    if n == 5:
        # day 5 is already a conditioning focus; add a block to Push and Pull days.
        return {i + 1 for i, f in enumerate(focuses) if f in (Focus.PUSH, Focus.PULL)}
    return set()
