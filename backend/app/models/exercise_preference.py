from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, enum_col
from app.enums import ExercisePreferenceStatus


class ExercisePreference(Base):
    """Global exercise preferences used by planning and substitutions."""

    __tablename__ = "exercise_preferences"

    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[ExercisePreferenceStatus] = mapped_column(
        enum_col(ExercisePreferenceStatus), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
