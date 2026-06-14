"""ORM models. Import all here so Alembic's metadata sees every table."""

from app.models.exercise import Exercise
from app.models.exercise_preference import ExercisePreference
from app.models.metrics import BodyMetric, NutritionTarget
from app.models.plan import Plan, PlanDay, PlanExercise
from app.models.profile import UserProfile
from app.models.session import SetLog, WorkoutSession

__all__ = [
    "Exercise",
    "ExercisePreference",
    "UserProfile",
    "Plan",
    "PlanDay",
    "PlanExercise",
    "WorkoutSession",
    "SetLog",
    "BodyMetric",
    "NutritionTarget",
]
