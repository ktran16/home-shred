"""profile limitations and exercise preferences

Revision ID: 2a7d9dfac116
Revises: 5b2f8c4b8a10
Create Date: 2026-06-14 20:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2a7d9dfac116"
down_revision: str | None = "5b2f8c4b8a10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_profile",
        sa.Column(
            "limitations",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
            nullable=False,
        ),
    )
    op.create_table(
        "exercise_preferences",
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("favorite", "avoid", name="exercisepreferencestatus", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("exercise_id"),
    )
    op.create_index(
        op.f("ix_exercise_preferences_status"),
        "exercise_preferences",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_exercise_preferences_status"), table_name="exercise_preferences")
    op.drop_table("exercise_preferences")
    op.drop_column("user_profile", "limitations")
