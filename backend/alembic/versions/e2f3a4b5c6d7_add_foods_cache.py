"""add foods cache for name search (W2)

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-06-15 13:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2f3a4b5c6d7"
down_revision: str | None = "d1e2f3a4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "foods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("brand", sa.Text(), nullable=True),
        sa.Column("kcal_per_100g", sa.Numeric(precision=7, scale=1), nullable=True),
        sa.Column("protein_per_100g", sa.Numeric(precision=7, scale=1), nullable=True),
        sa.Column("carbs_per_100g", sa.Numeric(precision=7, scale=1), nullable=True),
        sa.Column("fat_per_100g", sa.Numeric(precision=7, scale=1), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_foods_code"), "foods", ["code"], unique=True)
    op.create_index(op.f("ix_foods_name"), "foods", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_foods_name"), table_name="foods")
    op.drop_index(op.f("ix_foods_code"), table_name="foods")
    op.drop_table("foods")
