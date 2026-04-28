from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional


class Currency(str, Enum):
    # Americas
    USD = "USD"  # US Dollar
    CAD = "CAD"  # Canadian Dollar
    BRL = "BRL"  # Brazilian Real
    MXN = "MXN"  # Mexican Peso
    ARS = "ARS"  # Argentine Peso
    CLP = "CLP"  # Chilean Peso
    COP = "COP"  # Colombian Peso
    PEN = "PEN"  # Peruvian Sol

    # Europe
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound
    CHF = "CHF"  # Swiss Franc
    SEK = "SEK"  # Swedish Krona
    NOK = "NOK"  # Norwegian Krone
    DKK = "DKK"  # Danish Krone
    PLN = "PLN"  # Polish Zloty
    CZK = "CZK"  # Czech Koruna
    HUF = "HUF"  # Hungarian Forint
    RON = "RON"  # Romanian Leu
    TRY = "TRY"  # Turkish Lira
    RUB = "RUB"  # Russian Ruble

    # Middle East & Africa
    ILS = "ILS"  # Israeli Shekel
    AED = "AED"  # UAE Dirham
    SAR = "SAR"  # Saudi Riyal
    QAR = "QAR"  # Qatari Riyal
    KWD = "KWD"  # Kuwaiti Dinar
    EGP = "EGP"  # Egyptian Pound
    NGN = "NGN"  # Nigerian Naira
    ZAR = "ZAR"  # South African Rand
    KES = "KES"  # Kenyan Shilling
    GHS = "GHS"  # Ghanaian Cedi
    MAD = "MAD"  # Moroccan Dirham

    # Asia Pacific
    JPY = "JPY"  # Japanese Yen
    CNY = "CNY"  # Chinese Yuan
    HKD = "HKD"  # Hong Kong Dollar
    KRW = "KRW"  # South Korean Won
    TWD = "TWD"  # Taiwanese Dollar
    SGD = "SGD"  # Singapore Dollar
    INR = "INR"  # Indian Rupee
    AUD = "AUD"  # Australian Dollar
    NZD = "NZD"  # New Zealand Dollar
    MYR = "MYR"  # Malaysian Ringgit
    THB = "THB"  # Thai Baht
    IDR = "IDR"  # Indonesian Rupiah
    PHP = "PHP"  # Philippine Peso
    VND = "VND"  # Vietnamese Dong
    PKR = "PKR"  # Pakistani Rupee
    BDT = "BDT"  # Bangladeshi Taka
    LKR = "LKR"  # Sri Lankan Rupee

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
