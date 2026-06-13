from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.exercise import Exercise


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_day_id: Mapped[int | None] = mapped_column(ForeignKey("plan_days.id"), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    set_logs: Mapped[list["SetLog"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="SetLog.id"
    )


class SetLog(Base):
    __tablename__ = "set_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("workout_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), nullable=False)
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-based
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    # null = pure bodyweight (SPEC §5).
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    rpe: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)  # 1–10

    session: Mapped["WorkoutSession"] = relationship(back_populates="set_logs")
    exercise: Mapped["Exercise"] = relationship()
