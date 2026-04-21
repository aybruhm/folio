from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date, datetime
from typing import Optional
from uuid import UUID, uuid4
from api.domain.value_objects.money import Money, Currency, TradeType, AssetClass, DateRange, ReturnMetric, AssetMetadata

@dataclass
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
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    @classmethod
    def from_metadata(cls, ticker: str, metadata: AssetMetadata) -> 'Asset':
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
            isin=metadata.isin
        )

@dataclass
class Trade:
    id: UUID
    portfolio_id: UUID
    asset_id: UUID
    ticker: str
    trade_type: TradeType
    trade_date: date
    quantity: Decimal
    price: Decimal
    trade_currency: Currency
    fees: Decimal = Decimal('0')
    notes: Optional[str] = None
    source: str = 'manual'
    import_batch_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def total_cost(self) -> Money:
        return Money(self.quantity * self.price + self.fees, self.trade_currency)

@dataclass
class Holding:
    asset_id: UUID
    ticker: str
    quantity: Decimal
    current_price: Money
    cost_basis: Money
    market_value: Money
    total_return: Money
    unrealised_pnl: Money
    realised_pnl: Money = field(default_factory=lambda: Money(Decimal('0'), Currency.USD))
    
    @property
    def total_return_percent(self) -> Decimal:
        if self.cost_basis.amount == 0:
            return Decimal('0')
        return (self.total_return.amount / self.cost_basis.amount) * Decimal('100')
    
    @property
    def weight(self) -> Decimal:
        return self.market_value.amount

@dataclass
class Portfolio:
    id: UUID
    name: str
    base_currency: Currency
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def update(self, name: Optional[str] = None, description: Optional[str] = None) -> None:
        if name:
            self.name = name
        if description is not None:
            self.description = description
        self.updated_at = datetime.utcnow()

@dataclass
class Goal:
    id: UUID
    portfolio_id: UUID
    name: str
    target_net_worth: Money
    target_date: date
    monthly_savings: Money
    expected_annual_return: Decimal
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        if not isinstance(self.expected_annual_return, Decimal):
            object.__setattr__(self, 'expected_annual_return', Decimal(str(self.expected_annual_return)))
        if self.monthly_savings.currency != self.target_net_worth.currency:
            raise ValueError("Monthly savings and target net worth must use same currency")

@dataclass
class FxRate:
    from_currency: Currency
    to_currency: Currency
    date: date
    rate: Decimal
    
    def convert(self, amount: Decimal) -> Decimal:
        return amount * self.rate
    
    def __post_init__(self):
        if not isinstance(self.rate, Decimal):
            object.__setattr__(self, 'rate', Decimal(str(self.rate)))
