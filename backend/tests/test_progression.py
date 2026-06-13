"""SPEC §7 progression & deload tests (mandatory gate)."""

from dataclasses import dataclass
from datetime import date

from app.services.progression import (
    WEIGHT_INCREMENT_KG,
    suggest_next_targets,
    week_number,
)


@dataclass
class PE:
    sets: int = 4
    target_reps_min: int = 6
    target_reps_max: int = 10


@dataclass
class Log:
    reps: int
    weight_kg: float | None = None


def session(reps: int, weight: float | None, n: int) -> list[Log]:
    return [Log(reps=reps, weight_kg=weight) for _ in range(n)]


def test_progression_increases_on_top_range_weighted() -> None:
    pe = PE()
    last = session(reps=10, weight=20.0, n=4)  # all sets at top with weight
    out = suggest_next_targets(pe, [last], week=1)
    assert out.suggested_weight_kg == 20.0 + WEIGHT_INCREMENT_KG
    assert (out.reps_min, out.reps_max) == (6, 10)


def test_progression_increases_reps_on_top_range_bodyweight() -> None:
    pe = PE(target_reps_min=12, target_reps_max=20)
    last = session(reps=20, weight=None, n=4)  # bodyweight, all sets at top
    out = suggest_next_targets(pe, [last], week=1)
    assert out.suggested_weight_kg is None
    assert out.reps_max == 22  # +2, under the +50% cap (30)


def test_deload_on_stall() -> None:
    pe = PE()
    # two consecutive sessions stuck at the bottom
    stalled = [session(reps=6, weight=20.0, n=4), session(reps=6, weight=20.0, n=4)]
    out = suggest_next_targets(pe, stalled, week=1)
    assert out.suggested_weight_kg == round(20.0 * 0.9, 1)


def test_deload_on_stall_bodyweight_drops_a_set() -> None:
    pe = PE(sets=4)
    stalled = [session(reps=6, weight=None, n=4), session(reps=6, weight=None, n=4)]
    out = suggest_next_targets(pe, stalled, week=1)
    assert out.sets == 3


def test_mesocycle_deload_week() -> None:
    pe = PE(sets=4)
    last = session(reps=10, weight=20.0, n=4)
    out = suggest_next_targets(pe, [last], week=4)
    assert out.sets == 3  # -1 set
    assert out.suggested_weight_kg == round(20.0 * 0.6, 1)


def test_no_history_returns_base() -> None:
    pe = PE()
    out = suggest_next_targets(pe, [], week=1)
    assert (out.sets, out.reps_min, out.reps_max) == (4, 6, 10)
    assert out.suggested_weight_kg is None


def test_week_number() -> None:
    start = date(2026, 1, 1)
    assert week_number(start, date(2026, 1, 1)) == 1
    assert week_number(start, date(2026, 1, 7)) == 1
    assert week_number(start, date(2026, 1, 8)) == 2
    assert week_number(start, date(2026, 1, 22)) == 4
