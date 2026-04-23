"""trade_date column to datetime

Revision ID: b3c2d1e4f5a6
Revises: 15737b75007b
Create Date: 2026-04-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3c2d1e4f5a6"
down_revision: Union[str, Sequence[str], None] = "15737b75007b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "trades",
        "trade_date",
        existing_type=sa.Date(),
        type_=sa.DateTime(),
        existing_nullable=False,
        postgresql_using="trade_date::timestamp",
    )


def downgrade() -> None:
    op.alter_column(
        "trades",
        "trade_date",
        existing_type=sa.DateTime(),
        type_=sa.Date(),
        existing_nullable=False,
        postgresql_using="trade_date::date",
    )
