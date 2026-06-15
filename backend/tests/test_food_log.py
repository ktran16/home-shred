from datetime import date, timedelta
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import FoodLogSource
from app.models import BodyMetric, FoodLog

PROFILE = {
    "name": "Khoa",
    "sex": "male",
    "age": 30,
    "height_cm": 180.0,
    "weight_kg": 80.0,
    "activity_level": "moderate",
    "experience_level": "intermediate",
}


def dec(value: object) -> Decimal:
    return Decimal(str(value))


async def test_food_log_create_get_delete_flow(client: AsyncClient) -> None:
    await client.put("/api/profile", json=PROFILE)
    today = date.today().isoformat()

    created = await client.post(
        "/api/nutrition/log",
        json={
            "date": today,
            "name": "Greek yogurt",
            "grams": 200.0,
            "kcal": 190,
            "protein_g": 20.0,
            "carbs_g": 12.0,
            "fat_g": 5.0,
            "source": "manual",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["date"] == today
    assert body["totals"]["kcal"] == 190
    assert dec(body["totals"]["protein_g"]) == Decimal("20.0")
    assert body["remaining_kcal"] == body["target"]["target_kcal"] - 190
    entry_id = body["entries"][0]["id"]

    listed = await client.get("/api/nutrition/log", params={"date": today})
    assert listed.status_code == 200
    assert listed.json()["entries"][0]["name"] == "Greek yogurt"

    deleted = await client.delete(f"/api/nutrition/log/{entry_id}")
    assert deleted.status_code == 200
    assert deleted.json()["entries"] == []
    assert deleted.json()["totals"]["kcal"] == 0


async def test_food_log_barcode_source_and_validation(client: AsyncClient) -> None:
    bad = await client.post(
        "/api/nutrition/log",
        json={
            "name": "   ",
            "grams": 100,
            "kcal": 50,
            "protein_g": 1,
            "carbs_g": 10,
            "fat_g": 1,
        },
    )
    assert bad.status_code == 422

    good = await client.post(
        "/api/nutrition/log",
        json={
            "name": "Protein bar",
            "grams": 60,
            "kcal": 220,
            "protein_g": 20,
            "carbs_g": 24,
            "fat_g": 7,
            "source": "barcode",
            "barcode": "1234567890123",
        },
    )
    assert good.status_code == 201
    entry = good.json()["entries"][0]
    assert entry["source"] == "barcode"
    assert entry["barcode"] == "1234567890123"

    assert (await client.delete("/api/nutrition/log/99999")).status_code == 404


async def test_food_log_recent_and_copy_day(client: AsyncClient) -> None:
    await client.put("/api/profile", json=PROFILE)
    today = date.today()
    yesterday = today - timedelta(days=1)
    older = today - timedelta(days=2)

    yogurt = {
        "name": "Greek yogurt",
        "grams": 200,
        "kcal": 190,
        "protein_g": 20,
        "carbs_g": 12,
        "fat_g": 5,
        "source": "manual",
    }
    bar = {
        "name": "Protein bar",
        "grams": 60,
        "kcal": 220,
        "protein_g": 20,
        "carbs_g": 24,
        "fat_g": 7,
        "source": "barcode",
        "barcode": "1234567890123",
    }
    await client.post("/api/nutrition/log", json={**yogurt, "date": older.isoformat()})
    await client.post("/api/nutrition/log", json={**bar, "date": yesterday.isoformat()})
    await client.post("/api/nutrition/log", json={**yogurt, "date": yesterday.isoformat()})

    recent = await client.get("/api/nutrition/log/recent", params={"limit": 5})
    assert recent.status_code == 200
    foods = recent.json()
    assert [food["name"] for food in foods] == ["Greek yogurt", "Protein bar"]
    assert foods[0]["last_logged_on"] == yesterday.isoformat()
    assert foods[1]["barcode"] == "1234567890123"

    copied = await client.post(
        "/api/nutrition/log/copy-day",
        json={"from_date": yesterday.isoformat(), "to_date": today.isoformat()},
    )
    assert copied.status_code == 201
    copied_body = copied.json()
    assert copied_body["date"] == today.isoformat()
    assert [entry["name"] for entry in copied_body["entries"]] == ["Protein bar", "Greek yogurt"]
    assert copied_body["totals"]["kcal"] == 410

    empty = await client.post(
        "/api/nutrition/log/copy-day",
        json={"from_date": (today - timedelta(days=10)).isoformat(), "to_date": today.isoformat()},
    )
    assert empty.status_code == 404

    same_day = await client.post(
        "/api/nutrition/log/copy-day",
        json={"from_date": today.isoformat(), "to_date": today.isoformat()},
    )
    assert same_day.status_code == 422


async def test_adaptive_tdee_prefers_logged_intake(client: AsyncClient, db: AsyncSession) -> None:
    await client.put("/api/profile", json=PROFILE)
    today = date.today()

    for i in range(4):
        db.add(BodyMetric(date=today - timedelta(days=21 - 7 * i), weight_kg=80.0 - 0.5 * i))
    for offset in range(29):
        db.add(
            FoodLog(
                date=today - timedelta(days=28 - offset),
                name="Logged day",
                grams=Decimal("1.0"),
                kcal=2500,
                protein_g=Decimal("1.0"),
                carbs_g=Decimal("1.0"),
                fat_g=Decimal("1.0"),
                source=FoodLogSource.MANUAL,
            )
        )
    await db.commit()

    preview = (await client.get("/api/nutrition/adaptive")).json()
    assert preview["enough_data"] is True
    assert preview["assumed_intake_kcal"] == 2500
    assert preview["estimated_tdee_kcal"] > 3000
