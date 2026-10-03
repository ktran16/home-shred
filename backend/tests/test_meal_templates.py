"""Tests for meal / recipe templates (SPEC §19.9 N2)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import FoodLogSource
from app.models import FoodLog, MealTemplateItem
from app.schemas.nutrition import FoodItemIn, FoodLogIn
from app.services import food_log
from app.services import meal_templates as svc

DAY = date(2026, 6, 15)

OATS = FoodItemIn(
    name="Oats", grams=Decimal("80"), kcal=300, protein_g=Decimal("10.0"),
    carbs_g=Decimal("54.0"), fat_g=Decimal("5.0"),
)  # fmt: skip
WHEY = FoodItemIn(
    name="Whey", grams=Decimal("30"), kcal=121, protein_g=Decimal("24.0"),
    carbs_g=Decimal("2.5"), fat_g=Decimal("1.5"), source=FoodLogSource.BARCODE,
    barcode="5012345678900",
)  # fmt: skip


def dec(value: object) -> Decimal:
    return Decimal(str(value))


async def _rows(db: AsyncSession, model: type, day: date | None = None) -> int:
    stmt = select(func.count()).select_from(model)
    if day is not None:
        stmt = stmt.where(FoodLog.date == day)
    return int(await db.scalar(stmt) or 0)


async def test_create_lists_and_rejects_duplicate_names(db: AsyncSession) -> None:
    created = await svc.create_template(db, "  Breakfast ", [OATS, WHEY])
    assert created.name == "Breakfast"
    assert [(i.position, i.name) for i in created.items] == [(0, "Oats"), (1, "Whey")]
    assert created.items[1].source == FoodLogSource.BARCODE
    assert created.items[1].barcode == "5012345678900"

    await svc.create_template(db, "after training", [WHEY])
    assert [t.name for t in await svc.list_templates(db)] == ["after training", "Breakfast"]

    with pytest.raises(svc.DuplicateMealTemplateError):
        await svc.create_template(db, "BREAKFAST", [OATS])


async def test_empty_items_rejected(db: AsyncSession) -> None:
    with pytest.raises(svc.EmptyMealTemplateError):
        await svc.create_template(db, "Nothing", [])


async def test_create_from_day_snapshots_and_stays_frozen(db: AsyncSession) -> None:
    with pytest.raises(food_log.FoodLogSourceDayEmptyError):
        await svc.create_from_day(db, "Empty day", DAY)

    logged = await food_log.create_entries(
        db,
        [
            FoodLogIn(date=DAY, **OATS.model_dump()),
            FoodLogIn(date=DAY, **WHEY.model_dump()),
        ],
    )
    template = await svc.create_from_day(db, "Usual breakfast", DAY)
    assert [i.name for i in template.items] == ["Oats", "Whey"]
    assert template.items[1].barcode == "5012345678900"

    # Deleting the source rows must not touch the template (macros are frozen copies).
    for entry in logged:
        await food_log.delete_entry(db, entry.id)
    again = await svc.get_template(db, template.id)
    assert [i.kcal for i in again.items] == [300, 121]


async def test_log_template_clones_rows_with_scaled_macros(db: AsyncSession) -> None:
    template = await svc.create_template(db, "Breakfast", [OATS, WHEY])

    rows = await svc.log_template(db, template.id, DAY, Decimal("1.5"))
    assert [r.name for r in rows] == ["Oats", "Whey"]
    assert all(r.date == DAY for r in rows)
    oats, whey = rows
    assert dec(oats.grams) == Decimal("120.0")
    assert oats.kcal == 450
    assert dec(oats.protein_g) == Decimal("15.0")
    assert dec(oats.carbs_g) == Decimal("81.0")
    # 121 × 1.5 = 181.5 → 182; 2.5 × 1.5 = 3.75 → 3.8; 1.5 × 1.5 = 2.25 → 2.3 (half-up)
    assert whey.kcal == 182
    assert dec(whey.carbs_g) == Decimal("3.8")
    assert dec(whey.fat_g) == Decimal("2.3")
    assert whey.source == FoodLogSource.BARCODE
    assert whey.barcode == "5012345678900"

    daily = await food_log.daily_log(db, DAY)
    assert len(daily.entries) == 2
    assert daily.totals.kcal == 632


async def test_log_template_scale_limits_are_atomic(db: AsyncSession) -> None:
    tiny = FoodItemIn(
        name="Salt", grams=Decimal("0.1"), kcal=0, protein_g=Decimal("0"),
        carbs_g=Decimal("0"), fat_g=Decimal("0"),
    )  # fmt: skip
    huge = FoodItemIn(
        name="Rice pot", grams=Decimal("4000"), kcal=5200, protein_g=Decimal("100"),
        carbs_g=Decimal("1100"), fat_g=Decimal("10"),
    )  # fmt: skip
    small = await svc.create_template(db, "Seasoning", [tiny])
    big = await svc.create_template(db, "Batch cook", [OATS, huge])

    with pytest.raises(svc.MealTemplateScaleError):
        await svc.log_template(db, small.id, DAY, Decimal("0.2"))
    with pytest.raises(svc.MealTemplateScaleError):
        await svc.log_template(db, small.id, DAY, Decimal("4.5"))

    # 4000 g × 4 exceeds the 10 kg food-log limit → nothing is logged, not even the oats.
    with pytest.raises(svc.MealTemplateScaleError):
        await svc.log_template(db, big.id, DAY, Decimal("4"))
    assert await _rows(db, FoodLog, DAY) == 0

    # Scaling a 0.1 g item down still satisfies grams > 0.
    (salt,) = await svc.log_template(db, small.id, DAY, Decimal("0.25"))
    assert dec(salt.grams) == Decimal("0.1")


async def test_delete_cascades_and_missing_ids(db: AsyncSession) -> None:
    template = await svc.create_template(db, "Breakfast", [OATS, WHEY])
    assert await _rows(db, MealTemplateItem) == 2

    await svc.delete_template(db, template.id)
    assert await _rows(db, MealTemplateItem) == 0
    assert await svc.list_templates(db) == []

    with pytest.raises(svc.MealTemplateNotFoundError):
        await svc.delete_template(db, template.id)
    with pytest.raises(svc.MealTemplateNotFoundError):
        await svc.log_template(db, template.id, DAY)


async def test_meal_template_api_roundtrip(client: AsyncClient) -> None:
    today = date.today()
    macros = ("name", "grams", "kcal", "protein_g", "carbs_g", "fat_g")
    items = [
        dict(zip(macros, ("Oats", 80, 300, 10, 54, 5), strict=True)),
        dict(zip(macros, ("Banana", 120, 105, 1.3, 27, 0.4), strict=True)),
    ]

    created = await client.post(
        "/api/nutrition/templates", json={"name": "Oat bowl", "items": items}
    )
    assert created.status_code == 201
    template = created.json()
    assert template["name"] == "Oat bowl"
    assert [i["name"] for i in template["items"]] == ["Oats", "Banana"]

    dup = await client.post("/api/nutrition/templates", json={"name": "oat bowl", "items": items})
    assert dup.status_code == 409
    both = {"name": "X", "items": items, "from_date": today.isoformat()}
    assert (await client.post("/api/nutrition/templates", json=both)).status_code == 422
    assert (await client.post("/api/nutrition/templates", json={"name": "X"})).status_code == 422
    empty = await client.post("/api/nutrition/templates", json={"name": "X", "items": []})
    assert empty.status_code == 422
    no_food = {"name": "X", "from_date": (today - timedelta(days=30)).isoformat()}
    assert (await client.post("/api/nutrition/templates", json=no_food)).status_code == 404

    listed = (await client.get("/api/nutrition/templates")).json()
    assert [t["id"] for t in listed] == [template["id"]]

    url = f"/api/nutrition/templates/{template['id']}/log"
    logged = await client.post(url, json={"date": today.isoformat(), "scale": 2})
    assert logged.status_code == 201
    day = logged.json()
    assert day["date"] == today.isoformat()
    assert [e["name"] for e in day["entries"]] == ["Oats", "Banana"]
    assert day["totals"]["kcal"] == 810
    assert dec(day["entries"][1]["protein_g"]) == Decimal("2.6")

    # Multi-row semantics: each food is its own entry and can be deleted on its own.
    after = await client.delete(f"/api/nutrition/log/{day['entries'][1]['id']}")
    assert [e["name"] for e in after.json()["entries"]] == ["Oats"]

    assert (await client.post(url, json={"scale": 5})).status_code == 422
    assert (await client.post("/api/nutrition/templates/9999/log", json={})).status_code == 404

    from_day = await client.post(
        "/api/nutrition/templates", json={"name": "Today", "from_date": today.isoformat()}
    )
    assert from_day.status_code == 201
    assert [i["name"] for i in from_day.json()["items"]] == ["Oats"]

    assert (await client.delete(f"/api/nutrition/templates/{template['id']}")).status_code == 204
    assert (await client.delete(f"/api/nutrition/templates/{template['id']}")).status_code == 404
