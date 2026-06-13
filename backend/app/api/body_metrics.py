from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.metrics import BodyMetricIn, BodyMetricOut
from app.services import metrics as svc

router = APIRouter(prefix="/body-metrics", tags=["body-metrics"])


@router.post("", response_model=BodyMetricOut, status_code=201)
async def create_body_metric(
    data: BodyMetricIn, db: AsyncSession = Depends(get_db)
) -> BodyMetricOut:
    metric = await svc.upsert_body_metric(db, data)
    return BodyMetricOut.model_validate(metric)


@router.get("", response_model=list[BodyMetricOut])
async def list_body_metrics(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
) -> list[BodyMetricOut]:
    rows = await svc.list_body_metrics(db, date_from=date_from, date_to=date_to)
    return [BodyMetricOut.model_validate(r) for r in rows]
