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


class TradeModel(Base):
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_id = Column(
        UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False
    )
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    ticker = Column(String(20), nullable=False)
    trade_type = Column(String(20), nullable=False)
    trade_date = Column(DateTime, nullable=False)
    quantity = Column(BigInteger, nullable=False)
    price = Column(BigInteger, nullable=False)
    trade_currency = Column(CHAR(3), nullable=False)
    fees = Column(BigInteger, default=0)
    notes = Column(String, nullable=True)
    source = Column(String(20), default="manual")
    import_batch_id = Column(UUID(as_uuid=True), nullable=True)
    market_data_provider = Column(String(20), nullable=False, default="yfinance")
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    portfolio = relationship("PortfolioModel", back_populates="trades")
    asset = relationship("AssetModel", back_populates="trades")

    __table_args__ = (
        Index("ix_trades_portfolio_id", "portfolio_id"),
        Index("ix_trades_asset_id", "asset_id"),
        Index("ix_trades_trade_date", "trade_date"),
        Index("ix_trades_import_batch_id", "import_batch_id"),
    )
