from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.enums import Equipment, ExercisePreferenceStatus, Level, MovementPattern


class ExercisePreferenceIn(BaseModel):
    status: ExercisePreferenceStatus


class ExercisePreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exercise_id: int
    status: ExercisePreferenceStatus
    updated_at: datetime


class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    equipment: Equipment
    pattern: MovementPattern | None
    category: str | None
    primary_muscles: list[str]
    secondary_muscles: list[str]
    level: Level | None
    is_compound: bool
    instructions: list[str]
    preference: ExercisePreferenceStatus | None = None


class ExerciseSearchHitOut(BaseModel):
    score: float
    exercise: ExerciseOut


class HistorySetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    set_number: int
    reps: int
    weight_kg: Decimal | None
    rpe: Decimal | None


class HistorySessionOut(BaseModel):
    session_id: int
    date: date_type
    sets: list[HistorySetOut]


class ExerciseHistoryOut(BaseModel):
    exercise_id: int
    sessions: list[HistorySessionOut]
