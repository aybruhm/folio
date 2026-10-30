"""add archived_at to portfolios

Revision ID: ba4ed9445511
Revises: 34aa3c0a9929
Create Date: 2026-10-30 23:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "ba4ed9445511"
down_revision: Union[str, Sequence[str], None] = "34aa3c0a9929"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NULL means active; a timestamp means archived (hidden by default).
    op.add_column("portfolios", sa.Column("archived_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("portfolios", "archived_at")
