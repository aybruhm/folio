"""add market_data_provider to assets and trades

Revision ID: b7c8d9e0f1a2
Revises: a7b8c9d0e1f2
Create Date: 2026-05-14 00:00:01.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assets",
        sa.Column(
            "market_data_provider",
            sa.String(length=20),
            nullable=False,
            server_default="yfinance",
        ),
    )
    op.add_column(
        "trades",
        sa.Column(
            "market_data_provider",
            sa.String(length=20),
            nullable=False,
            server_default="yfinance",
        ),
    )


def downgrade() -> None:
    op.drop_column("trades", "market_data_provider")
    op.drop_column("assets", "market_data_provider")
