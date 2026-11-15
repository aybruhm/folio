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


class AssetModel(Base):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ticker = Column(String(20), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    asset_class = Column(String(20), nullable=False)
    exchange = Column(String(10), nullable=True)
    currency = Column(CHAR(3), nullable=False)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    isin = Column(String(20), nullable=True)
    market_data_provider = Column(String(20), nullable=False, default="yfinance")
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    trades = relationship("TradeModel", back_populates="asset")
    price_history = relationship(
        "PriceHistoryModel", back_populates="asset", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_assets_ticker", "ticker"),
        Index("ix_assets_asset_class", "asset_class"),
        Index("ix_assets_sector", "sector"),
    )
