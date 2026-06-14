from datetime import date
from uuid import uuid4

import pytest

from adapters.inbound.http import asset_routes
from domain.entities.models import Asset
from domain.value_objects.money import AssetClass, Currency


class FakeAssetRepository:
    def __init__(self, assets=None):
        self.assets = assets or []

    async def search_by_ticker(self, query, limit=10):
        return self.assets

    async def get_by_ticker(self, ticker):
        upper = ticker.upper()
        return next((a for a in self.assets if a.ticker.upper() == upper), None)

    async def list_all(self):
        return self.assets


class FakeYFinanceAdapter:
    def __init__(self, history=None, metadata=None):
        self.history = history or []
        self.metadata = metadata
        self.calls = []

    async def get_price_history(self, ticker, start, end):
        self.calls.append((ticker, start, end))
        return self.history

    async def get_asset_metadata(self, ticker, currency):
        return self.metadata


class FakeTiingoAdapter:
    def __init__(self, metadata=None):
        self.metadata = metadata

    async def get_asset_metadata(self, ticker, currency):
        return self.metadata


class FakeNgnMarketAdapter:
    def __init__(self, metadata=None):
        self.metadata = metadata

    async def get_asset_metadata(self, ticker, currency, asset_class=""):
        return self.metadata


class FakeTradingviewAdapter:
    def __init__(self, metadata=None):
        self.metadata = metadata

    async def get_asset_metadata(self, ticker, currency):
        return self.metadata


@pytest.mark.integration
@pytest.mark.happy_path
def test_asset_search_and_history_routes(client, monkeypatch):
    assets = [
        Asset(
            id=uuid4(),
            ticker="AAPL",
            name="Apple Inc.",
            asset_class=AssetClass.STOCK,
            currency=Currency.USD,
        )
    ]
    history = [(date(2024, 1, 1), 18520)]
    repo = FakeAssetRepository(assets)
    yfinance = FakeYFinanceAdapter(history)
    monkeypatch.setattr(asset_routes, "AssetRepository", lambda session: repo)
    monkeypatch.setattr(asset_routes, "YFinanceAdapter", lambda: yfinance)

    search = client.get("/api/v1/assets/search", params={"q": "AAP"})
    assert search.status_code == 200
    assert search.json()[0]["ticker"] == "AAPL"

    history_response = client.get(
        "/api/v1/assets/AAPL/history",
        params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
    )
    assert history_response.status_code == 200
    assert history_response.json()["ticker"] == "AAPL"
    assert history_response.json()["data"][0]["close"] == "185.2"


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_asset_routes_reject_bad_search_and_history_errors(client, monkeypatch):
    monkeypatch.setattr(
        asset_routes, "AssetRepository", lambda session: FakeAssetRepository([])
    )

    bad_search = client.get("/api/v1/assets/search", params={"q": ""})
    assert bad_search.status_code == 400

    class BrokenYFinance:
        async def get_price_history(self, ticker, start, end):
            raise RuntimeError("boom")

    monkeypatch.setattr(asset_routes, "YFinanceAdapter", lambda: BrokenYFinance())
    broken_history = client.get("/api/v1/assets/AAPL/history")
    assert broken_history.status_code == 400


@pytest.mark.integration
@pytest.mark.edge_case
def test_asset_history_defaults_date_range_when_not_provided(client, monkeypatch):
    yfinance = FakeYFinanceAdapter([(date(2024, 1, 1), 10000)])
    monkeypatch.setattr(asset_routes, "AssetRepository", lambda session: FakeAssetRepository([]))
    monkeypatch.setattr(asset_routes, "YFinanceAdapter", lambda: yfinance)

    response = client.get("/api/v1/assets/MSFT/history")
    assert response.status_code == 200
    assert response.json()["ticker"] == "MSFT"
    assert "start_date" in response.json()
    assert "end_date" in response.json()
    assert yfinance.calls[0][0] == "MSFT"


@pytest.mark.integration
@pytest.mark.happy_path
def test_asset_search_accepts_single_character_query(client, monkeypatch):
    monkeypatch.setattr(
        asset_routes, "AssetRepository", lambda session: FakeAssetRepository([])
    )
    response = client.get("/api/v1/assets/search", params={"q": "A"})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.integration
@pytest.mark.happy_path
def test_validate_ticker_route_supports_all_providers(client, monkeypatch):
    monkeypatch.setattr(
        asset_routes,
        "YFinanceAdapter",
        lambda: FakeYFinanceAdapter(metadata={"ticker": "AAPL"}),
    )
    monkeypatch.setattr(
        asset_routes,
        "TiingoAdapter",
        lambda: FakeTiingoAdapter(metadata={"ticker": "AAPL"}),
    )
    monkeypatch.setattr(
        asset_routes,
        "NgnMarketAdapter",
        lambda: FakeNgnMarketAdapter(metadata={"ticker": "NGX30"}),
    )
    monkeypatch.setattr(
        asset_routes,
        "TradingviewAdapter",
        lambda: FakeTradingviewAdapter(metadata={"ticker": "NASDAQ:AAPL"}),
    )

    yfinance_response = client.get(
        "/api/v1/assets/validate",
        params={"ticker": "AAPL", "provider": "yfinance", "currency": "USD"},
    )
    assert yfinance_response.status_code == 200
    assert yfinance_response.json()["supported"] is True

    tiingo_response = client.get(
        "/api/v1/assets/validate",
        params={"ticker": "AAPL", "provider": "tiingo", "currency": "USD"},
    )
    assert tiingo_response.status_code == 200
    assert tiingo_response.json()["supported"] is True

    ngn_response = client.get(
        "/api/v1/assets/validate",
        params={"ticker": "NGX:NGX30", "provider": "ngnmarket", "currency": "NGN"},
    )
    assert ngn_response.status_code == 200
    assert ngn_response.json()["supported"] is True
    assert ngn_response.json()["provider"] == "ngnmarket"

    tradingview_response = client.get(
        "/api/v1/assets/validate",
        params={"ticker": "NASDAQ:AAPL", "provider": "tradingview", "currency": "USD"},
    )
    assert tradingview_response.status_code == 200
    assert tradingview_response.json()["supported"] is True
    assert tradingview_response.json()["provider"] == "tradingview"
