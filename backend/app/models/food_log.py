from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, enum_col
from app.enums import FoodLogSource


class FoodLog(Base):
    __tablename__ = "food_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    grams: Mapped[float] = mapped_column(Numeric(7, 1), nullable=False)
    kcal: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_g: Mapped[float] = mapped_column(Numeric(7, 1), nullable=False)
    carbs_g: Mapped[float] = mapped_column(Numeric(7, 1), nullable=False)
    fat_g: Mapped[float] = mapped_column(Numeric(7, 1), nullable=False)
    source: Mapped[FoodLogSource] = mapped_column(
        enum_col(FoodLogSource), nullable=False, index=True
    )
    barcode: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_food_log_name_nonempty"),
        CheckConstraint("grams > 0", name="ck_food_log_grams_positive"),
        CheckConstraint("kcal >= 0", name="ck_food_log_kcal_nonnegative"),
        CheckConstraint("protein_g >= 0", name="ck_food_log_protein_nonnegative"),
        CheckConstraint("carbs_g >= 0", name="ck_food_log_carbs_nonnegative"),
        CheckConstraint("fat_g >= 0", name="ck_food_log_fat_nonnegative"),
    )
