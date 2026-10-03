"""Meal / recipe templates (SPEC §19.9 N2).

A template is a named list of foods with macros frozen at save time. Logging one clones
every item into `food_log` as ordinary rows (multi-row), so per-item delete, adaptive
TDEE (§17.3 A1) and history/adherence keep reading the same table — exactly what
copy-day already does.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import FoodLog, MealTemplate, MealTemplateItem
from app.schemas.nutrition import (
    TEMPLATE_SCALE_MAX,
    TEMPLATE_SCALE_MIN,
    FoodItemIn,
    FoodLogIn,
)
from app.services import food_log

_ONE_DP = Decimal("0.1")


class DuplicateMealTemplateError(Exception):
    """A template with this name (case-insensitive) already exists."""


class EmptyMealTemplateError(Exception):
    """A template needs at least one item."""


class MealTemplateNotFoundError(Exception):
    """No meal template with the given id."""


class MealTemplateScaleError(Exception):
    """Scale out of range, or a scaled item falls outside the food-log limits."""


async def list_templates(db: AsyncSession) -> list[MealTemplate]:
    stmt = (
        select(MealTemplate)
        .options(selectinload(MealTemplate.items))
        .order_by(func.lower(MealTemplate.name))
    )
    return list(await db.scalars(stmt))


async def get_template(db: AsyncSession, template_id: int) -> MealTemplate:
    template = await db.scalar(
        select(MealTemplate)
        .options(selectinload(MealTemplate.items))
        .where(MealTemplate.id == template_id)
        .execution_options(populate_existing=True)
    )
    if template is None:
        raise MealTemplateNotFoundError
    return template


async def create_template(db: AsyncSession, name: str, items: list[FoodItemIn]) -> MealTemplate:
    name = name.strip()
    if not items:
        raise EmptyMealTemplateError
    duplicate = await db.scalar(
        select(MealTemplate.id).where(func.lower(MealTemplate.name) == func.lower(name))
    )
    if duplicate is not None:
        raise DuplicateMealTemplateError

    template = MealTemplate(
        name=name,
        items=[
            MealTemplateItem(
                position=position,
                name=item.name,
                grams=item.grams,
                kcal=item.kcal,
                protein_g=item.protein_g,
                carbs_g=item.carbs_g,
                fat_g=item.fat_g,
                source=item.source,
                barcode=item.barcode,
            )
            for position, item in enumerate(items)
        ],
    )
    db.add(template)
    await db.commit()
    return await get_template(db, template.id)


async def create_from_day(db: AsyncSession, name: str, day: date) -> MealTemplate:
    """Snapshot one day's food log as a template (same empty-day contract as copy-day)."""
    entries = list(
        await db.scalars(select(FoodLog).where(FoodLog.date == day).order_by(FoodLog.id))
    )
    if not entries:
        raise food_log.FoodLogSourceDayEmptyError
    items = [FoodItemIn.model_validate(entry, from_attributes=True) for entry in entries]
    return await create_template(db, name, items)


async def log_template(
    db: AsyncSession,
    template_id: int,
    day: date | None = None,
    scale: Decimal = Decimal("1"),
) -> list[FoodLog]:
    """Clone every item into the food log with grams/macros × scale, in one transaction.

    Each scaled item goes through `FoodLogIn`, so the usual food-log limits apply.
    """
    if not TEMPLATE_SCALE_MIN <= scale <= TEMPLATE_SCALE_MAX:
        raise MealTemplateScaleError(
            f"Scale must be between {TEMPLATE_SCALE_MIN} and {TEMPLATE_SCALE_MAX}"
        )
    template = await get_template(db, template_id)
    log_date = day or date.today()
    try:
        entries = [
            FoodLogIn(
                date=log_date,
                name=item.name,
                # A tiny item scaled down must still satisfy grams > 0.
                grams=max(_scaled(item.grams, scale), _ONE_DP),
                kcal=int((Decimal(item.kcal) * scale).quantize(Decimal(1), ROUND_HALF_UP)),
                protein_g=_scaled(item.protein_g, scale),
                carbs_g=_scaled(item.carbs_g, scale),
                fat_g=_scaled(item.fat_g, scale),
                source=item.source,
                barcode=item.barcode,
            )
            for item in template.items
        ]
    except ValidationError as exc:
        raise MealTemplateScaleError("A scaled item is outside the food-log limits") from exc
    return await food_log.create_entries(db, entries)


async def delete_template(db: AsyncSession, template_id: int) -> None:
    template = await db.get(MealTemplate, template_id)
    if template is None:
        raise MealTemplateNotFoundError
    await db.delete(template)
    await db.commit()


def _scaled(value: float | Decimal, scale: Decimal) -> Decimal:
    return (Decimal(value) * scale).quantize(_ONE_DP, ROUND_HALF_UP)
