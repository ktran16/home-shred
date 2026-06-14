from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.plan import (
    CoveragePointOut,
    DayFatigueOut,
    PlanCreateIn,
    PlanDetailOut,
    PlanSummaryOut,
)
from app.services import plans as svc
from app.services.plans import NoProfileError

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("", response_model=PlanDetailOut, status_code=201)
async def create_plan(data: PlanCreateIn, db: AsyncSession = Depends(get_db)) -> PlanDetailOut:
    try:
        plan = await svc.create_plan(
            db, days_per_week=data.days_per_week, goal=data.goal, week=data.week
        )
    except NoProfileError as exc:
        raise HTTPException(
            status_code=409, detail="Set a profile before generating a plan"
        ) from exc
    return PlanDetailOut.model_validate(plan)


@router.get("", response_model=list[PlanSummaryOut])
async def list_plans(db: AsyncSession = Depends(get_db)) -> list[PlanSummaryOut]:
    return [PlanSummaryOut.model_validate(p) for p in await svc.list_plans(db)]


@router.get("/{plan_id}", response_model=PlanDetailOut)
async def get_plan(plan_id: int, db: AsyncSession = Depends(get_db)) -> PlanDetailOut:
    plan = await svc.get_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return PlanDetailOut.model_validate(plan)


@router.get("/{plan_id}/coverage", response_model=list[CoveragePointOut])
async def plan_coverage(plan_id: int, db: AsyncSession = Depends(get_db)) -> list[CoveragePointOut]:
    report = await svc.plan_coverage(db, plan_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return [
        CoveragePointOut(muscle=c.muscle, sets=c.sets, target=c.target, met=c.met) for c in report
    ]


@router.get("/{plan_id}/fatigue", response_model=list[DayFatigueOut])
async def plan_fatigue(plan_id: int, db: AsyncSession = Depends(get_db)) -> list[DayFatigueOut]:
    report = await svc.plan_fatigue(db, plan_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return [DayFatigueOut(day_index=d.day_index, focus=d.focus, fatigue=d.fatigue) for d in report]


@router.patch("/{plan_id}/activate", response_model=PlanSummaryOut)
async def activate_plan(plan_id: int, db: AsyncSession = Depends(get_db)) -> PlanSummaryOut:
    plan = await svc.activate_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return PlanSummaryOut.model_validate(plan)
