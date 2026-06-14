from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, enum_col
from app.enums import ActivityLevel, Level, Sex


class UserProfile(Base):
    """Managed training profile. Exactly one profile should be active."""

    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, default="Default")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    sex: Mapped[Sex] = mapped_column(enum_col(Sex), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    height_cm: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    weight_kg: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    activity_level: Mapped[ActivityLevel] = mapped_column(enum_col(ActivityLevel), nullable=False)
    experience_level: Mapped[Level] = mapped_column(enum_col(Level), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_user_profile_name_nonempty"),
        CheckConstraint("age >= 14 AND age <= 100", name="ck_user_profile_age"),
    )
