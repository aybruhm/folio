import pytest

from adapters.outbound.market_data import tiingo_adapter as tiingo_module
from domain.value_objects.money import Currency


class FakeTiingoClient:
    def __init__(self, metadata_by_symbol=None, stock_tickers=None):
        self.metadata_by_symbol = metadata_by_symbol or {}
        self.stock_tickers = stock_tickers or []
        self.metadata_calls = []
        self.list_calls = 0

    def get_ticker_metadata(self, symbol: str):
        self.metadata_calls.append(symbol)
        return self.metadata_by_symbol.get(symbol)

    def list_stock_tickers(self):
        self.list_calls += 1
        return self.stock_tickers


@pytest.mark.asyncio
async def test_get_asset_metadata_returns_none_when_api_key_missing(monkeypatch):
    monkeypatch.setattr(tiingo_module.settings, "TIINGO_API_KEY", "", raising=False)

    adapter = tiingo_module.TiingoAdapter()
    result = await adapter.get_asset_metadata("AAPL", "USD")

    assert result is None


@pytest.mark.asyncio
async def test_get_asset_metadata_maps_tiingo_payload(monkeypatch):
    monkeypatch.setattr(
        tiingo_module.settings, "TIINGO_API_KEY", "test-tiingo-key", raising=False
    )

    fake_client = FakeTiingoClient(
        metadata_by_symbol={
            "AAPL": {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "assetType": "Stock",
                "currency": "USD",
                "exchangeCode": "NASDAQ",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "countryCode": "US",
                "isin": "US0378331005",
            }
        }
    )

    monkeypatch.setattr(tiingo_module, "TiingoClient", lambda config: fake_client)

    adapter = tiingo_module.TiingoAdapter()
    result = await adapter.get_asset_metadata("AAPL", "USD")

    assert result is not None
    assert result.ticker == "AAPL"
    assert result.name == "Apple Inc."
    assert result.asset_class == "stock"
    assert result.currency == Currency.USD
    assert result.exchange == "NASDAQ"
    assert result.country == "US"
    assert result.isin == "US0378331005"
    assert fake_client.metadata_calls[0] == "AAPL"


@pytest.mark.asyncio
async def test_get_asset_metadata_resolves_exchange_qualified_ticker(monkeypatch):
    monkeypatch.setattr(
        tiingo_module.settings, "TIINGO_API_KEY", "test-tiingo-key", raising=False
    )

    fake_client = FakeTiingoClient(
        metadata_by_symbol={
            "SPY": {
                "ticker": "SPY",
                "name": "SPDR S&P 500 ETF Trust",
                "assetType": "ETF",
                "currency": "USD",
                "exchange": "NYSE Arca",
            }
        },
        stock_tickers=[
            {"ticker": "SPY", "exchange": "NYSE Arca"},
            {"ticker": "SPY", "exchange": "BATS/CBOE Equities"},
        ],
    )

    monkeypatch.setattr(tiingo_module, "TiingoClient", lambda config: fake_client)

    adapter = tiingo_module.TiingoAdapter()
    result = await adapter.get_asset_metadata("NYSE ARCA:SPY", "USD")

    assert result is not None
    assert result.asset_class == "etf"
    assert result.exchange == "NYSE Arca"
    assert fake_client.list_calls == 1


@pytest.mark.asyncio
async def test_get_asset_metadata_handles_dot_ticker_with_dash_variant(monkeypatch):
    monkeypatch.setattr(
        tiingo_module.settings, "TIINGO_API_KEY", "test-tiingo-key", raising=False
    )

    fake_client = FakeTiingoClient(
        metadata_by_symbol={
            "BRK-B": {
                "ticker": "BRK-B",
                "name": "Berkshire Hathaway Inc. Class B",
                "assetType": "Stock",
                "currency": "USD",
                "exchange": "NYSE",
            }
        }
    )

    monkeypatch.setattr(tiingo_module, "TiingoClient", lambda config: fake_client)

    adapter = tiingo_module.TiingoAdapter()
    result = await adapter.get_asset_metadata("BRK.B", "USD")

    assert result is not None
    assert result.name == "Berkshire Hathaway Inc. Class B"
    assert result.exchange == "NYSE"
    assert "BRK.B" in fake_client.metadata_calls
    assert "BRK-B" in fake_client.metadata_calls


@pytest.mark.asyncio
async def test_get_asset_metadata_stops_when_hourly_limit_reached(monkeypatch):
    monkeypatch.setattr(
        tiingo_module.settings, "TIINGO_API_KEY", "test-tiingo-key", raising=False
    )

    fake_client = FakeTiingoClient(
        metadata_by_symbol={
            "AAPL": {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "assetType": "Stock",
                "currency": "USD",
            }
        }
    )

    monkeypatch.setattr(tiingo_module, "TiingoClient", lambda config: fake_client)

    adapter = tiingo_module.TiingoAdapter()
    adapter._hour_count = adapter._MAX_REQUESTS_PER_HOUR

    result = await adapter.get_asset_metadata("AAPL", "USD")

    assert result is None
    assert fake_client.metadata_calls == []
