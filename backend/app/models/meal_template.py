from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, enum_col
from app.enums import FoodLogSource


class MealTemplate(Base):
    """A named combination of foods logged in one tap (SPEC §19.9 N2)."""

    __tablename__ = "meal_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["MealTemplateItem"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        passive_deletes=True,  # rows go via the FK's ON DELETE CASCADE
        order_by="MealTemplateItem.position",
    )

    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_meal_templates_name_nonempty"),
        Index("uq_meal_templates_name_lower", func.lower(name), unique=True),
    )


class MealTemplateItem(Base):
    """One food in a template. Macros are frozen at save time, never re-derived, so a
    template does not drift when Open Food Facts data changes."""

    __tablename__ = "meal_template_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("meal_templates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    grams: Mapped[float] = mapped_column(Numeric(7, 1), nullable=False)
    kcal: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_g: Mapped[float] = mapped_column(Numeric(7, 1), nullable=False)
    carbs_g: Mapped[float] = mapped_column(Numeric(7, 1), nullable=False)
    fat_g: Mapped[float] = mapped_column(Numeric(7, 1), nullable=False)
    source: Mapped[FoodLogSource] = mapped_column(enum_col(FoodLogSource), nullable=False)
    barcode: Mapped[str | None] = mapped_column(Text, nullable=True)

    template: Mapped["MealTemplate"] = relationship(back_populates="items")

    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_meal_template_items_name_nonempty"),
        CheckConstraint("grams > 0", name="ck_meal_template_items_grams_positive"),
        CheckConstraint("kcal >= 0", name="ck_meal_template_items_kcal_nonnegative"),
        CheckConstraint("protein_g >= 0", name="ck_meal_template_items_protein_nonnegative"),
        CheckConstraint("carbs_g >= 0", name="ck_meal_template_items_carbs_nonnegative"),
        CheckConstraint("fat_g >= 0", name="ck_meal_template_items_fat_nonnegative"),
    )
