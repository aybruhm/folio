SUPPORTED_MARKET_DATA_PROVIDERS = frozenset(
    {"yfinance", "tiingo", "ngnmarket", "ngxpulse", "tradingview"}
)


def normalize_provider(provider: str | None) -> str:
    normalized = (provider or "yfinance").strip().lower()
    return normalized if normalized in SUPPORTED_MARKET_DATA_PROVIDERS else "yfinance"
