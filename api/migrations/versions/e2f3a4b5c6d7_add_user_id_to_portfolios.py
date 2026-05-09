"""add user_id foreign key to portfolios

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-05-06 00:00:01.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Stable UUID for the seed user created to own pre-existing portfolios
SEED_USER_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    # Insert a seed user to own any pre-existing portfolios
    op.execute(
        f"""
        INSERT INTO users (id, email, hashed_password, is_active, created_at, updated_at)
        VALUES (
            '{SEED_USER_ID}',
            'seed@folio.local',
            '$2b$12$placeholder_hash_not_for_login',
            false,
            NOW(),
            NOW()
        )
        ON CONFLICT (id) DO NOTHING
        """
    )

    # Add user_id as nullable first so existing rows don't violate the constraint
    op.add_column("portfolios", sa.Column("user_id", sa.UUID(), nullable=True))

    # Backfill: assign all existing portfolios to the seed user
    op.execute(
        f"UPDATE portfolios SET user_id = '{SEED_USER_ID}' WHERE user_id IS NULL"
    )

    # Now make user_id NOT NULL
    op.alter_column("portfolios", "user_id", nullable=False)

    # Add foreign key constraint and index
    op.create_foreign_key(
        "fk_portfolios_user_id", "portfolios", "users", ["user_id"], ["id"]
    )
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_portfolios_user_id", table_name="portfolios")
    op.drop_constraint("fk_portfolios_user_id", "portfolios", type_="foreignkey")
    op.drop_column("portfolios", "user_id")
    op.execute(f"DELETE FROM users WHERE id = '{SEED_USER_ID}'")
