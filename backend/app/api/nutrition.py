from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.nutrition import NutritionTargetOut
from app.services import nutrition as svc

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.get("/targets", response_model=NutritionTargetOut)
async def get_targets(db: AsyncSession = Depends(get_db)) -> NutritionTargetOut:
    target = await svc.latest(db)
    if target is None:
        raise HTTPException(status_code=404, detail="No nutrition targets yet")
    return NutritionTargetOut.model_validate(target)


@router.post("/recompute", response_model=NutritionTargetOut)
async def recompute(db: AsyncSession = Depends(get_db)) -> NutritionTargetOut:
    target = await svc.recompute(db)
    if target is None:
        raise HTTPException(status_code=409, detail="Set a profile before computing nutrition")
    return NutritionTargetOut.model_validate(target)
