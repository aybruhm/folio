from uuid import uuid4

import pytest

from application.trades import csv_import_interactor as csv_module
from domain.entities.models import Asset, Trade
from domain.value_objects.money import AssetClass, AssetMetadata, Currency


class FakeTradeRepository:
    def __init__(self):
        self.added = []

    async def add(self, trade: Trade) -> None:
        self.added.append(trade)


class FakeAssetRepository:
    def __init__(self):
        self.assets = {}
        self.added = []
        self.updated = []

    async def get_by_ticker(self, ticker: str):
        return self.assets.get(ticker)

    async def add(self, asset: Asset) -> None:
        self.assets[asset.ticker] = asset
        self.added.append(asset)

    async def update_classification(
        self, asset_id, asset_class, currency, market_data_provider="yfinance"
    ):
        asset = next(item for item in self.assets.values() if item.id == asset_id)
        updated = Asset(
            id=asset.id,
            ticker=asset.ticker,
            name=asset.name,
            asset_class=AssetClass(asset_class),
            currency=Currency(currency),
            exchange=asset.exchange,
            sector=asset.sector,
            industry=asset.industry,
            country=asset.country,
            isin=asset.isin,
            market_data_provider=market_data_provider,
            created_at=asset.created_at,
        )
        self.assets[updated.ticker] = updated
        self.updated.append(updated)


class FakeYFinanceAdapter:
    def __init__(self, metadata=None):
        self.metadata = metadata
        self.calls = []

    async def get_asset_metadata(self, ticker, currency):
        self.calls.append((ticker, currency))
        return self.metadata


class FakeTiingoAdapter:
    def __init__(self, metadata=None):
        self.metadata = metadata
        self.calls = []

    async def get_asset_metadata(self, ticker, currency):
        self.calls.append((ticker, currency))
        return self.metadata


class FakeNgnMarketAdapter:
    def __init__(self, metadata=None):
        self.metadata = metadata
        self.calls = []

    async def get_asset_metadata(self, ticker, currency):
        self.calls.append((ticker, currency))
        return self.metadata


def _patch_import_deps(
    monkeypatch,
    *,
    yfinance_metadata=None,
    tiingo_metadata=None,
    ngnmarket_metadata=None,
):
    trade_repo = FakeTradeRepository()
    asset_repo = FakeAssetRepository()
    yfinance = FakeYFinanceAdapter(yfinance_metadata)
    tiingo = FakeTiingoAdapter(tiingo_metadata)
    ngnmarket = FakeNgnMarketAdapter(ngnmarket_metadata)

    monkeypatch.setattr(csv_module, "TradeRepository", lambda session: trade_repo)
    monkeypatch.setattr(csv_module, "AssetRepository", lambda session: asset_repo)
    monkeypatch.setattr(csv_module, "YFinanceAdapter", lambda: yfinance)
    monkeypatch.setattr(csv_module, "TiingoAdapter", lambda: tiingo)
    monkeypatch.setattr(csv_module, "NgnMarketAdapter", lambda: ngnmarket)

    interactor = csv_module.CsvImportInteractor(session=object())
    return interactor, trade_repo, asset_repo, yfinance, tiingo, ngnmarket


@pytest.mark.asyncio
@pytest.mark.smoke
async def test_preview_csv_returns_headers_and_sample_rows(monkeypatch):
    interactor, *_ = _patch_import_deps(monkeypatch)
    csv_bytes = (
        b"Ticker,Type,Date,Quantity,Price,Currency\nAAPL,buy,2024-01-01,10,185.20,USD\n"
    )

    result = await interactor.preview_csv(csv_bytes, "trades.csv")

    assert result["headers"] == [
        "Ticker",
        "Type",
        "Date",
        "Quantity",
        "Price",
        "Currency",
    ]
    assert result["sample_rows"][0]["Ticker"] == "AAPL"
    assert result["total_lines"] == 2


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_validate_mapping_reports_good_and_bad_rows(monkeypatch):
    interactor, *_ = _patch_import_deps(monkeypatch)
    csv_bytes = (
        b"Ticker,Type,Date,Quantity,Price,Currency,Asset Class\n"
        b"AAPL,buy,2024-01-01,10,185.20,USD,stock\n"
        b"MSFT,sell,2024-02-01,not-a-number,374.00,USD,stock\n"
    )

    result = await interactor.validate_mapping(csv_bytes, "trades.csv", {}, "%Y-%m-%d")

    assert result["valid_count"] == 1
    assert result["error_count"] == 1
    assert result["sample_valid_rows"][0]["ticker"] == "AAPL"


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_confirm_import_creates_cash_asset_and_trade(monkeypatch):
    interactor, trade_repo, asset_repo, yfinance, _tiingo, _ngnmarket = (
        _patch_import_deps(monkeypatch)
    )
    csv_bytes = (
        b"Ticker,Type,Date,Quantity,Price,Currency,Asset Class\n"
        b"CASH,buy,2024-01-01,10,1.00,USD,cash\n"
    )

    result = await interactor.confirm_import(
        csv_bytes,
        "trades.csv",
        {},
        "%Y-%m-%d",
        uuid4(),
    )

    assert result["imported_count"] == 1
    assert result["rejected_count"] == 0
    assert asset_repo.added[0].asset_class == AssetClass.CASH
    assert trade_repo.added[0].source == "csv_import"
    assert trade_repo.added[0].market_data_provider == "yfinance"
    assert asset_repo.added[0].market_data_provider == "yfinance"
    assert yfinance.calls == []


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_confirm_import_updates_existing_asset_market_data_provider(monkeypatch):
    existing_asset = Asset(
        id=uuid4(),
        ticker="AAPL",
        name="Apple",
        asset_class=AssetClass.STOCK,
        currency=Currency.USD,
        market_data_provider="yfinance",
    )
    metadata = AssetMetadata(
        ticker="AAPL",
        name="Apple Inc.",
        asset_class="stock",
        currency=Currency.USD,
        exchange="NASDAQ",
    )
    interactor, trade_repo, asset_repo, yfinance, tiingo, _ngnmarket = (
        _patch_import_deps(monkeypatch, tiingo_metadata=metadata)
    )
    asset_repo.assets[existing_asset.ticker] = existing_asset

    csv_bytes = (
        b"Ticker,Type,Date,Quantity,Price,Currency,Asset Class,Market Data Provider\n"
        b"AAPL,buy,2024-01-01,10,1.00,USD,stock,tiingo\n"
    )

    result = await interactor.confirm_import(
        csv_bytes,
        "trades.csv",
        {},
        "%Y-%m-%d",
        uuid4(),
        market_data_provider="yfinance",
    )

    assert result["imported_count"] == 1
    assert tiingo.calls == [("AAPL", "USD")]
    assert yfinance.calls == []
    assert asset_repo.updated[0].market_data_provider == "tiingo"
    assert trade_repo.added[0].market_data_provider == "tiingo"


