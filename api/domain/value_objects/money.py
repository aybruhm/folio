from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from datetime import date, datetime
from enum import Enum

class Currency(str, Enum):
    USD = "USD"
    GBP = "GBP"
    EUR = "EUR"
    JPY = "JPY"
    AUD = "AUD"
    CAD = "CAD"
    CHF = "CHF"
    CNY = "CNY"
    INR = "INR"
    SGD = "SGD"
    
    @classmethod
    def validate(cls, code: str) -> bool:
        try:
            cls(code)
            return True
        except ValueError:
            return False

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: Currency
    
    def __post_init__(self):
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, 'amount', Decimal(str(self.amount)))
    
    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)
    
    def __sub__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {self.currency} and {other.currency}")
        return Money(self.amount - other.amount, self.currency)
    
    def __mul__(self, factor: Decimal | int | float) -> 'Money':
        return Money(self.amount * Decimal(str(factor)), self.currency)
    
    def __rmul__(self, factor: Decimal | int | float) -> 'Money':
        return self.__mul__(factor)
    
    def __truediv__(self, divisor: Decimal | int | float) -> 'Money':
        return Money(self.amount / Decimal(str(divisor)), self.currency)
    
    def convert(self, target_currency: Currency, rate: Decimal) -> 'Money':
        return Money(self.amount * rate, target_currency)

@dataclass(frozen=True)
class DateRange:
    start: date
    end: date
    
    def __post_init__(self):
        if self.start > self.end:
            raise ValueError("start date must be <= end date")
    
    def days(self) -> int:
        return (self.end - self.start).days

@dataclass(frozen=True)
class ReturnMetric:
    twr: Optional[Decimal] = None
    mwr: Optional[Decimal] = None
    
    def __post_init__(self):
        if self.twr is not None and not isinstance(self.twr, Decimal):
            object.__setattr__(self, 'twr', Decimal(str(self.twr)))
        if self.mwr is not None and not isinstance(self.mwr, Decimal):
            object.__setattr__(self, 'mwr', Decimal(str(self.mwr)))

@dataclass(frozen=True)
class AssetMetadata:
    ticker: str
    name: str
    asset_class: str
    currency: Currency
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    isin: Optional[str] = None

class TradeType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    FEE = "fee"

class AssetClass(str, Enum):
    STOCK = "stock"
    ETF = "etf"
    CRYPTO = "crypto"
    CASH = "cash"
