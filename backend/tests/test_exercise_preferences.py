"""Tests for exercise preferences + profile limitations (SPEC §16 follow-up).

Covers the preferences service (favorite/avoid persistence), the preference REST
endpoints, profile limitation upsert/dedup, and the way both feed plan generation:
avoided moves are hard-excluded, favorites get selection priority, and limitations
filter blocked movement patterns out of the candidate pool.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import ExercisePreferenceStatus, MovementPattern
from app.models import Exercise
from app.seed.seed_exercises import build_rows
from app.services import exercise_preferences as pref_svc
from app.services.plans import _candidate_exercises

PROFILE = {
    "sex": "male",
    "age": 30,
    "height_cm": 180.0,
    "weight_kg": 80.0,
    "activity_level": "moderate",
    "experience_level": "intermediate",
}


@pytest.fixture
async def seeded(db: AsyncSession) -> None:
    for row in build_rows():
        db.add(Exercise(**row))
    await db.commit()


async def _first_exercise_with_pattern(db: AsyncSession, pattern: MovementPattern) -> Exercise:
    row = (await db.scalars(select(Exercise).where(Exercise.pattern == pattern))).first()
    assert row is not None, f"no seeded exercise with pattern {pattern}"
    return row


# --- service ---------------------------------------------------------------


async def test_set_update_clear_preference(db: AsyncSession, seeded: None) -> None:
    ex = await _first_exercise_with_pattern(db, MovementPattern.HORIZONTAL_PUSH)

    pref = await pref_svc.set_preference(db, ex.id, ExercisePreferenceStatus.FAVORITE)
    assert pref.status is ExercisePreferenceStatus.FAVORITE
    assert await pref_svc.preference_map(db, [ex.id]) == {ex.id: ExercisePreferenceStatus.FAVORITE}
    assert await pref_svc.avoided_exercise_ids(db) == set()

    # upsert flips the same row to avoid (primary key on exercise_id)
    await pref_svc.set_preference(db, ex.id, ExercisePreferenceStatus.AVOID)
    assert await pref_svc.avoided_exercise_ids(db) == {ex.id}

    await pref_svc.clear_preference(db, ex.id)
    assert await pref_svc.preference_map(db, [ex.id]) == {}
    assert await pref_svc.avoided_exercise_ids(db) == set()


async def test_preference_map_empty_input(db: AsyncSession) -> None:
    assert await pref_svc.preference_map(db, []) == {}


# --- candidate pool --------------------------------------------------------


async def test_avoided_excluded_from_candidates(db: AsyncSession, seeded: None) -> None:
    ex = await _first_exercise_with_pattern(db, MovementPattern.HORIZONTAL_PUSH)
    await pref_svc.set_preference(db, ex.id, ExercisePreferenceStatus.AVOID)

    candidates = await _candidate_exercises(db, limitations=[])
    assert ex.id not in {c.id for c in candidates}


async def test_favorites_get_selection_priority(db: AsyncSession, seeded: None) -> None:
    ex = await _first_exercise_with_pattern(db, MovementPattern.HORIZONTAL_PULL)
    await pref_svc.set_preference(db, ex.id, ExercisePreferenceStatus.FAVORITE)

    candidates = await _candidate_exercises(db, limitations=[])
    # favorites are weighted into the pool more than once so the generator prefers them
    assert sum(1 for c in candidates if c.id == ex.id) > 1


async def test_limitation_filters_blocked_pattern(db: AsyncSession, seeded: None) -> None:
    # with the full seeded pool, blocking one pattern still leaves enough variety,
    # so the limitation filter is applied rather than falling back.
    candidates = await _candidate_exercises(db, limitations=["knee"])
    assert MovementPattern.SQUAT not in {c.pattern for c in candidates}


# --- REST endpoints --------------------------------------------------------


async def test_preference_endpoints_roundtrip(client: AsyncClient, seeded: None) -> None:
    ex_id = (await client.get("/api/exercises")).json()[0]["id"]

    put = await client.put(f"/api/exercises/{ex_id}/preference", json={"status": "favorite"})
    assert put.status_code == 200
    assert put.json()["status"] == "favorite"

    listed = {e["id"]: e for e in (await client.get("/api/exercises")).json()}
    assert listed[ex_id]["preference"] == "favorite"

    detail = await client.get(f"/api/exercises/{ex_id}")
    assert detail.json()["preference"] == "favorite"

    cleared = await client.delete(f"/api/exercises/{ex_id}/preference")
    assert cleared.status_code == 204
    assert (await client.get(f"/api/exercises/{ex_id}")).json()["preference"] is None


async def test_preference_missing_exercise_404(client: AsyncClient, seeded: None) -> None:
    assert (
        await client.put("/api/exercises/999999/preference", json={"status": "avoid"})
    ).status_code == 404
    assert (await client.delete("/api/exercises/999999/preference")).status_code == 404


# --- profile limitations ---------------------------------------------------


async def test_profile_limitations_upsert_and_dedup(client: AsyncClient) -> None:
    payload = {**PROFILE, "limitations": ["shoulder", "knee", "shoulder"]}
    r = await client.put("/api/profile", json=payload)
    assert r.status_code == 200
    assert r.json()["limitations"] == ["shoulder", "knee"]

    got = await client.get("/api/profile")
    assert got.json()["limitations"] == ["shoulder", "knee"]


async def test_profile_invalid_limitation_422(client: AsyncClient) -> None:
    bad = {**PROFILE, "limitations": ["ankle"]}
    assert (await client.put("/api/profile", json=bad)).status_code == 422


async def test_plan_respects_limitations(client: AsyncClient, seeded: None) -> None:
    await client.put("/api/profile", json={**PROFILE, "limitations": ["knee"]})
    plan = (await client.post("/api/plans", json={"days_per_week": 4})).json()
    patterns = {pe["exercise"]["pattern"] for day in plan["days"] for pe in day["exercises"]}
    assert "squat" not in patterns
