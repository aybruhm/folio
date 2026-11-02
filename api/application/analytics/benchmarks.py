BENCHMARK_CATALOG: list[dict[str, str]] = [
    {"ticker": "^GSPC", "name": "S&P 500", "category": "Indices"},
    {"ticker": "^NDX", "name": "Nasdaq-100", "category": "Indices"},
    {"ticker": "^DJI", "name": "Dow Jones Industrial Average", "category": "Indices"},
    {"ticker": "^RUT", "name": "Russell 2000", "category": "Indices"},
    {"ticker": "^FTSE", "name": "FTSE 100", "category": "Indices"},
    {"ticker": "^GDAXI", "name": "DAX", "category": "Indices"},
    {"ticker": "^N225", "name": "Nikkei 225", "category": "Indices"},
    {
        "ticker": "NGX:ASI",
        "name": "NGX All-Share Index",
        "category": "Indices",
        "provider": "ngxpulse",
        "currency": "NGN",
    },
    {
        "ticker": "NGX:NGX-30",
        "name": "NGX 30",
        "category": "Indices",
        "provider": "ngxpulse",
        "currency": "NGN",
    },
    {"ticker": "VOO", "name": "Vanguard S&P 500 ETF", "category": "ETFs"},
    {"ticker": "VTI", "name": "Vanguard Total Stock Market ETF", "category": "ETFs"},
    {"ticker": "QQQ", "name": "Invesco QQQ (Nasdaq-100)", "category": "ETFs"},
    {"ticker": "URTH", "name": "iShares MSCI World ETF", "category": "ETFs"},
    {"ticker": "IWDA.L", "name": "iShares Core MSCI World", "category": "ETFs"},
    {"ticker": "VT", "name": "Vanguard Total World Stock ETF", "category": "ETFs"},
    {"ticker": "EEM", "name": "iShares MSCI Emerging Markets ETF", "category": "ETFs"},
    {"ticker": "AGG", "name": "iShares Core US Aggregate Bond ETF", "category": "ETFs"},
    {"ticker": "VNQ", "name": "Vanguard Real Estate ETF", "category": "ETFs"},
    {"ticker": "GLD", "name": "SPDR Gold Shares", "category": "ETFs"},
    {"ticker": "BTC-USD", "name": "Bitcoin", "category": "Crypto"},
    {"ticker": "ETH-USD", "name": "Ethereum", "category": "Crypto"},
    {"ticker": "SOL-USD", "name": "Solana", "category": "Crypto"},
]

_BY_TICKER = {b["ticker"]: b for b in BENCHMARK_CATALOG}
DEFAULT_PROVIDER = "yfinance"


def benchmark_name(ticker: str) -> str:
    """The catalog name for a ticker, or the ticker itself for a custom one."""
    entry = _BY_TICKER.get(ticker)
    return entry["name"] if entry else ticker


def benchmark_provider(ticker: str) -> str:
    """The provider a catalog ticker is served by; Yahoo for anything else."""
    entry = _BY_TICKER.get(ticker)
    return entry.get("provider", DEFAULT_PROVIDER) if entry else DEFAULT_PROVIDER


def benchmark_currency(ticker: str) -> str | None:
    """The quote currency a catalog entry declares, when it declares one."""
    entry = _BY_TICKER.get(ticker)
    return entry.get("currency") if entry else None


def list_catalog() -> list[dict[str, str]]:
    return [
        {**b, "provider": b.get("provider", DEFAULT_PROVIDER)}
        for b in BENCHMARK_CATALOG
    ]
