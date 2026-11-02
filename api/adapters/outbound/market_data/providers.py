from adapters.outbound.market_data.ngnmarket_adapter import NgnMarketAdapter
from adapters.outbound.market_data.ngxpulse_adapter import NgxPulseAdapter
from adapters.outbound.market_data.yfinance_adapter import YFinanceAdapter

# Providers that can supply a daily price or index series for a benchmark.
# Tiingo and TradingView are for holdings only: neither serves index history.
BENCHMARK_PROVIDERS = ("yfinance", "ngxpulse", "ngnmarket")

PROVIDER_LABELS = {
    "yfinance": "Yahoo Finance",
    "ngxpulse": "NGXPulse",
    "ngnmarket": "NGNMarket",
}

# Currency a provider quotes in when it can't be asked. Yahoo reports its own.
PROVIDER_CURRENCY = {"ngxpulse": "NGN", "ngnmarket": "NGN"}


def build_adapter(provider: str):
    if provider == "ngxpulse":
        return NgxPulseAdapter()
    if provider == "ngnmarket":
        return NgnMarketAdapter()
    return YFinanceAdapter()


def is_configured(adapter) -> bool:
    """False for a keyed provider with no API key on this server."""
    return getattr(adapter, "_enabled", True)
