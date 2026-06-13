from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.metrics import VolumePoint
from app.services import volume as svc

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/volume", response_model=list[VolumePoint])
async def volume(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
) -> list[VolumePoint]:
    points = await svc.weekly_volume(db, date_from=date_from, date_to=date_to)
    return [VolumePoint(week=p.week, muscle=p.muscle, volume=p.volume) for p in points]
