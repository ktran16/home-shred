from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FoodLog, NutritionTarget
from app.schemas.nutrition import FoodLogIn


class FoodLogNotFoundError(Exception):
    """Raised when a requested food-log entry does not exist."""


class FoodLogSourceDayEmptyError(Exception):
    """Raised when copying from a day with no food-log entries."""


@dataclass(frozen=True)
class FoodLogTotals:
    kcal: int
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal


@dataclass(frozen=True)
class DailyFoodLog:
    date: date
    entries: list[FoodLog]
    totals: FoodLogTotals
    target: NutritionTarget | None

    @property
    def remaining_kcal(self) -> int | None:
        return None if self.target is None else self.target.target_kcal - self.totals.kcal

    @property
    def remaining_protein_g(self) -> Decimal | None:
        if self.target is None:
            return None
        return Decimal(self.target.protein_g) - self.totals.protein_g

    @property
    def remaining_carbs_g(self) -> Decimal | None:
        return None if self.target is None else Decimal(self.target.carbs_g) - self.totals.carbs_g

    @property
    def remaining_fat_g(self) -> Decimal | None:
        return None if self.target is None else Decimal(self.target.fat_g) - self.totals.fat_g


async def create_entry(db: AsyncSession, data: FoodLogIn) -> FoodLog:
    entry = FoodLog(
        date=data.date or date.today(),
        name=data.name.strip(),
        grams=data.grams,
        kcal=data.kcal,
        protein_g=data.protein_g,
        carbs_g=data.carbs_g,
        fat_g=data.fat_g,
        source=data.source,
        barcode=data.barcode,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def daily_log(db: AsyncSession, day: date | None = None) -> DailyFoodLog:
    log_date = day or date.today()
    entries = list(
        await db.scalars(select(FoodLog).where(FoodLog.date == log_date).order_by(FoodLog.id))
    )
    target = await db.scalar(
        select(NutritionTarget)
        .where(NutritionTarget.date <= log_date)
        .order_by(NutritionTarget.date.desc(), NutritionTarget.id.desc())
        .limit(1)
    )
    return DailyFoodLog(
        date=log_date,
        entries=entries,
        totals=_totals(entries),
        target=target,
    )


async def delete_entry(db: AsyncSession, entry_id: int) -> date:
    entry = await db.get(FoodLog, entry_id)
    if entry is None:
        raise FoodLogNotFoundError
    log_date = entry.date
    await db.delete(entry)
    await db.commit()
    return log_date


async def recent_foods(db: AsyncSession, *, limit: int = 8) -> list[FoodLog]:
    """Return recently used distinct foods for one-tap relogging.

    Distinctness includes macros and barcode because the same display name can refer to
    different serving sizes or products.
    """
    rows = list(
        await db.scalars(
            select(FoodLog).order_by(FoodLog.created_at.desc(), FoodLog.id.desc()).limit(250)
        )
    )
    seen: set[tuple[object, ...]] = set()
    foods: list[FoodLog] = []
    for row in rows:
        key = (
            row.name.strip().lower(),
            Decimal(row.grams),
            row.kcal,
            Decimal(row.protein_g),
            Decimal(row.carbs_g),
            Decimal(row.fat_g),
            row.barcode or "",
        )
        if key in seen:
            continue
        seen.add(key)
        foods.append(row)
        if len(foods) >= limit:
            break
    return foods


async def copy_day(db: AsyncSession, *, from_date: date, to_date: date) -> list[FoodLog]:
    source_entries = list(
        await db.scalars(select(FoodLog).where(FoodLog.date == from_date).order_by(FoodLog.id))
    )
    if not source_entries:
        raise FoodLogSourceDayEmptyError

    copied = [
        FoodLog(
            date=to_date,
            name=entry.name,
            grams=entry.grams,
            kcal=entry.kcal,
            protein_g=entry.protein_g,
            carbs_g=entry.carbs_g,
            fat_g=entry.fat_g,
            source=entry.source,
            barcode=entry.barcode,
        )
        for entry in source_entries
    ]
    db.add_all(copied)
    await db.commit()
    for entry in copied:
        await db.refresh(entry)
    return copied


async def daily_intake_kcals(
    db: AsyncSession,
    *,
    since: date,
    until: date,
    fallback_target_kcal: int,
) -> list[int]:
    """Return one kcal value per day, preferring measured food logs over targets.

    A logged day uses the food-log total. Unlogged days use the latest target in effect;
    if no persisted target exists yet, the static target is the fallback.
    """
    log_rows = await db.execute(
        select(FoodLog.date, func.sum(FoodLog.kcal))
        .where(FoodLog.date >= since, FoodLog.date <= until)
        .group_by(FoodLog.date)
    )
    logged_by_date = {row[0]: int(row[1]) for row in log_rows}

    targets = list(
        await db.scalars(
            select(NutritionTarget)
            .where(NutritionTarget.date <= until)
            .order_by(NutritionTarget.date)
        )
    )
    target_by_date: dict[date, int] = {target.date: target.target_kcal for target in targets}

    intakes: list[int] = []
    latest_target = fallback_target_kcal
    for day in _date_range(since, until):
        if day in target_by_date:
            latest_target = target_by_date[day]
        intakes.append(logged_by_date.get(day, latest_target))
    return intakes


def _totals(entries: list[FoodLog]) -> FoodLogTotals:
    totals = defaultdict(Decimal)
    kcal = 0
    for entry in entries:
        kcal += entry.kcal
        totals["protein_g"] += Decimal(entry.protein_g)
        totals["carbs_g"] += Decimal(entry.carbs_g)
        totals["fat_g"] += Decimal(entry.fat_g)
    return FoodLogTotals(
        kcal=kcal,
        protein_g=totals["protein_g"],
        carbs_g=totals["carbs_g"],
        fat_g=totals["fat_g"],
    )


def _date_range(since: date, until: date) -> list[date]:
    days = (until - since).days
    if days < 0:
        return []
    return [since + timedelta(days=offset) for offset in range(days + 1)]
