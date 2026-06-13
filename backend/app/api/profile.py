from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.profile import ProfileIn, ProfileOut
from app.services import nutrition as nutrition_svc
from app.services import profile as svc

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
async def get_profile(db: AsyncSession = Depends(get_db)) -> ProfileOut:
    profile = await svc.get_profile(db)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not set")
    return ProfileOut.model_validate(profile)


@router.put("", response_model=ProfileOut)
async def put_profile(data: ProfileIn, db: AsyncSession = Depends(get_db)) -> ProfileOut:
    profile = await svc.upsert_profile(db, data)
    # Recompute nutrition targets on profile change (SPEC §8).
    await nutrition_svc.recompute(db)
    return ProfileOut.model_validate(profile)
