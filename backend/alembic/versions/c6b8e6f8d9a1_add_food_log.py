"""add food log

Revision ID: c6b8e6f8d9a1
Revises: 2a7d9dfac116
Create Date: 2026-06-15 10:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c6b8e6f8d9a1"
down_revision: str | None = "2a7d9dfac116"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "food_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("grams", sa.Numeric(precision=7, scale=1), nullable=False),
        sa.Column("kcal", sa.Integer(), nullable=False),
        sa.Column("protein_g", sa.Numeric(precision=7, scale=1), nullable=False),
        sa.Column("carbs_g", sa.Numeric(precision=7, scale=1), nullable=False),
        sa.Column("fat_g", sa.Numeric(precision=7, scale=1), nullable=False),
        sa.Column(
            "source",
            sa.Enum("manual", "barcode", "llm", name="foodlogsource", native_enum=False),
            nullable=False,
        ),
        sa.Column("barcode", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_food_log_name_nonempty"),
        sa.CheckConstraint("grams > 0", name="ck_food_log_grams_positive"),
        sa.CheckConstraint("kcal >= 0", name="ck_food_log_kcal_nonnegative"),
        sa.CheckConstraint("protein_g >= 0", name="ck_food_log_protein_nonnegative"),
        sa.CheckConstraint("carbs_g >= 0", name="ck_food_log_carbs_nonnegative"),
        sa.CheckConstraint("fat_g >= 0", name="ck_food_log_fat_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_food_log_date"), "food_log", ["date"], unique=False)
    op.create_index(op.f("ix_food_log_source"), "food_log", ["source"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_food_log_source"), table_name="food_log")
    op.drop_index(op.f("ix_food_log_date"), table_name="food_log")
    op.drop_table("food_log")
