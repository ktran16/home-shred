"""multi profile management

Revision ID: 5b2f8c4b8a10
Revises: 7217d574bf8e
Create Date: 2026-06-14 17:02:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5b2f8c4b8a10"
down_revision: str | None = "7217d574bf8e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_user_profile_singleton", "user_profile", type_="check")
    op.add_column("user_profile", sa.Column("name", sa.Text(), nullable=True))
    op.add_column(
        "user_profile",
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.execute("UPDATE user_profile SET name = 'Default', is_active = true WHERE id = 1")
    op.alter_column("user_profile", "name", nullable=False)
    op.create_check_constraint(
        "ck_user_profile_name_nonempty", "user_profile", "length(trim(name)) > 0"
    )
    op.create_index(op.f("ix_user_profile_is_active"), "user_profile", ["is_active"], unique=False)
    op.execute("CREATE SEQUENCE IF NOT EXISTS user_profile_id_seq OWNED BY user_profile.id")
    op.execute(
        "SELECT setval('user_profile_id_seq', "
        "COALESCE((SELECT MAX(id) FROM user_profile), 1))"
    )
    op.alter_column(
        "user_profile",
        "id",
        server_default=sa.text("nextval('user_profile_id_seq'::regclass)"),
        existing_type=sa.Integer(),
    )


def downgrade() -> None:
    op.alter_column("user_profile", "id", server_default=None, existing_type=sa.Integer())
    op.execute("DROP SEQUENCE IF EXISTS user_profile_id_seq")
    op.drop_index(op.f("ix_user_profile_is_active"), table_name="user_profile")
    op.drop_constraint("ck_user_profile_name_nonempty", "user_profile", type_="check")
    op.drop_column("user_profile", "is_active")
    op.drop_column("user_profile", "name")
    op.create_check_constraint("ck_user_profile_singleton", "user_profile", "id = 1")
