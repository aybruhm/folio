from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    CHAR,
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from infrastructure.db.postgres.base import Base


class FxRateModel(Base):
    __tablename__ = "fx_rates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    from_currency = Column(CHAR(3), nullable=False)
    to_currency = Column(CHAR(3), nullable=False)
    date = Column(Date, nullable=False)
    rate = Column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "from_currency", "to_currency", "date", name="uq_fx_rates_currencies_date"
        ),
        Index("ix_fx_rates_currencies", "from_currency", "to_currency"),
        Index("ix_fx_rates_date", "date"),
    )
