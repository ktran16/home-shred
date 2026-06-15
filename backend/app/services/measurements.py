"""Custom body measurements (SPEC §19.8 W1).

A generic, user-extensible measurement system that complements the fixed `body_metrics`
columns (weight / body_fat / waist, which the §8 nutrition engine reads). Each
`MeasurementType` (chest, arms, …) owns a dated `MeasurementEntry` series; one value per
type per day (upsert), mirroring how `body_metrics` keys on `date`.
"""

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MeasurementEntry, MeasurementType
from app.schemas.measurement import MeasurementEntryIn, MeasurementTypeIn

# rationale (SPEC §19.8 W1): common circumference measures seeded so the user starts with
# useful options. weight/body_fat/waist are deliberately excluded — they live in
# body_metrics for §8 nutrition and must not be double-sourced here.
BUILTIN_MEASUREMENT_TYPES: list[tuple[str, str, str]] = [
    ("chest", "Chest", "cm"),
    ("shoulders", "Shoulders", "cm"),
    ("hips", "Hips", "cm"),
    ("left_arm", "Left arm", "cm"),
    ("right_arm", "Right arm", "cm"),
    ("left_thigh", "Left thigh", "cm"),
    ("right_thigh", "Right thigh", "cm"),
    ("calf", "Calf", "cm"),
    ("neck", "Neck", "cm"),
]


class DuplicateMeasurementTypeError(Exception):
    """A measurement type with this key already exists."""


class MeasurementTypeNotFoundError(Exception):
    """No measurement type with the given id."""


class BuiltinMeasurementTypeError(Exception):
    """Built-in measurement types cannot be deleted."""


class MeasurementEntryNotFoundError(Exception):
    """No measurement entry with the given id."""


def slugify(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_")
    return slug or "measurement"


async def ensure_builtin_types(db: AsyncSession) -> None:
    """Idempotently seed the built-in measurement types (no-op if already present)."""
    stmt = pg_insert(MeasurementType).values(
        [
            {"key": key, "label": label, "unit": unit, "builtin": True}
            for key, label, unit in BUILTIN_MEASUREMENT_TYPES
        ]
    )
    stmt = stmt.on_conflict_do_nothing(index_elements=[MeasurementType.key])
    await db.execute(stmt)
    await db.commit()


async def list_types(db: AsyncSession) -> list[MeasurementType]:
    await ensure_builtin_types(db)
    stmt = select(MeasurementType).order_by(
        MeasurementType.builtin.desc(), MeasurementType.label
    )
    return list((await db.scalars(stmt)).all())


async def create_type(db: AsyncSession, data: MeasurementTypeIn) -> MeasurementType:
    await ensure_builtin_types(db)
    key = slugify(data.label)
    existing = await db.scalar(select(MeasurementType).where(MeasurementType.key == key))
    if existing is not None:
        raise DuplicateMeasurementTypeError(key)
    mtype = MeasurementType(key=key, label=data.label, unit=data.unit, builtin=False)
    db.add(mtype)
    await db.commit()
    await db.refresh(mtype)
    return mtype


async def delete_type(db: AsyncSession, type_id: int) -> None:
    mtype = await db.get(MeasurementType, type_id)
    if mtype is None:
        raise MeasurementTypeNotFoundError(type_id)
    if mtype.builtin:
        raise BuiltinMeasurementTypeError(type_id)
    await db.delete(mtype)
    await db.commit()


async def upsert_entry(db: AsyncSession, data: MeasurementEntryIn) -> MeasurementEntry:
    if await db.get(MeasurementType, data.type_id) is None:
        raise MeasurementTypeNotFoundError(data.type_id)
    entry_date = data.date or date.today()
    stmt = (
        pg_insert(MeasurementEntry)
        .values(type_id=data.type_id, date=entry_date, value=data.value)
        .on_conflict_do_update(
            index_elements=[MeasurementEntry.type_id, MeasurementEntry.date],
            set_={"value": data.value},
        )
        .returning(MeasurementEntry)
    )
    result = await db.execute(stmt)
    await db.commit()
    entry = result.scalar_one()
    # The session may already hold this row (same type+date) from a prior upsert; refresh
    # so the returned value reflects the conflict update rather than a stale identity-map copy.
    await db.refresh(entry)
    return entry


async def delete_entry(db: AsyncSession, entry_id: int) -> None:
    entry = await db.get(MeasurementEntry, entry_id)
    if entry is None:
        raise MeasurementEntryNotFoundError(entry_id)
    await db.delete(entry)
    await db.commit()


async def list_entries(
    db: AsyncSession,
    *,
    type_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[MeasurementEntry]:
    stmt = select(MeasurementEntry)
    if type_id is not None:
        stmt = stmt.where(MeasurementEntry.type_id == type_id)
    if date_from is not None:
        stmt = stmt.where(MeasurementEntry.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(MeasurementEntry.date <= date_to)
    stmt = stmt.order_by(MeasurementEntry.type_id, MeasurementEntry.date)
    return list((await db.scalars(stmt)).all())


@dataclass(frozen=True)
class MeasurementSeries:
    type: MeasurementType
    entries: list[MeasurementEntry]

    @property
    def latest(self) -> Decimal | None:
        return Decimal(self.entries[-1].value) if self.entries else None

    @property
    def change(self) -> Decimal | None:
        if len(self.entries) < 2:
            return None
        return Decimal(self.entries[-1].value) - Decimal(self.entries[0].value)


async def measurement_series(
    db: AsyncSession, *, date_from: date | None = None, date_to: date | None = None
) -> list[MeasurementSeries]:
    """Per-type chronological series, only for types that have at least one entry."""
    types = await list_types(db)
    entries = await list_entries(db, date_from=date_from, date_to=date_to)
    by_type: dict[int, list[MeasurementEntry]] = defaultdict(list)
    for entry in entries:
        by_type[entry.type_id].append(entry)
    return [
        MeasurementSeries(type=mtype, entries=by_type[mtype.id])
        for mtype in types
        if by_type.get(mtype.id)
    ]
