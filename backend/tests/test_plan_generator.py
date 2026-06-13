"""SPEC §6.9 hard tests for the plan generator. Equipment-constraint failure = build not done."""

from types import SimpleNamespace

import pytest

from app.enums import Equipment, Goal, Level
from app.seed.seed_exercises import build_rows
from app.services.plan_generator import PRESCRIPTION, generate_plan

ALLOWED = {Equipment.BODYWEIGHT, Equipment.DUMBBELL, Equipment.PULL_UP_BAR}
LEVELS = [Level.BEGINNER, Level.INTERMEDIATE, Level.ADVANCED]
DAYS = [3, 4, 5]


def make_exercises() -> list[SimpleNamespace]:
    """ExerciseLike objects from the seed data, with synthetic ids."""
    return [
        SimpleNamespace(
            id=i + 1,
            pattern=row["pattern"],
            equipment=row["equipment"],
            level=row["level"],
            is_compound=row["is_compound"],
        )
        for i, row in enumerate(build_rows())
    ]


def _gen(days: int, level: Level):
    return generate_plan(Goal.SHRED, days, level, ALLOWED, make_exercises())


def test_no_disallowed_equipment() -> None:
    exercises = make_exercises()
    equip_by_id = {e.id: e.equipment for e in exercises}
    for days in DAYS:
        for level in LEVELS:
            draft = generate_plan(Goal.SHRED, days, level, ALLOWED, exercises)
            for day in draft.days:
                for pe in day.exercises:
                    assert equip_by_id[pe.exercise_id] in ALLOWED


def test_split_day_count() -> None:
    for days in DAYS:
        draft = _gen(days, Level.INTERMEDIATE)
        assert len(draft.days) == days
        assert [d.day_index for d in draft.days] == list(range(1, days + 1))


def test_prescription_ranges() -> None:
    valid_reps = {tuple(PRESCRIPTION[r]["reps"]) for r in PRESCRIPTION}  # type: ignore[misc]
    for days in DAYS:
        for level in LEVELS:
            draft = _gen(days, level)
            for day in draft.days:
                for pe in day.exercises:
                    assert pe.sets >= 2  # floor 2 (SPEC §6.4)
                    if pe.is_conditioning:
                        assert (pe.target_reps_min, pe.target_reps_max) == (0, 0)
                    else:
                        assert (pe.target_reps_min, pe.target_reps_max) in valid_reps
                        assert pe.target_reps_min > 0


def test_reproducible() -> None:
    for days in DAYS:
        a = _gen(days, Level.INTERMEDIATE)
        b = _gen(days, Level.INTERMEDIATE)
        assert a == b


def test_no_intraday_duplicates() -> None:
    for days in DAYS:
        for level in LEVELS:
            draft = _gen(days, level)
            for day in draft.days:
                ids = [pe.exercise_id for pe in day.exercises]
                assert len(ids) == len(set(ids)), f"day {day.day_index} has dupes"


@pytest.mark.parametrize("days", DAYS)
def test_each_day_has_exercises(days: int) -> None:
    draft = _gen(days, Level.INTERMEDIATE)
    for day in draft.days:
        assert day.exercises, f"day {day.day_index} empty"
