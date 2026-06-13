"""Phase 1 data-layer tests: curation + seed honour the hard equipment constraint."""

from collections import Counter

from app.enums import Equipment, MovementPattern
from app.seed.seed_exercises import build_rows

ALLOWED = {Equipment.BODYWEIGHT, Equipment.DUMBBELL, Equipment.PULL_UP_BAR}


def test_seed_only_allowed_equipment() -> None:
    rows = build_rows()
    assert rows, "seed produced no rows"
    for row in rows:
        assert row["equipment"] in ALLOWED, row


def test_seed_pattern_coverage() -> None:
    counts = Counter(r["pattern"] for r in build_rows())
    for pattern in MovementPattern:
        if pattern is MovementPattern.CONDITIONING:
            continue
        assert counts.get(pattern, 0) >= 3, f"{pattern} has < 3 exercises"
    assert counts.get(MovementPattern.CONDITIONING, 0) >= 3


def test_seed_category_matches_pattern() -> None:
    for row in build_rows():
        assert row["category"] is not None
        if row["pattern"] in {MovementPattern.SQUAT, MovementPattern.HINGE}:
            assert row["category"] == "legs"
