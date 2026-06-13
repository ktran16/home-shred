from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, enum_col
from app.enums import Focus, Goal, Level

if TYPE_CHECKING:
    from app.models.exercise import Exercise


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    goal: Mapped[Goal] = mapped_column(enum_col(Goal), nullable=False)
    days_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    experience_level: Mapped[Level] = mapped_column(enum_col(Level), nullable=False)
    # only one active at a time (enforced in service, SPEC §5).
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    days: Mapped[list["PlanDay"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="PlanDay.day_index"
    )

    __table_args__ = (
        CheckConstraint("days_per_week >= 3 AND days_per_week <= 5", name="ck_plans_days"),
    )


class PlanDay(Base):
    __tablename__ = "plan_days"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-based
    focus: Mapped[Focus] = mapped_column(enum_col(Focus), nullable=False)

    plan: Mapped["Plan"] = relationship(back_populates="days")
    exercises: Mapped[list["PlanExercise"]] = relationship(
        back_populates="plan_day",
        cascade="all, delete-orphan",
        order_by="PlanExercise.order_index",
    )

    __table_args__ = (UniqueConstraint("plan_id", "day_index", name="uq_plan_days_plan_day"),)


class PlanExercise(Base):
    __tablename__ = "plan_exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_day_id: Mapped[int] = mapped_column(
        ForeignKey("plan_days.id", ondelete="CASCADE"), index=True, nullable=False
    )
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    target_reps_min: Mapped[int] = mapped_column(Integer, nullable=False)
    target_reps_max: Mapped[int] = mapped_column(Integer, nullable=False)
    rest_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    is_conditioning: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    plan_day: Mapped["PlanDay"] = relationship(back_populates="exercises")
    exercise: Mapped["Exercise"] = relationship()
