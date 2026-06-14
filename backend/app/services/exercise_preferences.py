from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import ExercisePreferenceStatus
from app.models import ExercisePreference


async def preference_map(
    db: AsyncSession, exercise_ids: list[int]
) -> dict[int, ExercisePreferenceStatus]:
    if not exercise_ids:
        return {}
    stmt = select(ExercisePreference).where(ExercisePreference.exercise_id.in_(exercise_ids))
    rows = (await db.scalars(stmt)).all()
    return {row.exercise_id: row.status for row in rows}


async def avoided_exercise_ids(db: AsyncSession) -> set[int]:
    stmt = select(ExercisePreference.exercise_id).where(
        ExercisePreference.status == ExercisePreferenceStatus.AVOID
    )
    return set((await db.scalars(stmt)).all())


async def set_preference(
    db: AsyncSession, exercise_id: int, status: ExercisePreferenceStatus
) -> ExercisePreference:
    preference = await db.get(ExercisePreference, exercise_id)
    if preference is None:
        preference = ExercisePreference(exercise_id=exercise_id, status=status)
        db.add(preference)
    else:
        preference.status = status
    await db.commit()
    await db.refresh(preference)
    return preference


async def clear_preference(db: AsyncSession, exercise_id: int) -> None:
    await db.execute(
        delete(ExercisePreference).where(ExercisePreference.exercise_id == exercise_id)
    )
    await db.commit()
