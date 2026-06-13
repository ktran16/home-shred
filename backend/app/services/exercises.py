from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import Equipment, MovementPattern
from app.models import Exercise


async def list_exercises(
    db: AsyncSession,
    *,
    equipment: Equipment | None = None,
    muscle: str | None = None,
    category: str | None = None,
    pattern: MovementPattern | None = None,
) -> list[Exercise]:
    stmt = select(Exercise).order_by(Exercise.name)
    if equipment is not None:
        stmt = stmt.where(Exercise.equipment == equipment)
    if category is not None:
        stmt = stmt.where(Exercise.category == category)
    if pattern is not None:
        stmt = stmt.where(Exercise.pattern == pattern)
    if muscle is not None:
        # muscle matches either primary or secondary muscle arrays.
        stmt = stmt.where(
            Exercise.primary_muscles.any(muscle) | Exercise.secondary_muscles.any(muscle)
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_exercise(db: AsyncSession, exercise_id: int) -> Exercise | None:
    return await db.get(Exercise, exercise_id)
