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


class PortfolioModel(Base):
    __tablename__ = "portfolios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    base_currency = Column(CHAR(3), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )
    archived_at = Column(DateTime, nullable=True)

    user = relationship("UserModel", back_populates="portfolios")
    trades = relationship(
        "TradeModel", back_populates="portfolio", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_portfolios_base_currency", "base_currency"),
        Index("ix_portfolios_user_id", "user_id"),
    )
