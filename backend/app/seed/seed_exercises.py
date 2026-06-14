"""Ingest free-exercise-db into our `exercises` table (SPEC §2, Phase 1).

- Keeps only exercises present in the curation map (which already enforces the
  allowed-equipment hard constraint, SPEC §1).
- Assigns curated equipment / pattern / category / is_compound.
- Idempotent: upserts by `slug`, safe to re-run (SPEC §14.7).
- Asserts each non-conditioning pattern has >= 3 exercises, else logs a warning.

Run: `uv run python -m app.seed.seed_exercises`
"""

import asyncio
import json
import logging
from collections import Counter
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.data.exercise_pools import CURATION, PATTERN_CATEGORY, load_factor
from app.db import async_session
from app.enums import Level, MovementPattern
from app.models import Exercise

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("seed_exercises")

DATA_FILE = Path(__file__).parent / "free-exercise-db.json"

# free-exercise-db uses "expert" where we use "advanced".
_LEVEL_MAP = {
    "beginner": Level.BEGINNER,
    "intermediate": Level.INTERMEDIATE,
    "expert": Level.ADVANCED,
}


def _to_level(raw: str | None) -> Level:
    return _LEVEL_MAP.get(raw or "", Level.INTERMEDIATE)


def build_rows() -> list[dict]:
    """Build exercise rows from the dataset filtered/annotated by the curation map."""
    raw = json.loads(DATA_FILE.read_text())
    by_id = {x["id"]: x for x in raw}
    rows: list[dict] = []
    for slug, cur in CURATION.items():
        src = by_id.get(slug)
        if src is None:
            log.warning("curated id %r not found in dataset; skipping", slug)
            continue
        rows.append(
            {
                "name": src["name"],
                "slug": slug,
                "equipment": cur.equipment,
                "pattern": cur.pattern,
                "category": PATTERN_CATEGORY[cur.pattern],
                "primary_muscles": src.get("primaryMuscles") or [],
                "secondary_muscles": src.get("secondaryMuscles") or [],
                "level": _to_level(src.get("level")),
                "is_compound": cur.is_compound,
                "bodyweight_load_factor": load_factor(slug),
                "instructions": src.get("instructions") or [],
            }
        )
    return rows


def _check_pattern_coverage(rows: list[dict]) -> None:
    counts = Counter(r["pattern"] for r in rows)
    for pattern in MovementPattern:
        if pattern is MovementPattern.CONDITIONING:
            continue
        n = counts.get(pattern, 0)
        if n < 3:
            log.warning("pattern %s has only %d exercises (< 3)", pattern, n)
        else:
            log.info("pattern %s: %d exercises", pattern, n)
    log.info("conditioning: %d exercises", counts.get(MovementPattern.CONDITIONING, 0))


async def seed() -> int:
    rows = build_rows()
    _check_pattern_coverage(rows)
    async with async_session() as session:
        for row in rows:
            stmt = (
                pg_insert(Exercise)
                .values(**row)
                .on_conflict_do_update(
                    index_elements=[Exercise.slug],
                    set_={k: row[k] for k in row if k != "slug"},
                )
            )
            await session.execute(stmt)
        await session.commit()
        total = await session.scalar(select(func.count()).select_from(Exercise))
    log.info("seeded %d exercises", len(rows))
    return total or len(rows)


if __name__ == "__main__":
    asyncio.run(seed())
