from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SessionCreateIn(BaseModel):
    plan_day_id: int
    date: date_type | None = None


class SetLogIn(BaseModel):
    exercise_id: int
    set_number: int = Field(ge=1)
    reps: int = Field(ge=0)
    weight_kg: Decimal | None = Field(default=None, ge=0)
    rpe: Decimal | None = Field(default=None, ge=1, le=10)


class SetLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    exercise_id: int
    set_number: int
    reps: int
    weight_kg: Decimal | None
    rpe: Decimal | None


class SuggestedTargetOut(BaseModel):
    exercise_id: int
    sets: int
    reps_min: int
    reps_max: int
    suggested_weight_kg: float | None


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_day_id: int | None
    date: date_type
    notes: str | None
    completed: bool
    created_at: datetime
    set_logs: list[SetLogOut] = []
    # Populated on session creation (SPEC §10 POST /sessions).
    suggested_targets: list[SuggestedTargetOut] = []
