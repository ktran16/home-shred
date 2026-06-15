from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.metrics import ExerciseStrengthOut, LoadPredictionOut, VolumePoint
from app.services import prediction as prediction_svc
from app.services import strength as strength_svc
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


@router.get("/strength", response_model=list[ExerciseStrengthOut])
async def strength(db: AsyncSession = Depends(get_db)) -> list[ExerciseStrengthOut]:
    rows = await strength_svc.exercise_strength(db)
    return [ExerciseStrengthOut.model_validate(r) for r in rows]


@router.get("/prediction", response_model=list[LoadPredictionOut])
async def prediction(db: AsyncSession = Depends(get_db)) -> list[LoadPredictionOut]:
    """Per-exercise next-session load / readiness forecast (SPEC §17.3 A2)."""
    rows = await prediction_svc.exercise_predictions(db)
    return [LoadPredictionOut.model_validate(r) for r in rows]
