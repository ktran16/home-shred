from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.profile import ProfileIn, ProfileOut
from app.services import nutrition as nutrition_svc
from app.services import profile as svc
from app.services.profile import LastProfileError, ProfileNotFoundError

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


@router.get("/all", response_model=list[ProfileOut])
async def list_profiles(db: AsyncSession = Depends(get_db)) -> list[ProfileOut]:
    profiles = await svc.list_profiles(db)
    return [ProfileOut.model_validate(p) for p in profiles]


@router.post("", response_model=ProfileOut, status_code=201)
async def create_profile(data: ProfileIn, db: AsyncSession = Depends(get_db)) -> ProfileOut:
    profile = await svc.create_profile(db, data)
    await nutrition_svc.recompute(db)
    return ProfileOut.model_validate(profile)


@router.patch("/{profile_id}/activate", response_model=ProfileOut)
async def activate_profile(profile_id: int, db: AsyncSession = Depends(get_db)) -> ProfileOut:
    try:
        profile = await svc.activate_profile(db, profile_id)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Profile not found") from exc
    await nutrition_svc.recompute(db)
    return ProfileOut.model_validate(profile)


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(profile_id: int, db: AsyncSession = Depends(get_db)) -> None:
    try:
        await svc.delete_profile(db, profile_id)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Profile not found") from exc
    except LastProfileError as exc:
        raise HTTPException(status_code=409, detail="Cannot delete the last profile") from exc
    await nutrition_svc.recompute(db)
