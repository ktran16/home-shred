from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.enums import Equipment, MovementPattern
from app.schemas.exercise import ExerciseOut
from app.services import exercises as svc

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("", response_model=list[ExerciseOut])
async def list_exercises(
    equipment: Equipment | None = None,
    muscle: str | None = None,
    category: str | None = None,
    pattern: MovementPattern | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[ExerciseOut]:
    rows = await svc.list_exercises(
        db, equipment=equipment, muscle=muscle, category=category, pattern=pattern
    )
    return [ExerciseOut.model_validate(r) for r in rows]


@router.get("/{exercise_id}", response_model=ExerciseOut)
async def get_exercise(exercise_id: int, db: AsyncSession = Depends(get_db)) -> ExerciseOut:
    row = await svc.get_exercise(db, exercise_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return ExerciseOut.model_validate(row)
