from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import Focus, Goal, Level
from app.schemas.exercise import ExerciseOut


class PlanCreateIn(BaseModel):
    goal: Goal = Goal.SHRED
    days_per_week: int = Field(ge=3, le=5)
    # mesocycle week to generate (SPEC §16 R2/R5): periodises volume + rotates exercises.
    week: int = Field(default=1, ge=1, le=52)


class PlanExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    exercise_id: int
    order_index: int
    sets: int
    target_reps_min: int
    target_reps_max: int
    rest_seconds: int
    is_conditioning: bool
    exercise: ExerciseOut


class PlanDayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    day_index: int
    focus: Focus
    exercises: list[PlanExerciseOut]


class PlanSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    goal: Goal
    days_per_week: int
    experience_level: Level
    mesocycle_week: int
    is_active: bool
    created_at: datetime


class PlanDetailOut(PlanSummaryOut):
    days: list[PlanDayOut]


class CoveragePointOut(BaseModel):
    muscle: str
    sets: float
    target: int
    met: bool


class DayFatigueOut(BaseModel):
    day_index: int
    focus: Focus
    fatigue: float
