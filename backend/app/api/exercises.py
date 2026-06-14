from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.enums import Equipment, MovementPattern
from app.schemas.exercise import (
    ExerciseHistoryOut,
    ExerciseOut,
    ExercisePreferenceIn,
    ExercisePreferenceOut,
    HistorySessionOut,
)
from app.services import exercise_history as hist_svc
from app.services import exercise_preferences as pref_svc
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
    preferences = await pref_svc.preference_map(db, [row.id for row in rows])
    return [
        ExerciseOut.model_validate(row).model_copy(update={"preference": preferences.get(row.id)})
        for row in rows
    ]


@router.get("/{exercise_id}", response_model=ExerciseOut)
async def get_exercise(exercise_id: int, db: AsyncSession = Depends(get_db)) -> ExerciseOut:
    row = await svc.get_exercise(db, exercise_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    preferences = await pref_svc.preference_map(db, [row.id])
    return ExerciseOut.model_validate(row).model_copy(
        update={"preference": preferences.get(row.id)}
    )


@router.get("/{exercise_id}/history", response_model=ExerciseHistoryOut)
async def get_exercise_history(
    exercise_id: int,
    sessions: int = Query(default=3, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
) -> ExerciseHistoryOut:
    if await svc.get_exercise(db, exercise_id) is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    rows = await hist_svc.recent_history(db, exercise_id, sessions=sessions)
    return ExerciseHistoryOut(
        exercise_id=exercise_id,
        sessions=[
            HistorySessionOut(
                session_id=session.id,
                date=session.date,
                sets=sorted(
                    (log for log in session.set_logs if log.exercise_id == exercise_id),
                    key=lambda log: log.set_number,
                ),
            )
            for session in rows
        ],
    )


@router.put("/{exercise_id}/preference", response_model=ExercisePreferenceOut)
async def put_exercise_preference(
    exercise_id: int,
    data: ExercisePreferenceIn,
    db: AsyncSession = Depends(get_db),
) -> ExercisePreferenceOut:
    row = await svc.get_exercise(db, exercise_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    preference = await pref_svc.set_preference(db, exercise_id, data.status)
    return ExercisePreferenceOut.model_validate(preference)


@router.delete("/{exercise_id}/preference", status_code=204)
async def delete_exercise_preference(
    exercise_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    row = await svc.get_exercise(db, exercise_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    await pref_svc.clear_preference(db, exercise_id)
