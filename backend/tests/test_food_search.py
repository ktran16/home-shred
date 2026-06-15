"""Tests for food search by name (SPEC §19.8 W2).

The pure OFF search parser is tested directly; the service/endpoint are tested with the
network fetch monkeypatched so no test reaches Open Food Facts.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import food_search
from app.services.food_lookup import FoodFacts, FoodLookupError
from app.services.food_search import parse_off_search


def _search_payload() -> dict:
    return {
        "products": [
            {
                "code": "111",
                "product_name": "  Chicken Breast ",
                "brands": "Generic",
                "nutriments": {"energy-kcal_100g": 165, "proteins_100g": 31, "fat_100g": 3.6},
            },
            {  # dropped: no name
                "code": "222",
                "product_name": "",
                "nutriments": {"energy-kcal_100g": 100},
            },
            {  # dropped: no barcode (cache is keyed on code)
                "product_name": "Mystery",
                "nutriments": {},
            },
        ]
    }


def test_parse_off_search_filters_nameless_and_codeless() -> None:
    facts = parse_off_search(_search_payload())
    assert len(facts) == 1
    assert facts[0].code == "111"
    assert facts[0].name == "Chicken Breast"  # trimmed
    assert facts[0].kcal_per_100g == 165.0
    assert facts[0].protein_per_100g == 31.0


def test_parse_off_search_empty() -> None:
    assert parse_off_search({}) == []


async def _fake_facts() -> list[FoodFacts]:
    return [
        FoodFacts("111", "Chicken Breast", "Generic", None, 165.0, 31.0, 0.0, 3.6),
        FoodFacts("333", "Chicken Breast Sandwich Deluxe", None, None, 250.0, 12.0, 30.0, 8.0),
    ]


async def test_search_foods_caches_and_ranks_shorter_first(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _fake(query: str, *, limit: int, **_: object) -> list[FoodFacts]:
        return await _fake_facts()

    monkeypatch.setattr(food_search, "search_off", _fake)
    hits = await food_search.search_foods(db, "chicken", limit=10)
    names = [h.name for h in hits]
    assert names == ["Chicken Breast", "Chicken Breast Sandwich Deluxe"]  # shorter first
    # cached: a second search with OFF "down" still returns the cached rows.
    cached = await food_search.search_cache(db, "chicken", limit=10)
    assert {f.code for f in cached} == {"111", "333"}


async def test_search_foods_offline_falls_back_to_cache(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Prime the cache.
    await food_search.cache_foods(db, await _fake_facts())

    async def _down(query: str, *, limit: int, **_: object) -> list[FoodFacts]:
        raise FoodLookupError("offline")

    monkeypatch.setattr(food_search, "search_off", _down)
    hits = await food_search.search_foods(db, "chicken", limit=10)
    assert {h.code for h in hits} == {"111", "333"}  # served from cache despite OFF down


async def test_search_foods_blank_query_returns_empty(db: AsyncSession) -> None:
    assert await food_search.search_foods(db, "   ") == []


async def test_cache_upsert_updates_existing(db: AsyncSession) -> None:
    await food_search.cache_foods(db, [FoodFacts("111", "Old Name", None, None, 100.0, 1, 1, 1)])
    await food_search.cache_foods(db, [FoodFacts("111", "New Name", None, None, 120.0, 2, 2, 2)])
    rows = await food_search.search_cache(db, "name", limit=10)
    assert len(rows) == 1  # upsert on code, not a second row
    assert rows[0].name == "New Name"
    assert float(rows[0].kcal_per_100g) == 120.0


async def test_endpoint(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake(query: str, *, limit: int, **_: object) -> list[FoodFacts]:
        return await _fake_facts()

    monkeypatch.setattr(food_search, "search_off", _fake)
    r = await client.get("/api/nutrition/food/search", params={"q": "chicken"})
    assert r.status_code == 200
    body = r.json()
    assert body[0]["name"] == "Chicken Breast"
    assert body[0]["kcal_per_100g"] == 165.0
    # blank q rejected by query validation
    assert (await client.get("/api/nutrition/food/search", params={"q": ""})).status_code == 422
