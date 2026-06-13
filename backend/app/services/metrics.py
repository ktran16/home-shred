"""Body metrics: upsert a dated measurement, list by range."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BodyMetric
from app.schemas.metrics import BodyMetricIn


async def upsert_body_metric(db: AsyncSession, data: BodyMetricIn) -> BodyMetric:
    values = data.model_dump()
    values["date"] = values.get("date") or date.today()
    stmt = (
        pg_insert(BodyMetric)
        .values(**values)
        .on_conflict_do_update(
            index_elements=[BodyMetric.date],
            set_={k: values[k] for k in values if k != "date"},
        )
        .returning(BodyMetric)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()


async def list_body_metrics(
    db: AsyncSession, *, date_from: date | None = None, date_to: date | None = None
) -> list[BodyMetric]:
    stmt = select(BodyMetric)
    if date_from is not None:
        stmt = stmt.where(BodyMetric.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(BodyMetric.date <= date_to)
    stmt = stmt.order_by(BodyMetric.date)
    return list((await db.scalars(stmt)).all())
