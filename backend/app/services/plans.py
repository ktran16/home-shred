"""Plan persistence: generate a draft, persist it, and manage the single active plan."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums import Equipment, Goal
from app.models import Exercise, Plan, PlanDay, PlanExercise
from app.services.plan_generator import (
    CoveragePoint,
    DayFatigue,
    coverage_report,
    fatigue_report,
    generate_plan,
    scaled_set_targets,
)
from app.services.profile import get_profile

# SPEC §1 hard constraint: the only available equipment.
AVAILABLE_EQUIPMENT: set[Equipment] = {
    Equipment.BODYWEIGHT,
    Equipment.DUMBBELL,
    Equipment.PULL_UP_BAR,
}


class NoProfileError(Exception):
    """Raised when generating a plan without a profile (router → 409)."""


_PLAN_LOADERS = (
    selectinload(Plan.days).selectinload(PlanDay.exercises).selectinload(PlanExercise.exercise),
)


async def _load_plan(db: AsyncSession, plan_id: int) -> Plan | None:
    stmt = select(Plan).where(Plan.id == plan_id).options(*_PLAN_LOADERS)
    return await db.scalar(stmt)


async def create_plan(
    db: AsyncSession, *, days_per_week: int, goal: Goal = Goal.SHRED, week: int = 1
) -> Plan:
    profile = await get_profile(db)
    if profile is None:
        raise NoProfileError

    exercises = list((await db.scalars(select(Exercise))).all())
    draft = generate_plan(
        goal=goal,
        days_per_week=days_per_week,
        level=profile.experience_level,
        available_equipment=AVAILABLE_EQUIPMENT,
        exercises=exercises,
        age=profile.age,  # age-based recovery/volume adjustment (SPEC §16 R7)
        week=week,  # periodisation + rotation (SPEC §16 R2/R5)
    )

    # Only one active plan at a time (SPEC §5).
    await db.execute(update(Plan).where(Plan.is_active.is_(True)).values(is_active=False))

    plan = Plan(
        name=draft.name,
        goal=draft.goal,
        days_per_week=draft.days_per_week,
        experience_level=draft.experience_level,
        mesocycle_week=week,
        is_active=True,
    )
    for day_draft in draft.days:
        day = PlanDay(day_index=day_draft.day_index, focus=day_draft.focus)
        for pe in day_draft.exercises:
            day.exercises.append(
                PlanExercise(
                    exercise_id=pe.exercise_id,
                    order_index=pe.order_index,
                    sets=pe.sets,
                    target_reps_min=pe.target_reps_min,
                    target_reps_max=pe.target_reps_max,
                    rest_seconds=pe.rest_seconds,
                    is_conditioning=pe.is_conditioning,
                )
            )
        plan.days.append(day)

    db.add(plan)
    await db.commit()
    loaded = await _load_plan(db, plan.id)
    assert loaded is not None
    return loaded


async def list_plans(db: AsyncSession) -> list[Plan]:
    stmt = select(Plan).order_by(Plan.created_at.desc())
    return list((await db.scalars(stmt)).all())


async def get_plan(db: AsyncSession, plan_id: int) -> Plan | None:
    return await _load_plan(db, plan_id)


async def plan_coverage(db: AsyncSession, plan_id: int) -> list[CoveragePoint] | None:
    """Weekly set-volume coverage report for a persisted plan (SPEC §16 R1)."""
    plan = await _load_plan(db, plan_id)
    if plan is None:
        return None
    # ORM Plan/PlanDay/PlanExercise/Exercise are duck-compatible with the draft types.
    ex_by_id = {pe.exercise_id: pe.exercise for day in plan.days for pe in day.exercises}
    profile = await get_profile(db)
    targets = scaled_set_targets(profile.age if profile else None, plan.mesocycle_week)  # §16 R7/R2
    return coverage_report(plan, ex_by_id, targets)  # type: ignore[arg-type]


async def plan_fatigue(db: AsyncSession, plan_id: int) -> list[DayFatigue] | None:
    """Per-day fatigue score for a persisted plan (SPEC §16 R6)."""
    plan = await _load_plan(db, plan_id)
    if plan is None:
        return None
    ex_by_id = {pe.exercise_id: pe.exercise for day in plan.days for pe in day.exercises}
    return fatigue_report(plan, ex_by_id)  # type: ignore[arg-type]


async def activate_plan(db: AsyncSession, plan_id: int) -> Plan | None:
    plan = await db.get(Plan, plan_id)
    if plan is None:
        return None
    await db.execute(update(Plan).where(Plan.is_active.is_(True)).values(is_active=False))
    plan.is_active = True
    await db.commit()
    return await _load_plan(db, plan_id)
