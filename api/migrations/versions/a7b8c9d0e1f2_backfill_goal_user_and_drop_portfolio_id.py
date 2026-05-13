"""backfill goals.user_id from portfolios and drop portfolio_id

Revision ID: a7b8c9d0e1f2
Revises: f6a1b2c3d4e5
Create Date: 2026-05-12 00:00:02.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE goals g
        SET user_id = p.user_id
        FROM portfolios p
        WHERE g.portfolio_id = p.id
          AND g.user_id IS NULL
        """
    )

    op.alter_column("goals", "user_id", nullable=False)

    op.drop_index("ix_goals_portfolio_id", table_name="goals")
    op.drop_constraint("goals_portfolio_id_fkey", "goals", type_="foreignkey")
    op.drop_column("goals", "portfolio_id")


def downgrade() -> None:
    op.add_column("goals", sa.Column("portfolio_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "goals_portfolio_id_fkey", "goals", "portfolios", ["portfolio_id"], ["id"]
    )
    op.create_index("ix_goals_portfolio_id", "goals", ["portfolio_id"], unique=False)

    op.execute(
        """
        UPDATE goals g
        SET portfolio_id = p.id
        FROM portfolios p
        WHERE g.user_id = p.user_id
          AND g.portfolio_id IS NULL
        """
    )

    op.alter_column("goals", "portfolio_id", nullable=False)
