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


class GoalModel(Base):
    __tablename__ = "goals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    target_net_worth = Column(BigInteger, nullable=False)
    target_net_worth_currency = Column(CHAR(3), nullable=False)
    target_date = Column(Date, nullable=False)
    monthly_savings = Column(BigInteger, nullable=False)
    monthly_savings_currency = Column(CHAR(3), nullable=False)
    expected_annual_return = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        Index("ix_goals_user_id", "user_id"),
        Index("ix_goals_target_date", "target_date"),
    )
