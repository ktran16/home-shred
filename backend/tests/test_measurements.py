"""Tests for custom body measurements (SPEC §19.8 W1)."""

from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.measurement import MeasurementEntryIn, MeasurementTypeIn
from app.services import measurements as svc

pytestmark = pytest.mark.asyncio


async def test_list_types_seeds_builtins_idempotently(db: AsyncSession) -> None:
    first = await svc.list_types(db)
    assert len(first) == len(svc.BUILTIN_MEASUREMENT_TYPES)
    assert all(t.builtin for t in first)
    # Calling again must not duplicate.
    second = await svc.list_types(db)
    assert len(second) == len(first)


async def test_create_type_slugifies_and_rejects_duplicates(db: AsyncSession) -> None:
    created = await svc.create_type(db, MeasurementTypeIn(label="Left Forearm", unit="cm"))
    assert created.key == "left_forearm"
    assert created.builtin is False

    # Duplicate slug (case/space-insensitive) is rejected.
    with pytest.raises(svc.DuplicateMeasurementTypeError):
        await svc.create_type(db, MeasurementTypeIn(label="left forearm"))
    # Clashing with a built-in key is also rejected.
    with pytest.raises(svc.DuplicateMeasurementTypeError):
        await svc.create_type(db, MeasurementTypeIn(label="Chest"))


async def test_delete_type_rules(db: AsyncSession) -> None:
    types = await svc.list_types(db)
    builtin = types[0]
    with pytest.raises(svc.BuiltinMeasurementTypeError):
        await svc.delete_type(db, builtin.id)

    custom = await svc.create_type(db, MeasurementTypeIn(label="Bicep peak"))
    await svc.delete_type(db, custom.id)  # ok
    with pytest.raises(svc.MeasurementTypeNotFoundError):
        await svc.delete_type(db, custom.id)


async def test_upsert_entry_one_value_per_day(db: AsyncSession) -> None:
    mtype = (await svc.list_types(db))[0]
    day = date(2026, 6, 1)
    first = await svc.upsert_entry(
        db, MeasurementEntryIn(type_id=mtype.id, date=day, value=Decimal("40.0"))
    )
    again = await svc.upsert_entry(
        db, MeasurementEntryIn(type_id=mtype.id, date=day, value=Decimal("41.5"))
    )
    assert first.id == again.id  # upsert, not insert
    assert Decimal(again.value) == Decimal("41.5")

    with pytest.raises(svc.MeasurementTypeNotFoundError):
        await svc.upsert_entry(db, MeasurementEntryIn(type_id=9999, value=Decimal("10")))


async def test_delete_entry(db: AsyncSession) -> None:
    mtype = (await svc.list_types(db))[0]
    entry = await svc.upsert_entry(
        db, MeasurementEntryIn(type_id=mtype.id, value=Decimal("33.3"))
    )
    await svc.delete_entry(db, entry.id)
    with pytest.raises(svc.MeasurementEntryNotFoundError):
        await svc.delete_entry(db, entry.id)


async def test_series_only_types_with_entries_and_change(db: AsyncSession) -> None:
    types = await svc.list_types(db)
    mtype = types[0]
    await svc.upsert_entry(
        db, MeasurementEntryIn(type_id=mtype.id, date=date(2026, 6, 1), value=Decimal("40.0"))
    )
    await svc.upsert_entry(
        db, MeasurementEntryIn(type_id=mtype.id, date=date(2026, 6, 8), value=Decimal("42.0"))
    )
    series = await svc.measurement_series(db)
    assert len(series) == 1  # only the one with entries
    s = series[0]
    assert s.type.id == mtype.id
    assert [p.date for p in s.entries] == [date(2026, 6, 1), date(2026, 6, 8)]
    assert s.latest == Decimal("42.00")
    assert s.change == Decimal("2.00")


async def test_api_roundtrip(client: AsyncClient) -> None:
    # Built-ins are listed.
    types = (await client.get("/api/measurements/types")).json()
    assert len(types) >= len(svc.BUILTIN_MEASUREMENT_TYPES)

    # Create a custom type.
    created = await client.post("/api/measurements/types", json={"label": "Forearm", "unit": "cm"})
    assert created.status_code == 201
    type_id = created.json()["id"]

    # Duplicate -> 409.
    dup = await client.post("/api/measurements/types", json={"label": "forearm"})
    assert dup.status_code == 409

    # Log an entry.
    posted = await client.post(
        "/api/measurements/entries",
        json={"type_id": type_id, "date": "2026-06-10", "value": 30.5},
    )
    assert posted.status_code == 201
    entry_id = posted.json()["id"]

    # Missing type -> 404.
    bad = await client.post(
        "/api/measurements/entries", json={"type_id": 9999, "value": 10}
    )
    assert bad.status_code == 404

    # Series reflects the entry.
    series = (await client.get("/api/measurements/series")).json()
    assert any(s["type"]["id"] == type_id and s["points"] for s in series)

    # Delete entry -> 204, then 404.
    assert (await client.delete(f"/api/measurements/entries/{entry_id}")).status_code == 204
    assert (await client.delete(f"/api/measurements/entries/{entry_id}")).status_code == 404

    # Built-in cannot be deleted -> 409.
    builtin_id = types[0]["id"]
    assert (await client.delete(f"/api/measurements/types/{builtin_id}")).status_code == 409
