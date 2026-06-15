"""add custom body measurements (W1)

Revision ID: d1e2f3a4b5c6
Revises: c6b8e6f8d9a1
Create Date: 2026-06-15 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: str | None = "c6b8e6f8d9a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Built-in measurement types seeded on upgrade (must mirror
# app.services.measurements.BUILTIN_MEASUREMENT_TYPES).
_BUILTIN_TYPES = [
    ("chest", "Chest", "cm"),
    ("shoulders", "Shoulders", "cm"),
    ("hips", "Hips", "cm"),
    ("left_arm", "Left arm", "cm"),
    ("right_arm", "Right arm", "cm"),
    ("left_thigh", "Left thigh", "cm"),
    ("right_thigh", "Right thigh", "cm"),
    ("calf", "Calf", "cm"),
    ("neck", "Neck", "cm"),
]


def upgrade() -> None:
    measurement_types = op.create_table(
        "measurement_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=False),
        sa.Column(
            "builtin", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_measurement_types_key"), "measurement_types", ["key"], unique=True
    )

    op.create_table(
        "measurement_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(precision=7, scale=2), nullable=False),
        sa.ForeignKeyConstraint(
            ["type_id"], ["measurement_types.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("type_id", "date", name="uq_measurement_entry_type_date"),
    )
    op.create_index(
        op.f("ix_measurement_entries_type_id"),
        "measurement_entries",
        ["type_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_measurement_entries_date"), "measurement_entries", ["date"], unique=False
    )

    op.bulk_insert(
        measurement_types,
        [
            {"key": key, "label": label, "unit": unit, "builtin": True}
            for key, label, unit in _BUILTIN_TYPES
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_measurement_entries_date"), table_name="measurement_entries")
    op.drop_index(
        op.f("ix_measurement_entries_type_id"), table_name="measurement_entries"
    )
    op.drop_table("measurement_entries")
    op.drop_index(op.f("ix_measurement_types_key"), table_name="measurement_types")
    op.drop_table("measurement_types")
