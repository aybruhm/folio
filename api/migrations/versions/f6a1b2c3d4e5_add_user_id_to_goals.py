"""add user_id to goals

Revision ID: f6a1b2c3d4e5
Revises: abcd1234ef56
Create Date: 2026-05-12 00:00:01.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "abcd1234ef56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("goals", sa.Column("user_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_goals_user_id", "goals", "users", ["user_id"], ["id"])
    op.create_index("ix_goals_user_id", "goals", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_goals_user_id", table_name="goals")
    op.drop_constraint("fk_goals_user_id", "goals", type_="foreignkey")
    op.drop_column("goals", "user_id")
