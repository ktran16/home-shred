"""add meal templates (N2)

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-10-03 12:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b5c6d7e8f9a0"
down_revision: str | None = "a4b5c6d7e8f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "meal_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_meal_templates_name_nonempty"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_meal_templates_name_lower",
        "meal_templates",
        [sa.text("lower(name)")],
        unique=True,
    )

    op.create_table(
        "meal_template_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("grams", sa.Numeric(precision=7, scale=1), nullable=False),
        sa.Column("kcal", sa.Integer(), nullable=False),
        sa.Column("protein_g", sa.Numeric(precision=7, scale=1), nullable=False),
        sa.Column("carbs_g", sa.Numeric(precision=7, scale=1), nullable=False),
        sa.Column("fat_g", sa.Numeric(precision=7, scale=1), nullable=False),
        sa.Column(
            "source",
            sa.Enum("manual", "barcode", "llm", name="foodlogsource", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("barcode", sa.Text(), nullable=True),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_meal_template_items_name_nonempty"),
        sa.CheckConstraint("grams > 0", name="ck_meal_template_items_grams_positive"),
        sa.CheckConstraint("kcal >= 0", name="ck_meal_template_items_kcal_nonnegative"),
        sa.CheckConstraint("protein_g >= 0", name="ck_meal_template_items_protein_nonnegative"),
        sa.CheckConstraint("carbs_g >= 0", name="ck_meal_template_items_carbs_nonnegative"),
        sa.CheckConstraint("fat_g >= 0", name="ck_meal_template_items_fat_nonnegative"),
        sa.ForeignKeyConstraint(["template_id"], ["meal_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_meal_template_items_template_id"),
        "meal_template_items",
        ["template_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_meal_template_items_template_id"), table_name="meal_template_items")
    op.drop_table("meal_template_items")
    op.drop_index("uq_meal_templates_name_lower", table_name="meal_templates")
    op.drop_table("meal_templates")
