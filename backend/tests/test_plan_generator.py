"""SPEC §6.9 hard tests for the plan generator. Equipment-constraint failure = build not done."""

from types import SimpleNamespace

import pytest

from app.enums import Equipment, Goal, Level
from app.seed.seed_exercises import build_rows
from app.services.plan_generator import (
    MAX_SETS_PER_EXERCISE,
    PRESCRIPTION,
    WEEKLY_SET_TARGETS,
    age_adjustment,
    coverage_report,
    generate_plan,
    scaled_set_targets,
    weekly_set_coverage,
)

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
            primary_muscles=row["primary_muscles"],
            secondary_muscles=row["secondary_muscles"],
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


# --- R1: weekly set-volume targeting (SPEC §16) ---


def test_volume_targets_met_or_capped() -> None:
    """Every targeted muscle reaches its weekly set minimum (or every exercise that
    trains it is at the per-exercise cap, i.e. we did all we could)."""
    exercises = make_exercises()
    ex_by_id = {e.id: e for e in exercises}
    for days in DAYS:
        for level in LEVELS:
            draft = generate_plan(Goal.SHRED, days, level, ALLOWED, exercises)
            coverage = weekly_set_coverage(draft, ex_by_id)
            for muscle, target in WEEKLY_SET_TARGETS.items():
                trains = [
                    pe
                    for d in draft.days
                    for pe in d.exercises
                    if not pe.is_conditioning
                    and (
                        muscle in ex_by_id[pe.exercise_id].primary_muscles
                        or muscle in ex_by_id[pe.exercise_id].secondary_muscles
                    )
                ]
                if not trains:
                    continue  # muscle not trainable by this split's patterns
                capped = all(pe.sets >= MAX_SETS_PER_EXERCISE for pe in trains)
                got = coverage.get(muscle, 0)
                assert got >= target or capped, f"{muscle} {got}/{target} on {days}d/{level}"


def test_volume_targeting_respects_set_cap() -> None:
    exercises = make_exercises()
    draft = generate_plan(Goal.SHRED, 4, Level.INTERMEDIATE, ALLOWED, exercises)
    for day in draft.days:
        for pe in day.exercises:
            assert pe.sets <= MAX_SETS_PER_EXERCISE


def test_coverage_report_shape() -> None:
    exercises = make_exercises()
    draft = generate_plan(Goal.SHRED, 5, Level.INTERMEDIATE, ALLOWED, exercises)
    report = coverage_report(draft, {e.id: e for e in exercises})
    assert {c.muscle for c in report} == set(WEEKLY_SET_TARGETS)
    for c in report:
        assert c.met == (c.sets >= c.target)


# --- R7: age-based recovery / volume adjustment (SPEC §16) ---


def test_age_adjustment_bands() -> None:
    assert age_adjustment(None) == (1.0, 1.0)
    assert age_adjustment(30) == (1.0, 1.0)
    assert age_adjustment(45) == (1.10, 0.90)
    assert age_adjustment(60) == (1.20, 0.80)


def test_scaled_targets_lower_for_older() -> None:
    young = scaled_set_targets(30)
    senior = scaled_set_targets(60)
    assert young == WEEKLY_SET_TARGETS
    assert all(senior[m] <= young[m] for m in WEEKLY_SET_TARGETS)
    assert any(senior[m] < young[m] for m in WEEKLY_SET_TARGETS)


def test_age_increases_rest_periods() -> None:
    exercises = make_exercises()
    young = generate_plan(Goal.SHRED, 4, Level.INTERMEDIATE, ALLOWED, exercises, age=30)
    senior = generate_plan(Goal.SHRED, 4, Level.INTERMEDIATE, ALLOWED, exercises, age=60)

    def rest_of_first(draft) -> int:
        return draft.days[0].exercises[0].rest_seconds

    assert rest_of_first(senior) > rest_of_first(young)


def test_age_reduces_total_volume() -> None:
    exercises = make_exercises()

    def total_sets(draft) -> int:
        return sum(pe.sets for d in draft.days for pe in d.exercises if not pe.is_conditioning)

    young = generate_plan(Goal.SHRED, 4, Level.INTERMEDIATE, ALLOWED, exercises, age=30)
    senior = generate_plan(Goal.SHRED, 4, Level.INTERMEDIATE, ALLOWED, exercises, age=60)
    assert total_sets(senior) <= total_sets(young)


# --- R2 periodisation + R5 rotation (SPEC §16) ---


def _strength_ids(draft) -> list[int]:
    return [pe.exercise_id for d in draft.days for pe in d.exercises if not pe.is_conditioning]


def _total_strength_sets(draft) -> int:
    return sum(pe.sets for d in draft.days for pe in d.exercises if not pe.is_conditioning)


def test_periodisation_ramps_then_deloads() -> None:
    ex = make_exercises()
    vols = {
        w: _total_strength_sets(
            generate_plan(Goal.SHRED, 4, Level.INTERMEDIATE, ALLOWED, ex, week=w)
        )
        for w in (1, 2, 3, 4)
    }
    assert vols[3] >= vols[2] >= vols[1]  # accumulation
    assert vols[4] < vols[1]  # deload week


def test_rotation_changes_exercises_across_weeks() -> None:
    ex = make_exercises()
    w1 = generate_plan(Goal.SHRED, 4, Level.INTERMEDIATE, ALLOWED, ex, week=1)
    w2 = generate_plan(Goal.SHRED, 4, Level.INTERMEDIATE, ALLOWED, ex, week=2)
    assert _strength_ids(w1) != _strength_ids(w2)  # exercises rotate


def test_each_week_reproducible() -> None:
    ex = make_exercises()
    for w in (1, 2, 3, 4):
        a = generate_plan(Goal.SHRED, 4, Level.INTERMEDIATE, ALLOWED, ex, week=w)
        b = generate_plan(Goal.SHRED, 4, Level.INTERMEDIATE, ALLOWED, ex, week=w)
        assert a == b


def test_mesocycle_position_wraps() -> None:
    from app.services.plan_generator import mesocycle_position

    assert [mesocycle_position(w) for w in (1, 2, 3, 4, 5, 8)] == [1, 2, 3, 4, 1, 4]
