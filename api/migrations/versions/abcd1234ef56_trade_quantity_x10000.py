"""trade quantity x10000

Revision ID: abcd1234ef56
Revises: e2f3a4b5c6d7
Create Date: 2026-05-11 23:59:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "abcd1234ef56"
down_revision: Union[str, Sequence[str], None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing trade quantities were stored at x100; multiplying by 100
    # carries them forward to the new x10000 scale without changing values.
    op.execute("UPDATE trades SET quantity = quantity * 100")
    op.alter_column(
        "trades",
        "quantity",
        existing_type=sa.BigInteger(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Reverse the one-time backfill if we ever return to the old x100 scale.
    op.execute("UPDATE trades SET quantity = quantity / 100")
    op.alter_column(
        "trades",
        "quantity",
        existing_type=sa.BigInteger(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )
