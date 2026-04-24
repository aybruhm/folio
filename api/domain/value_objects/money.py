from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional


class Currency(str, Enum):
    USD = "USD"
    GBP = "GBP"
    EUR = "EUR"
    JPY = "JPY"
    AUD = "AUD"
    NGN = "NGN"
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
    twr: Optional[float] = None
    mwr: Optional[float] = None


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