@pytest.mark.asyncio
@pytest.mark.grumpy_path
async def test_confirm_import_rejects_when_asset_metadata_is_missing(monkeypatch):
    interactor, trade_repo, asset_repo, yfinance, _tiingo, _ngnmarket = (
        _patch_import_deps(monkeypatch)
    )
    csv_bytes = (
        b"Ticker,Type,Date,Quantity,Price,Currency,Asset Class\n"
        b"UNKNOWN,buy,2024-01-01,10,1.00,USD,stock\n"
    )

    result = await interactor.confirm_import(
        csv_bytes,
        "trades.csv",
        {},
        "%Y-%m-%d",
        uuid4(),
    )

    assert result["imported_count"] == 0
    assert result["rejected_count"] == 1
    assert "Cannot resolve asset" in result["rejection_details"][0]["error"]
    assert trade_repo.added == []
    assert yfinance.calls == [("UNKNOWN", "USD")]


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_confirm_import_uses_selected_ngnmarket_provider(monkeypatch):
    metadata = AssetMetadata(
        ticker="NGX:NGX30",
        name="NGX 30 Index",
        asset_class="etf",
        currency=Currency.NGN,
        exchange="NGX",
    )
    interactor, trade_repo, asset_repo, yfinance, tiingo, ngnmarket = (
        _patch_import_deps(monkeypatch, ngnmarket_metadata=metadata)
    )
    csv_bytes = (
        b"Ticker,Type,Date,Quantity,Price,Currency,Asset Class,Market Data Provider\n"
        b"NGX:NGX30,buy,2024-01-01,10,1.00,NGN,etf,ngnmarket\n"
    )

    result = await interactor.confirm_import(
        csv_bytes,
        "trades.csv",
        {},
        "%Y-%m-%d",
        uuid4(),
        market_data_provider="ngnmarket",
    )

    assert result["imported_count"] == 1
    assert result["rejected_count"] == 0
    assert ngnmarket.calls == [("NGX:NGX30", "NGN")]
    assert tiingo.calls == []
    assert yfinance.calls == []
    assert trade_repo.added[0].ticker == "NGX:NGX30"
    assert trade_repo.added[0].market_data_provider == "ngnmarket"
    assert asset_repo.added[0].exchange == "NGX"
    assert asset_repo.added[0].market_data_provider == "ngnmarket"


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_confirm_import_uses_row_market_data_provider_over_default(monkeypatch):
    metadata = AssetMetadata(
        ticker="NGX:NGX30",
        name="NGX 30 Index",
        asset_class="etf",
        currency=Currency.NGN,
        exchange="NGX",
    )
    interactor, trade_repo, asset_repo, yfinance, tiingo, ngnmarket = (
        _patch_import_deps(monkeypatch, ngnmarket_metadata=metadata)
    )
    csv_bytes = (
        b"Ticker,Type,Date,Quantity,Price,Currency,Asset Class,Market Data Provider\n"
        b"NGX:NGX30,buy,2024-01-01,10,1.00,NGN,etf,ngnmarket\n"
    )

    result = await interactor.confirm_import(
        csv_bytes,
        "trades.csv",
        {},
        "%Y-%m-%d",
        uuid4(),
        market_data_provider="yfinance",
    )

    assert result["imported_count"] == 1
    assert ngnmarket.calls == [("NGX:NGX30", "NGN")]
    assert tiingo.calls == []
    assert yfinance.calls == []
    assert trade_repo.added[0].ticker == "NGX:NGX30"
    assert trade_repo.added[0].market_data_provider == "ngnmarket"
    assert asset_repo.added[0].exchange == "NGX"
    assert asset_repo.added[0].market_data_provider == "ngnmarket"
