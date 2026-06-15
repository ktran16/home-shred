from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class MeasurementType(Base):
    """A user-extensible body measurement (chest, arms, …) — SPEC §19.8 W1.

    Complements the fixed `body_metrics` columns (weight/body_fat/waist), which the
    §8 nutrition engine depends on and are deliberately *not* modelled here.
    """

    __tablename__ = "measurement_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(Text, unique=True, index=True, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str] = mapped_column(Text, nullable=False, default="cm")
    builtin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    entries: Mapped[list["MeasurementEntry"]] = relationship(
        back_populates="type",
        cascade="all, delete-orphan",
        order_by="MeasurementEntry.date",
    )


class MeasurementEntry(Base):
    __tablename__ = "measurement_entries"
    __table_args__ = (
        UniqueConstraint("type_id", "date", name="uq_measurement_entry_type_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    type_id: Mapped[int] = mapped_column(
        ForeignKey("measurement_types.id", ondelete="CASCADE"), index=True, nullable=False
    )
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    value: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False)

    type: Mapped["MeasurementType"] = relationship(back_populates="entries")
