"""add workout_sessions.impression (W4)

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-06-15 14:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4b5c6d7e8f9"
down_revision: str | None = "f3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("workout_sessions", sa.Column("impression", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("workout_sessions", "impression")
