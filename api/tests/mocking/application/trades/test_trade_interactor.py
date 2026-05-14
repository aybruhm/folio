from dataclasses import replace
from datetime import date, datetime
from uuid import uuid4

import pytest

from application.trades import trade_interactor as trade_module
from domain.entities.models import Asset, Portfolio, Trade
from domain.ports.inbound.use_cases import CreateTradeRequest
from domain.value_objects.money import AssetClass, AssetMetadata, Currency, TradeType


class FakePortfolioRepository:
    def __init__(self, portfolio=None):
        self.portfolio = portfolio

    async def get_by_id(self, portfolio_id):
        if self.portfolio and self.portfolio.id == portfolio_id:
            return self.portfolio
        return None


class FakeAssetRepository:
    def __init__(self, asset=None):
        self.assets = {}
        self.added = []
        self.updated = []
        if asset is not None:
            self.assets[asset.ticker] = asset

    async def add(self, asset: Asset) -> None:
        self.assets[asset.ticker] = asset
        self.added.append(asset)

    async def get_by_ticker(self, ticker: str):
        return self.assets.get(ticker)

    async def update_classification(
        self, asset_id, asset_class, currency, market_data_provider="yfinance"
    ):
        asset = next(item for item in self.assets.values() if item.id == asset_id)
        updated = replace(
            asset,
            asset_class=AssetClass(asset_class),
            currency=Currency(currency),
            market_data_provider=market_data_provider,
        )
        self.assets[updated.ticker] = updated
        self.updated.append(updated)


class FakeTradeRepository:
    def __init__(self):
        self.trades = {}
        self.added = []
        self.updated = []
        self.deleted = []

    async def add(self, trade: Trade) -> None:
        self.trades[trade.id] = trade
        self.added.append(trade)

    async def get_by_id(self, trade_id):
        return self.trades.get(trade_id)

    async def list_by_portfolio(
        self,
        portfolio_id,
        ticker=None,
        trade_type=None,
        start_date=None,
        end_date=None,
        skip=0,
        limit=100,
    ):
        trades = [t for t in self.trades.values() if t.portfolio_id == portfolio_id]
        if ticker:
            normalized = ticker.lower()
            trades = [t for t in trades if normalized in t.ticker.lower()]
        if trade_type:
            trades = [t for t in trades if t.trade_type == trade_type]
        if start_date:
            trades = [
                t
                for t in trades
                if (
                    t.trade_date.date()
                    if hasattr(t.trade_date, "date")
                    else t.trade_date
                )
                >= start_date
            ]
        if end_date:
            trades = [
                t
                for t in trades
                if (
                    t.trade_date.date()
                    if hasattr(t.trade_date, "date")
                    else t.trade_date
                )
                <= end_date
            ]
        total = len(trades)
        return trades[skip : skip + limit], total

    async def update(self, trade: Trade) -> None:
        self.trades[trade.id] = trade
        self.updated.append(trade)

    async def delete(self, trade_id) -> None:
        self.deleted.append(trade_id)
        self.trades.pop(trade_id, None)


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


def _patch_trade_deps(
    monkeypatch,
    *,
    portfolio=None,
    asset=None,
    yfinance_metadata=None,
    tiingo_metadata=None,
    ngnmarket_metadata=None,
):
    portfolio_repo = FakePortfolioRepository(portfolio)
    asset_repo = FakeAssetRepository(asset)
    trade_repo = FakeTradeRepository()
    yfinance = FakeYFinanceAdapter(yfinance_metadata)
    tiingo = FakeTiingoAdapter(tiingo_metadata)
    ngnmarket = FakeNgnMarketAdapter(ngnmarket_metadata)

    monkeypatch.setattr(
        trade_module, "PortfolioRepository", lambda session: portfolio_repo
    )
    monkeypatch.setattr(trade_module, "AssetRepository", lambda session: asset_repo)
    monkeypatch.setattr(trade_module, "TradeRepository", lambda session: trade_repo)
    monkeypatch.setattr(trade_module, "YFinanceAdapter", lambda: yfinance)
    monkeypatch.setattr(trade_module, "TiingoAdapter", lambda: tiingo)
    monkeypatch.setattr(trade_module, "NgnMarketAdapter", lambda: ngnmarket)

    interactor = trade_module.TradeInteractor(session=object())
    return (
        interactor,
        portfolio_repo,
        asset_repo,
        trade_repo,
        yfinance,
        tiingo,
        ngnmarket,
    )


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_create_trade_creates_cash_asset_without_yfinance(monkeypatch):
    portfolio = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Cash",
        base_currency=Currency.USD,
    )
    (
        interactor,
        _portfolio_repo,
        asset_repo,
        trade_repo,
        yfinance,
        _tiingo,
        _ngnmarket,
    ) = _patch_trade_deps(monkeypatch, portfolio=portfolio)
    request = CreateTradeRequest(
        portfolio_id=portfolio.id,
        ticker="CASH",
        trade_type=TradeType.BUY,
        trade_date=datetime(2024, 1, 1, 9, 30),
        quantity=100000,
        price=100,
        trade_currency=Currency.USD,
        asset_class=AssetClass.CASH,
    )

    trade_id = await interactor.create_trade(request)

    assert yfinance.calls == []
    assert asset_repo.added[0].asset_class == AssetClass.CASH
    assert trade_repo.added[0].id == trade_id
    assert trade_repo.added[0].market_data_provider == "yfinance"
    assert trade_repo.added[0].asset_id == asset_repo.added[0].id


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_create_trade_fetches_metadata_and_adds_asset_when_missing(monkeypatch):
    portfolio = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Equities",
        base_currency=Currency.USD,
    )
    metadata = AssetMetadata(
        ticker="AAPL",
        name="Apple Inc.",
        asset_class="stock",
        currency=Currency.USD,
        exchange="NASDAQ",
    )
    (
        interactor,
        _portfolio_repo,
        asset_repo,
        trade_repo,
        yfinance,
        _tiingo,
        _ngnmarket,
    ) = _patch_trade_deps(monkeypatch, portfolio=portfolio, yfinance_metadata=metadata)
    request = CreateTradeRequest(
        portfolio_id=portfolio.id,
        ticker="AAPL",
        trade_type=TradeType.BUY,
        trade_date=datetime(2024, 1, 2, 9, 30),
        quantity=100000,
        price=18520,
        trade_currency=Currency.USD,
    )

    trade_id = await interactor.create_trade(request)

    assert yfinance.calls == [("AAPL", "USD")]
    assert asset_repo.added[0].name == "Apple Inc."
    assert trade_repo.added[0].id == trade_id
    assert trade_repo.added[0].market_data_provider == "yfinance"


