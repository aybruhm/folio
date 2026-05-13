from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
from uuid import UUID, uuid4

from domain.value_objects.money import (
    AssetClass,
    AssetMetadata,
    Currency,
    TradeType,
)


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    hashed_password: str
    is_active: bool
    created_at: datetime


@dataclass(frozen=True)
class Asset:
    id: UUID
    ticker: str
    name: str
    asset_class: AssetClass
    currency: Currency
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    isin: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_metadata(cls, ticker: str, metadata: AssetMetadata) -> "Asset":
        return cls(
            id=uuid4(),
            ticker=ticker,
            name=metadata.name,
            asset_class=AssetClass(metadata.asset_class),
            currency=metadata.currency,
            exchange=metadata.exchange,
            sector=metadata.sector,
            industry=metadata.industry,
            country=metadata.country,
            isin=metadata.isin,
        )


@dataclass(frozen=True)
class Trade:
    id: UUID
    portfolio_id: UUID
    asset_id: UUID
    ticker: str
    trade_type: TradeType
    trade_date: datetime
    quantity: int  # ×10000 scale (e.g. 1.0000 BTC → 10000)
    price: int  # ×100 scale (e.g. $185.20 → 18520)
    trade_currency: Currency
    fees: int = 0  # ×100 scale
    notes: Optional[str] = None
    source: str = "manual"
    import_batch_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=datetime.now)

    def total_cost(self) -> int:
        return (self.quantity * self.price) // 10000 + self.fees


@dataclass(frozen=True)
class Holding:
    asset_id: UUID
    ticker: str
    quantity: int  # ×100
    current_price: int  # ×100
    cost_basis: int  # ×100
    market_value: int  # ×100
    total_return: int  # ×100
    unrealised_pnl: int  # ×100
    realised_pnl: int = 0  # ×100

    @property
    def total_return_percent(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return (self.total_return / self.cost_basis) * 100

    @property
    def weight(self) -> int:
        return self.market_value


@dataclass
class Portfolio:
    id: UUID
    user_id: UUID
    name: str
    base_currency: Currency
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update(
        self, name: Optional[str] = None, description: Optional[str] = None
    ) -> None:
        if name:
            self.name = name
        if description is not None:
            self.description = description
        self.updated_at = datetime.now()


@dataclass(frozen=True)
class Goal:
    id: UUID
    user_id: UUID
    name: str
    target_net_worth: int  # ×100
    target_net_worth_currency: Currency
    target_date: date
    monthly_savings: int  # ×100
    monthly_savings_currency: Currency
    expected_annual_return: int  # ×100 (e.g. 7% → 7)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class FxRate:
    from_currency: Currency
    to_currency: Currency
    date: date
    rate: int  # ×100

    def convert(self, amount: int) -> int:
        return (amount * self.rate) // 100
