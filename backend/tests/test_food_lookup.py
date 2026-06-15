"""Tests for barcode → Open Food Facts macro lookup (SPEC §17.5 B2b).

The pure OFF parser is tested directly; the endpoint is tested with the network call
monkeypatched so no test ever reaches Open Food Facts.
"""

import pytest
from httpx import AsyncClient

from app.services import food_lookup
from app.services.food_lookup import (
    FoodFacts,
    FoodLookupError,
    FoodNotFoundError,
    parse_off_product,
)


def _off_payload() -> dict:
    return {
        "status": 1,
        "code": "737628064502",
        "product": {
            "product_name": "  Crunchy Peanut Butter ",
            "brands": "Acme",
            "serving_size": "32 g",
            "nutriments": {
                "energy-kcal_100g": 588,
                "proteins_100g": 25.1,
                "carbohydrates_100g": "20",
                "fat_100g": 50.0,
            },
        },
    }


def test_parse_found() -> None:
    facts = parse_off_product(_off_payload())
    assert facts is not None
    assert facts.code == "737628064502"
    assert facts.name == "Crunchy Peanut Butter"  # trimmed
    assert facts.brand == "Acme"
    assert facts.serving_size == "32 g"
    assert facts.kcal_per_100g == 588.0
    assert facts.protein_per_100g == 25.1
    assert facts.carbs_per_100g == 20.0  # string coerced
    assert facts.fat_per_100g == 50.0


def test_parse_not_found() -> None:
    assert parse_off_product({"status": 0, "code": "x", "product": {}}) is None


def test_parse_missing_nutriments() -> None:
    facts = parse_off_product({"status": 1, "code": "1", "product": {"product_name": "Water"}})
    assert facts is not None
    assert facts.name == "Water"
    assert facts.kcal_per_100g is None
    assert facts.protein_per_100g is None


async def test_barcode_endpoint_found(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake(code: str, **_: object) -> FoodFacts:
        return FoodFacts(
            code=code,
            name="Test Food",
            brand=None,
            serving_size=None,
            kcal_per_100g=100.0,
            protein_per_100g=10.0,
            carbs_per_100g=5.0,
            fat_per_100g=2.0,
        )

    monkeypatch.setattr(food_lookup, "lookup_barcode", _fake)
    r = await client.get("/api/nutrition/barcode/123")
    assert r.status_code == 200
    assert r.json()["name"] == "Test Food"
    assert r.json()["kcal_per_100g"] == 100.0


async def test_barcode_endpoint_not_found(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _fake(code: str, **_: object) -> FoodFacts:
        raise FoodNotFoundError(code)

    monkeypatch.setattr(food_lookup, "lookup_barcode", _fake)
    assert (await client.get("/api/nutrition/barcode/000")).status_code == 404


async def test_barcode_endpoint_upstream_error(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _fake(code: str, **_: object) -> FoodFacts:
        raise FoodLookupError("timeout")

    monkeypatch.setattr(food_lookup, "lookup_barcode", _fake)
    assert (await client.get("/api/nutrition/barcode/999")).status_code == 502
