from datetime import datetime

from sqlalchemy import DateTime, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Food(Base):
    """Local cache of foods discovered via Open Food Facts text search (SPEC §19.8 W2).

    Keyed on the OFF barcode so repeat searches are served offline and fast. Macros are
    per 100 g (same convention as the barcode lookup / `FoodFactsOut`).
    """

    __tablename__ = "foods"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    brand: Mapped[str | None] = mapped_column(Text, nullable=True)
    kcal_per_100g: Mapped[float | None] = mapped_column(Numeric(7, 1), nullable=True)
    protein_per_100g: Mapped[float | None] = mapped_column(Numeric(7, 1), nullable=True)
    carbs_per_100g: Mapped[float | None] = mapped_column(Numeric(7, 1), nullable=True)
    fat_per_100g: Mapped[float | None] = mapped_column(Numeric(7, 1), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
