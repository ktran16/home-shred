from sqlalchemy import Boolean, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, enum_col
from app.enums import Equipment, Level, MovementPattern


class Exercise(Base):
    """Seeded, read-mostly catalogue of exercises (SPEC §5)."""

    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    equipment: Mapped[Equipment] = mapped_column(enum_col(Equipment), nullable=False, index=True)
    # nullable: filled by the curation step in seed (SPEC §5).
    pattern: Mapped[MovementPattern | None] = mapped_column(
        enum_col(MovementPattern), nullable=True
    )
    # push|pull|legs|core|conditioning
    category: Mapped[str | None] = mapped_column(String(32), index=True)
    primary_muscles: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    secondary_muscles: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default="{}"
    )
    level: Mapped[Level | None] = mapped_column(enum_col(Level), nullable=True)
    is_compound: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # fraction of bodyweight that loads the prime movers, for the volume proxy of
    # bodyweight exercises (SPEC §16 R4). 1.0 for weighted/uncurated exercises.
    bodyweight_load_factor: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0, server_default="1.0"
    )
    instructions: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default="{}"
    )

    __table_args__ = (Index("ix_exercises_pattern", "pattern"),)
