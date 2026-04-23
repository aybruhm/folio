from sqlalchemy import Column, String, DateTime, Numeric, Date, ForeignKey, Index, UniqueConstraint, JSON, Enum as SQLEnum, CHAR
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from uuid import uuid4
import enum

Base = declarative_base()

class PortfolioModel(Base):
    __tablename__ = 'portfolios'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    base_currency = Column(CHAR(3), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    trades = relationship('TradeModel', back_populates='portfolio', cascade='all, delete-orphan')
    goals = relationship('GoalModel', back_populates='portfolio', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('ix_portfolios_base_currency', 'base_currency'),
    )

class AssetModel(Base):
    __tablename__ = 'assets'
    
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
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    trades = relationship('TradeModel', back_populates='asset')
    price_history = relationship('PriceHistoryModel', back_populates='asset', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('ix_assets_ticker', 'ticker'),
        Index('ix_assets_asset_class', 'asset_class'),
        Index('ix_assets_sector', 'sector'),
    )

class TradeModel(Base):
    __tablename__ = 'trades'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey('portfolios.id'), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id'), nullable=False)
    ticker = Column(String(20), nullable=False)
    trade_type = Column(String(20), nullable=False)
    trade_date = Column(DateTime, nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    price = Column(Numeric(20, 8), nullable=False)
    trade_currency = Column(CHAR(3), nullable=False)
    fees = Column(Numeric(20, 8), default=0)
    notes = Column(String, nullable=True)
    source = Column(String(20), default='manual')
    import_batch_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    portfolio = relationship('PortfolioModel', back_populates='trades')
    asset = relationship('AssetModel', back_populates='trades')
    
    __table_args__ = (
        Index('ix_trades_portfolio_id', 'portfolio_id'),
        Index('ix_trades_asset_id', 'asset_id'),
        Index('ix_trades_trade_date', 'trade_date'),
        Index('ix_trades_import_batch_id', 'import_batch_id'),
    )

class PriceHistoryModel(Base):
    __tablename__ = 'price_history'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id'), nullable=False)
    date = Column(Date, nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    currency = Column(CHAR(3), nullable=False)
    
    asset = relationship('AssetModel', back_populates='price_history')
    
    __table_args__ = (
        UniqueConstraint('asset_id', 'date', name='uq_price_history_asset_date'),
        Index('ix_price_history_asset_id', 'asset_id'),
        Index('ix_price_history_date', 'date'),
    )

class FxRateModel(Base):
    __tablename__ = 'fx_rates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    from_currency = Column(CHAR(3), nullable=False)
    to_currency = Column(CHAR(3), nullable=False)
    date = Column(Date, nullable=False)
    rate = Column(Numeric(20, 8), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('from_currency', 'to_currency', 'date', name='uq_fx_rates_currencies_date'),
        Index('ix_fx_rates_currencies', 'from_currency', 'to_currency'),
        Index('ix_fx_rates_date', 'date'),
    )

class BenchmarkModel(Base):
    __tablename__ = 'benchmarks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ticker = Column(String(20), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_benchmarks_ticker', 'ticker'),
    )

class GoalModel(Base):
    __tablename__ = 'goals'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey('portfolios.id'), nullable=False)
    name = Column(String(255), nullable=False)
    target_net_worth = Column(Numeric(20, 2), nullable=False)
    target_net_worth_currency = Column(CHAR(3), nullable=False)
    target_date = Column(Date, nullable=False)
    monthly_savings = Column(Numeric(20, 2), nullable=False)
    monthly_savings_currency = Column(CHAR(3), nullable=False)
    expected_annual_return = Column(Numeric(5, 4), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    portfolio = relationship('PortfolioModel', back_populates='goals')
    
    __table_args__ = (
        Index('ix_goals_portfolio_id', 'portfolio_id'),
        Index('ix_goals_target_date', 'target_date'),
    )

class CsvImportProfileModel(Base):
    __tablename__ = 'csv_import_profiles'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    column_mapping = Column(JSON, nullable=False)
    date_format = Column(String(50), nullable=True)
    delimiter = Column(CHAR(1), default=',')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_csv_import_profiles_name', 'name'),
    )