@pytest.mark.asyncio
@pytest.mark.grumpy_path
async def test_create_trade_raises_when_portfolio_missing(monkeypatch):
    (
        interactor,
        _portfolio_repo,
        _asset_repo,
        _trade_repo,
        _yfinance,
        _tiingo,
        _ngnmarket,
    ) = _patch_trade_deps(monkeypatch)
    request = CreateTradeRequest(
        portfolio_id=uuid4(),
        ticker="AAPL",
        trade_type=TradeType.BUY,
        trade_date=datetime(2024, 1, 2, 9, 30),
        quantity=100000,
        price=18520,
        trade_currency=Currency.USD,
    )

    with pytest.raises(ValueError, match="Portfolio"):
        await interactor.create_trade(request)


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_create_trade_updates_existing_asset_classification_when_metadata_changes(
    monkeypatch,
):
    portfolio = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Mixed",
        base_currency=Currency.USD,
    )
    existing_asset = Asset(
        id=uuid4(),
        ticker="AAPL",
        name="Apple",
        asset_class=AssetClass.STOCK,
        currency=Currency.USD,
    )
    metadata = AssetMetadata(
        ticker="AAPL",
        name="Apple Inc.",
        asset_class="etf",
        currency=Currency.EUR,
        exchange="NASDAQ",
    )
    (
        interactor,
        _portfolio_repo,
        asset_repo,
        trade_repo,
        yfinance,
        _tiingo,
        _ngnmarket,
    ) = _patch_trade_deps(
        monkeypatch,
        portfolio=portfolio,
        asset=existing_asset,
        yfinance_metadata=metadata,
    )
    request = CreateTradeRequest(
        portfolio_id=portfolio.id,
        ticker="AAPL",
        trade_type=TradeType.BUY,
        trade_date=datetime(2024, 1, 3, 9, 30),
        quantity=100000,
        price=20000,
        trade_currency=Currency.EUR,
    )

    trade_id = await interactor.create_trade(request)

    assert yfinance.calls == [("AAPL", "EUR")]
    assert asset_repo.updated[0].asset_class == AssetClass.ETF
    assert asset_repo.updated[0].currency == Currency.EUR
    assert asset_repo.updated[0].market_data_provider == "yfinance"
    assert trade_repo.added[0].id == trade_id


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_get_trade_serializes_model(monkeypatch):
    portfolio = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Core",
        base_currency=Currency.USD,
    )
    trade = Trade(
        id=uuid4(),
        portfolio_id=portfolio.id,
        asset_id=uuid4(),
        ticker="AAPL",
        trade_type=TradeType.BUY,
        trade_date=datetime(2024, 1, 4, 9, 30),
        quantity=100000,
        price=18520,
        trade_currency=Currency.USD,
        fees=495,
        created_at=datetime(2024, 1, 4, 9, 31),
    )
    (
        interactor,
        _portfolio_repo,
        _asset_repo,
        trade_repo,
        _yfinance,
        _tiingo,
        _ngnmarket,
    ) = _patch_trade_deps(monkeypatch, portfolio=portfolio)
    trade_repo.trades[trade.id] = trade

    result = await interactor.get_trade(trade.id)

    assert result["id"] == str(trade.id)
    assert result["ticker"] == "AAPL"
    assert result["quantity"] == 10.0
    assert result["price"] == 185.2
    assert result["fees"] == 4.95


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_list_trades_filters_by_ticker_type_and_dates(monkeypatch):
    portfolio = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Core",
        base_currency=Currency.USD,
    )
    (
        interactor,
        _portfolio_repo,
        _asset_repo,
        trade_repo,
        _yfinance,
        _tiingo,
        _ngnmarket,
    ) = _patch_trade_deps(monkeypatch, portfolio=portfolio)
    common_asset_id = uuid4()
    trade_repo.trades = {
        uuid4(): Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=common_asset_id,
            ticker="AAPL",
            trade_type=TradeType.BUY,
            trade_date=datetime(2024, 1, 5, 9, 30),
            quantity=100000,
            price=18520,
            trade_currency=Currency.USD,
        ),
        uuid4(): Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=common_asset_id,
            ticker="MSFT",
            trade_type=TradeType.SELL,
            trade_date=datetime(2024, 2, 5, 9, 30),
            quantity=50000,
            price=37400,
            trade_currency=Currency.USD,
        ),
    }

    trades, total = await interactor.list_trades(
        portfolio_id=portfolio.id,
        ticker="AAPL",
        trade_type=TradeType.BUY,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
    )

    assert total == 1
    assert trades[0]["ticker"] == "AAPL"


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_update_trade_updates_fields(monkeypatch):
    portfolio = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Core",
        base_currency=Currency.USD,
    )
    existing_asset = Asset(
        id=uuid4(),
        ticker="AAPL",
        name="Apple",
        asset_class=AssetClass.STOCK,
        currency=Currency.USD,
    )
    trade = Trade(
        id=uuid4(),
        portfolio_id=portfolio.id,
        asset_id=existing_asset.id,
        ticker="AAPL",
        trade_type=TradeType.BUY,
        trade_date=datetime(2024, 1, 4, 9, 30),
        quantity=100000,
        price=18520,
        trade_currency=Currency.USD,
    )
    metadata = AssetMetadata(
        ticker="AAPL",
        name="Apple Inc.",
        asset_class="etf",
        currency=Currency.EUR,
        exchange="NASDAQ",
    )
    (
        interactor,
        _portfolio_repo,
        asset_repo,
        trade_repo,
        _yfinance,
        _tiingo,
        _ngnmarket,
    ) = _patch_trade_deps(
        monkeypatch,
        portfolio=portfolio,
        asset=existing_asset,
        yfinance_metadata=metadata,
    )
    trade_repo.trades[trade.id] = trade

    request = CreateTradeRequest(
        portfolio_id=portfolio.id,
        ticker="AAPL",
        trade_type=TradeType.SELL,
        trade_date=datetime(2024, 1, 6, 9, 30),
        quantity=75000,
        price=19000,
        trade_currency=Currency.EUR,
        fees=250,
    )

    await interactor.update_trade(trade.id, request)

    updated = trade_repo.trades[trade.id]
    assert updated.trade_type == TradeType.SELL
    assert updated.quantity == 75000
    assert updated.price == 19000
    assert updated.trade_currency == Currency.EUR
    assert asset_repo.updated[0].asset_class == AssetClass.ETF


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_delete_trade_removes_trade(monkeypatch):
    portfolio = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Core",
        base_currency=Currency.USD,
    )
    (
        interactor,
        _portfolio_repo,
        _asset_repo,
        trade_repo,
        _yfinance,
        _tiingo,
        _ngnmarket,
    ) = _patch_trade_deps(monkeypatch, portfolio=portfolio)
    trade = Trade(
        id=uuid4(),
        portfolio_id=portfolio.id,
        asset_id=uuid4(),
        ticker="AAPL",
        trade_type=TradeType.BUY,
        trade_date=datetime(2024, 1, 4, 9, 30),
        quantity=100000,
        price=18520,
        trade_currency=Currency.USD,
    )
    trade_repo.trades[trade.id] = trade

    await interactor.delete_trade(trade.id)

    assert trade.id not in trade_repo.trades
    assert trade_repo.deleted == [trade.id]


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_create_trade_uses_ngnmarket_provider_when_selected(monkeypatch):
    portfolio = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Nigeria",
        base_currency=Currency.NGN,
    )
    metadata = AssetMetadata(
        ticker="NGX:NGX30",
        name="NGX 30 Index",
        asset_class="etf",
        currency=Currency.NGN,
        exchange="NGX",
    )
    (
        interactor,
        _portfolio_repo,
        asset_repo,
        trade_repo,
        yfinance,
        tiingo,
        ngnmarket,
    ) = _patch_trade_deps(
        monkeypatch,
        portfolio=portfolio,
        ngnmarket_metadata=metadata,
    )

    request = CreateTradeRequest(
        portfolio_id=portfolio.id,
        ticker="NGX:NGX30",
        trade_type=TradeType.BUY,
        trade_date=datetime(2024, 1, 7, 9, 30),
        quantity=100000,
        price=20000,
        trade_currency=Currency.NGN,
        market_data_provider="ngnmarket",
    )

    trade_id = await interactor.create_trade(request)

    assert ngnmarket.calls == [("NGX:NGX30", "NGN")]
    assert tiingo.calls == []
    assert yfinance.calls == []
    assert asset_repo.added[0].exchange == "NGX"
    assert trade_repo.added[0].id == trade_id
    assert trade_repo.added[0].market_data_provider == "ngnmarket"
