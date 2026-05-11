from uuid import uuid4

import pytest

from application.trades import csv_import_interactor as csv_module
from domain.entities.models import Asset, Trade
from domain.value_objects.money import AssetClass


class FakeTradeRepository:
    def __init__(self):
        self.added = []

    async def add(self, trade: Trade) -> None:
        self.added.append(trade)


class FakeAssetRepository:
    def __init__(self):
        self.assets = {}
        self.added = []

    async def get_by_ticker(self, ticker: str):
        return self.assets.get(ticker)

    async def add(self, asset: Asset) -> None:
        self.assets[asset.ticker] = asset
        self.added.append(asset)


class FakeYFinanceAdapter:
    def __init__(self, metadata=None):
        self.metadata = metadata
        self.calls = []

    async def get_asset_metadata(self, ticker, currency):
        self.calls.append((ticker, currency))
        return self.metadata


def _patch_import_deps(monkeypatch, *, metadata=None):
    trade_repo = FakeTradeRepository()
    asset_repo = FakeAssetRepository()
    yfinance = FakeYFinanceAdapter(metadata)

    monkeypatch.setattr(csv_module, "TradeRepository", lambda session: trade_repo)
    monkeypatch.setattr(csv_module, "AssetRepository", lambda session: asset_repo)
    monkeypatch.setattr(csv_module, "YFinanceAdapter", lambda: yfinance)

    interactor = csv_module.CsvImportInteractor(session=object())
    return interactor, trade_repo, asset_repo, yfinance


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
    interactor, trade_repo, asset_repo, yfinance = _patch_import_deps(monkeypatch)
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
    assert yfinance.calls == []


@pytest.mark.asyncio
@pytest.mark.grumpy_path
async def test_confirm_import_rejects_when_asset_metadata_is_missing(monkeypatch):
    interactor, trade_repo, asset_repo, yfinance = _patch_import_deps(monkeypatch)
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
