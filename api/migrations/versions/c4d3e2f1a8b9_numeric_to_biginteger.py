"""numeric columns to biginteger (×100 integer storage)

Revision ID: c4d3e2f1a8b9
Revises: b3c2d1e4f5a6
Create Date: 2026-04-23 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d3e2f1a8b9"
down_revision: Union[str, Sequence[str], None] = "b3c2d1e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # trades: quantity, price, fees → BIGINT (multiply existing by 100)
    op.execute("UPDATE trades SET quantity = ROUND(quantity * 100), price = ROUND(price * 100), fees = ROUND(fees * 100)")
    op.alter_column("trades", "quantity", existing_type=sa.Numeric(20, 8), type_=sa.BigInteger(), existing_nullable=False, postgresql_using="ROUND(quantity)::bigint")
    op.alter_column("trades", "price", existing_type=sa.Numeric(20, 8), type_=sa.BigInteger(), existing_nullable=False, postgresql_using="ROUND(price)::bigint")
    op.alter_column("trades", "fees", existing_type=sa.Numeric(20, 8), type_=sa.BigInteger(), existing_nullable=True, postgresql_using="ROUND(fees)::bigint")

    # price_history: close → BIGINT
    op.execute("UPDATE price_history SET close = ROUND(close * 100)")
    op.alter_column("price_history", "close", existing_type=sa.Numeric(20, 8), type_=sa.BigInteger(), existing_nullable=False, postgresql_using="ROUND(close)::bigint")

    # fx_rates: rate → BIGINT
    op.execute("UPDATE fx_rates SET rate = ROUND(rate * 100)")
    op.alter_column("fx_rates", "rate", existing_type=sa.Numeric(20, 8), type_=sa.BigInteger(), existing_nullable=False, postgresql_using="ROUND(rate)::bigint")

    # goals: target_net_worth, monthly_savings, expected_annual_return → BIGINT
    op.execute("UPDATE goals SET target_net_worth = ROUND(target_net_worth * 100), monthly_savings = ROUND(monthly_savings * 100), expected_annual_return = ROUND(expected_annual_return * 100)")
    op.alter_column("goals", "target_net_worth", existing_type=sa.Numeric(20, 2), type_=sa.BigInteger(), existing_nullable=False, postgresql_using="ROUND(target_net_worth)::bigint")
    op.alter_column("goals", "monthly_savings", existing_type=sa.Numeric(20, 2), type_=sa.BigInteger(), existing_nullable=False, postgresql_using="ROUND(monthly_savings)::bigint")
    op.alter_column("goals", "expected_annual_return", existing_type=sa.Numeric(5, 4), type_=sa.BigInteger(), existing_nullable=False, postgresql_using="ROUND(expected_annual_return)::bigint")


def downgrade() -> None:
    # Reverse: divide by 100 back to Numeric
    op.alter_column("trades", "quantity", existing_type=sa.BigInteger(), type_=sa.Numeric(20, 8), existing_nullable=False, postgresql_using="quantity::numeric / 100")
    op.alter_column("trades", "price", existing_type=sa.BigInteger(), type_=sa.Numeric(20, 8), existing_nullable=False, postgresql_using="price::numeric / 100")
    op.alter_column("trades", "fees", existing_type=sa.BigInteger(), type_=sa.Numeric(20, 8), existing_nullable=True, postgresql_using="fees::numeric / 100")
    op.alter_column("price_history", "close", existing_type=sa.BigInteger(), type_=sa.Numeric(20, 8), existing_nullable=False, postgresql_using="close::numeric / 100")
    op.alter_column("fx_rates", "rate", existing_type=sa.BigInteger(), type_=sa.Numeric(20, 8), existing_nullable=False, postgresql_using="rate::numeric / 100")
    op.alter_column("goals", "target_net_worth", existing_type=sa.BigInteger(), type_=sa.Numeric(20, 2), existing_nullable=False, postgresql_using="target_net_worth::numeric / 100")
    op.alter_column("goals", "monthly_savings", existing_type=sa.BigInteger(), type_=sa.Numeric(20, 2), existing_nullable=False, postgresql_using="monthly_savings::numeric / 100")
    op.alter_column("goals", "expected_annual_return", existing_type=sa.BigInteger(), type_=sa.Numeric(5, 4), existing_nullable=False, postgresql_using="expected_annual_return::numeric / 100")
