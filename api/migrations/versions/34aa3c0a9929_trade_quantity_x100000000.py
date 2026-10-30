"""trade quantity x100000000

Revision ID: 34aa3c0a9929
Revises: b7c8d9e0f1a2
Create Date: 2026-10-30 23:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "34aa3c0a9929"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Largest x10000 quantity that still fits in BIGINT after multiplying by 10000.
MAX_X10000_QUANTITY = 9223372036854775807 // 10000


def upgrade() -> None:
    # Fail before writing anything if a quantity would overflow BIGINT.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM trades WHERE abs(quantity) > {MAX_X10000_QUANTITY}
            ) THEN
                RAISE EXCEPTION 'trades.quantity too large to rescale to x100000000';
            END IF;
        END $$;
        """
    )
    # Existing trade quantities are stored at x10000; multiplying by 10000
    # carries them forward to the new x100000000 scale (8 decimal places).
    op.execute("UPDATE trades SET quantity = quantity * 10000")


def downgrade() -> None:
    # Digits beyond the 4th decimal place are lost when returning to x10000.
    op.execute("UPDATE trades SET quantity = ROUND(quantity / 10000.0)")
