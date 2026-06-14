from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.nutrition import AdaptiveTDEEOut, NutritionTargetOut, SuggestedTargets
from app.services import nutrition as svc
from app.services.nutrition import ADAPTIVE_MIN_DAYS_SPAN, ADAPTIVE_MIN_SAMPLES
from app.services.profile import get_profile

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


@router.get("/adaptive", response_model=AdaptiveTDEEOut)
async def adaptive(db: AsyncSession = Depends(get_db)) -> AdaptiveTDEEOut:
    """Adaptive TDEE preview from the bodyweight trend (SPEC §17.3 A1)."""
    if await get_profile(db) is None:
        raise HTTPException(status_code=404, detail="Profile not set")
    est = await svc.adaptive_targets(db)
    if est is None:
        return AdaptiveTDEEOut(
            enough_data=False,
            reason=(
                f"Need at least {ADAPTIVE_MIN_SAMPLES} weigh-ins spanning "
                f"{ADAPTIVE_MIN_DAYS_SPAN}+ days in the last 4 weeks."
            ),
        )
    return AdaptiveTDEEOut(
        enough_data=True,
        samples=est.samples,
        days_span=est.days_span,
        static_tdee_kcal=est.static_tdee_kcal,
        estimated_tdee_kcal=est.estimated_tdee_kcal,
        assumed_intake_kcal=est.assumed_intake_kcal,
        weight_change_kg_per_week=est.weight_change_kg_per_week,
        clamped=est.clamped,
        suggested=SuggestedTargets(
            target_kcal=est.targets.target_kcal,
            protein_g=est.targets.protein_g,
            carbs_g=est.targets.carbs_g,
            fat_g=est.targets.fat_g,
        ),
    )


@router.post("/adaptive/apply", response_model=NutritionTargetOut)
async def apply_adaptive(db: AsyncSession = Depends(get_db)) -> NutritionTargetOut:
    """Persist today's targets from the adaptive TDEE estimate (SPEC §17.3 A1)."""
    if await get_profile(db) is None:
        raise HTTPException(status_code=409, detail="Set a profile before computing nutrition")
    target = await svc.apply_adaptive(db)
    if target is None:
        raise HTTPException(status_code=409, detail="Not enough bodyweight history to adapt yet")
    return NutritionTargetOut.model_validate(target)
