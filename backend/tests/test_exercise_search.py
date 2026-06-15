"""Tests for local exercise semantic-ish search (SPEC §17.3 A3)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Exercise
from app.seed.seed_exercises import build_rows
from app.services.exercise_search import (
    SearchDoc,
    expand,
    rank_exercises,
    score_doc,
    search_exercises,
    tokenize,
)


@pytest.fixture
async def seeded(db: AsyncSession) -> None:
    for row in build_rows():
        db.add(Exercise(**row))
    await db.commit()


def test_tokenize_drops_stopwords_and_short() -> None:
    assert tokenize("Find a hamstring exercise") == {"find", "hamstring"}
    assert tokenize("the of for to") == set()


def test_expand_adds_synonyms() -> None:
    expanded = expand({"rdl"})
    assert {"rdl", "romanian", "deadlift", "hinge", "hamstring"} <= expanded


def test_score_and_rank_prefer_relevant() -> None:
    docs = [
        SearchDoc(1, "DB Romanian Deadlift", ["hamstrings", "glutes"], ["back"], "hinge", "legs"),
        SearchDoc(2, "Push-up", ["chest"], ["triceps"], "horizontal_push", "push"),
    ]
    hits = rank_exercises("hamstring exercise like an rdl", docs)
    assert hits[0].id == 1
    assert hits[0].score > 0
    # the push-up shares no tokens with the hamstring query and is dropped.
    assert all(h.id != 2 for h in hits)


def test_rank_empty_query() -> None:
    docs = [SearchDoc(1, "Push-up", ["chest"], [], "horizontal_push", "push")]
    assert rank_exercises("   ", docs) == []


def test_score_name_beats_secondary() -> None:
    name_hit = SearchDoc(1, "Squat", ["quads"], [], "squat", "legs")
    secondary_hit = SearchDoc(2, "Lunge", ["glutes"], ["squat"], "squat", "legs")
    query = {"squat"}
    assert score_doc(query, name_hit) > score_doc(query, secondary_hit)


async def test_search_exercises_db(db: AsyncSession, seeded: None) -> None:
    results = await search_exercises(db, "squat", limit=5)
    assert results
    exercises, scores = zip(*results, strict=True)
    assert all(s > 0 for s in scores)
    assert list(scores) == sorted(scores, reverse=True)  # ranked
    assert any(
        "squat" in e.name.lower() or (e.pattern and e.pattern.value == "squat") for e in exercises
    )


async def test_search_endpoint(client: AsyncClient, seeded: None) -> None:
    r = await client.get("/api/exercises/search", params={"q": "row", "limit": 3})
    assert r.status_code == 200  # not shadowed by /{exercise_id}
    body = r.json()
    assert len(body) <= 3
    assert body and body[0]["score"] > 0
    assert "name" in body[0]["exercise"]


async def test_search_endpoint_requires_query(client: AsyncClient, seeded: None) -> None:
    assert (await client.get("/api/exercises/search", params={"q": ""})).status_code == 422
