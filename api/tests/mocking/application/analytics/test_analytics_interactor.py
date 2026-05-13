from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from application.analytics import analytics_interactor as analytics_module
from domain.entities.models import Asset, Portfolio, Trade
from domain.value_objects.money import AssetClass, Currency, TradeType


class FakeTradeRepository:
    def __init__(self, trades=None):
        self.trades = trades or []

    async def list_by_portfolio(self, portfolio_id, skip=0, limit=100):
        filtered = [t for t in self.trades if t.portfolio_id == portfolio_id]
        return filtered[skip : skip + limit], len(filtered)


class FakeAssetRepository:
    def __init__(self, assets=None):
        self.assets_by_id = assets or {}
        self.assets_by_ticker = {
            asset.ticker: asset for asset in self.assets_by_id.values()
        }

    async def get_by_id(self, asset_id):
        return self.assets_by_id.get(asset_id)

    async def get_by_ticker(self, ticker):
        return self.assets_by_ticker.get(ticker)


class FakePriceRepository:
    def __init__(self, latest=None, history=None):
        self.latest = latest or {}
        self.history = history or {}

    async def get_latest(self, asset_id):
        return self.latest.get(asset_id)

    async def get_history(self, asset_id, start, end):
        return self.history.get(asset_id, [])


class FakeYFinanceAdapter:
    def __init__(self):
        self.current_price_calls = []
        self.price_history_calls = []

    async def get_current_price(self, symbol):
        self.current_price_calls.append(symbol)
        return date(2024, 1, 1), 0

    async def get_price_history(self, ticker, start, end):
        self.price_history_calls.append((ticker, start, end))
        return []


def _patch_analytics_deps(
    monkeypatch, *, trades=None, assets=None, latest=None, history=None
):
    trade_repo = FakeTradeRepository(trades)
    asset_repo = FakeAssetRepository(assets)
    price_repo = FakePriceRepository(latest=latest, history=history)
    yfinance = FakeYFinanceAdapter()

    monkeypatch.setattr(analytics_module, "TradeRepository", lambda session: trade_repo)
    monkeypatch.setattr(analytics_module, "AssetRepository", lambda session: asset_repo)
    monkeypatch.setattr(
        analytics_module, "PriceHistoryRepository", lambda session: price_repo
    )
    monkeypatch.setattr(analytics_module, "FxRateRepository", lambda session: object())
    monkeypatch.setattr(analytics_module, "YFinanceAdapter", lambda: yfinance)

    interactor = analytics_module.AnalyticsInteractor(
        session=object(), portfolio_base_currency=Currency.USD
    )
    interactor.trade_repo = trade_repo
    interactor.asset_repo = asset_repo
    interactor.price_repo = price_repo
    interactor.yfinance = yfinance
    return interactor, trade_repo, asset_repo, price_repo, yfinance


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_get_holdings_uses_cash_valuation_and_price_fallback(monkeypatch):
    portfolio = Portfolio(
        id=uuid4(), user_id=uuid4(), name="Core", base_currency=Currency.USD
    )
    cash_asset = Asset(
        id=uuid4(),
        ticker="CASH",
        name="Cash",
        asset_class=AssetClass.CASH,
        currency=Currency.USD,
    )
    stock_asset = Asset(
        id=uuid4(),
        ticker="AAPL",
        name="Apple",
        asset_class=AssetClass.STOCK,
        currency=Currency.USD,
    )
    trades = [
        Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=cash_asset.id,
            ticker="CASH",
            trade_type=TradeType.BUY,
            trade_date=datetime(2024, 1, 1, 9, 30),
            quantity=1000,
            price=100,
            trade_currency=Currency.USD,
        ),
        Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=stock_asset.id,
            ticker="AAPL",
            trade_type=TradeType.BUY,
            trade_date=datetime(2024, 1, 2, 9, 30),
            quantity=1000,
            price=18520,
            trade_currency=Currency.USD,
        ),
    ]
    latest = {stock_asset.id: (date(2024, 1, 3), 19000)}
    interactor, *_ = _patch_analytics_deps(
        monkeypatch,
        trades=trades,
        assets={cash_asset.id: cash_asset, stock_asset.id: stock_asset},
        latest=latest,
    )

    result = await interactor.get_holdings(portfolio.id)

    assert len(result) == 2
    cash = next(item for item in result if item["ticker"] == "CASH")
    stock = next(item for item in result if item["ticker"] == "AAPL")
    assert cash["market_value"] == cash["cost_basis"]
    assert stock["current_price"] == 190.0


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_calculate_performance_returns_zero_when_no_trades(monkeypatch):
    portfolio = Portfolio(
        id=uuid4(), user_id=uuid4(), name="Core", base_currency=Currency.USD
    )
    interactor, *_ = _patch_analytics_deps(monkeypatch, trades=[], assets={})

    result = await interactor.calculate_performance(portfolio.id)

    assert result == {"twr": "0", "mwr": "0"}


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_get_benchmark_comparison_uses_portfolio_performance_and_requests_prices(
    monkeypatch,
):
    portfolio = Portfolio(
        id=uuid4(), user_id=uuid4(), name="Core", base_currency=Currency.USD
    )
    interactor, *_ = _patch_analytics_deps(monkeypatch, trades=[], assets={})

    async def fake_calculate_performance(portfolio_id, start_date=None, end_date=None):
        return {"twr": "12.5"}

    interactor.calculate_performance = fake_calculate_performance

    result = await interactor.get_benchmark_comparison(portfolio.id, ["SPY", "QQQ"])

    assert result["portfolio_twr"] == "12.5"
    assert set(result["benchmarks"].keys()) == {"SPY", "QQQ"}
    assert interactor.yfinance.price_history_calls[0][0] == "SPY"


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_get_holdings_cash_roundtrip_results_in_no_remaining_position(
    monkeypatch,
):
    portfolio = Portfolio(
        id=uuid4(), user_id=uuid4(), name="Cash", base_currency=Currency.USD
    )
    cash_asset = Asset(
        id=uuid4(),
        ticker="RCASH.CST",
        name="Cash Bucket",
        asset_class=AssetClass.CASH,
        currency=Currency.USD,
    )
    trades = [
        Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=cash_asset.id,
            ticker="RCASH.CST",
            trade_type=TradeType.BUY,
            trade_date=datetime(2025, 1, 10, 9, 30),
            quantity=10000,
            price=658235,
            trade_currency=Currency.USD,
        ),
        Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=cash_asset.id,
            ticker="RCASH.CST",
            trade_type=TradeType.SELL,
            trade_date=datetime(2025, 2, 10, 9, 30),
            quantity=10000,
            price=658235,
            trade_currency=Currency.USD,
        ),
    ]

    interactor, *_ = _patch_analytics_deps(
        monkeypatch,
        trades=trades,
        assets={cash_asset.id: cash_asset},
    )

    result = await interactor.get_holdings(portfolio.id)

    assert result == []


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_calculate_performance_cash_roundtrip_is_neutral(monkeypatch):
    portfolio = Portfolio(
        id=uuid4(), user_id=uuid4(), name="Cash", base_currency=Currency.USD
    )
    cash_asset = Asset(
        id=uuid4(),
        ticker="RCASH.CST",
        name="Cash Bucket",
        asset_class=AssetClass.CASH,
        currency=Currency.USD,
    )
    trades = [
        Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=cash_asset.id,
            ticker="RCASH.CST",
            trade_type=TradeType.BUY,
            trade_date=datetime(2025, 1, 10, 9, 30),
            quantity=10000,
            price=658235,
            trade_currency=Currency.USD,
        ),
        Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=cash_asset.id,
            ticker="RCASH.CST",
            trade_type=TradeType.SELL,
            trade_date=datetime(2025, 2, 10, 9, 30),
            quantity=10000,
            price=658235,
            trade_currency=Currency.USD,
        ),
    ]

    interactor, *_ = _patch_analytics_deps(
        monkeypatch,
        trades=trades,
        assets={cash_asset.id: cash_asset},
    )

    perf = await interactor.calculate_performance(portfolio.id)

    assert float(perf["twr"]) == 0.0
    assert abs(float(perf["mwr"])) <= 0.01


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_get_performance_history_uses_trade_price_fallback_when_history_missing(
    monkeypatch,
):
    portfolio = Portfolio(
        id=uuid4(), user_id=uuid4(), name="Core", base_currency=Currency.USD
    )
    asset = Asset(
        id=uuid4(),
        ticker="AAPL",
        name="Apple",
        asset_class=AssetClass.STOCK,
        currency=Currency.USD,
    )
    trades = [
        Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            ticker="AAPL",
            trade_type=TradeType.BUY,
            trade_date=datetime(2025, 4, 10, 9, 30),
            quantity=10000,
            price=18520,
            trade_currency=Currency.USD,
        )
    ]

    interactor, *_ = _patch_analytics_deps(
        monkeypatch,
        trades=trades,
        assets={asset.id: asset},
        history={asset.id: []},
    )

    # Ensure last fallback doesn't interfere with this check
    async def _resolve_price_zero(_asset_id, _ticker):
        return 0

    interactor._resolve_price = _resolve_price_zero

    result = await interactor.get_performance_history(portfolio.id)

    assert len(result) > 0
    assert any(Decimal(str(point["value"])) > 0 for point in result)


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_get_performance_history_cash_uses_net_amount_not_unit_count(monkeypatch):
    portfolio = Portfolio(
        id=uuid4(), user_id=uuid4(), name="Cash", base_currency=Currency.USD
    )
    cash_asset = Asset(
        id=uuid4(),
        ticker="RCASH.CST",
        name="Cash Bucket",
        asset_class=AssetClass.CASH,
        currency=Currency.USD,
    )
    trades = [
        Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=cash_asset.id,
            ticker="RCASH.CST",
            trade_type=TradeType.BUY,
            trade_date=datetime(2025, 4, 9, 9, 30),
            quantity=10000,
            price=414,
            trade_currency=Currency.USD,
        ),
        Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=cash_asset.id,
            ticker="RCASH.CST",
            trade_type=TradeType.BUY,
            trade_date=datetime(2025, 4, 29, 9, 30),
            quantity=10000,
            price=73081,
            trade_currency=Currency.USD,
        ),
    ]

    interactor, *_ = _patch_analytics_deps(
        monkeypatch,
        trades=trades,
        assets={cash_asset.id: cash_asset},
    )

    result = await interactor.get_performance_history(portfolio.id)

    apr_points = [p for p in result if p["name"] == "Apr 2025"]
    assert len(apr_points) == 1
    # 4.14 + 730.81 = 734.95
    assert Decimal(str(apr_points[0]["value"])) == Decimal("734.95")


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_get_holdings_uses_fifo_cost_basis_for_remaining_position(monkeypatch):
    portfolio = Portfolio(
        id=uuid4(), user_id=uuid4(), name="BTC", base_currency=Currency.USD
    )
    btc_asset = Asset(
        id=uuid4(),
        ticker="BTC-USD",
        name="Bitcoin",
        asset_class=AssetClass.CRYPTO,
        currency=Currency.USD,
    )

    # Buy 0.1 @ 80,000 then buy 0.1 @ 90,000, then sell 0.1.
    # FIFO leaves the second lot (0.1 @ 90,000) as open position.
    trades = [
        Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=btc_asset.id,
            ticker="BTC-USD",
            trade_type=TradeType.BUY,
            trade_date=datetime(2025, 1, 1, 9, 30),
            quantity=1000,
            price=8000000,
            trade_currency=Currency.USD,
        ),
        Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=btc_asset.id,
            ticker="BTC-USD",
            trade_type=TradeType.BUY,
            trade_date=datetime(2025, 1, 2, 9, 30),
            quantity=1000,
            price=9000000,
            trade_currency=Currency.USD,
        ),
        Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=btc_asset.id,
            ticker="BTC-USD",
            trade_type=TradeType.SELL,
            trade_date=datetime(2025, 1, 3, 9, 30),
            quantity=1000,
            price=9500000,
            trade_currency=Currency.USD,
        ),
    ]

    interactor, *_ = _patch_analytics_deps(
        monkeypatch,
        trades=trades,
        assets={btc_asset.id: btc_asset},
        latest={btc_asset.id: (date(2025, 1, 4), 8000000)},
    )

    async def _resolve_price_zero(_asset_id, _ticker):
        return 0

    interactor._resolve_price = _resolve_price_zero

    result = await interactor.get_holdings(portfolio.id)

    assert len(result) == 1
    holding = result[0]
    assert holding["quantity"] == 0.1
    # remaining FIFO lot cost basis = 0.1 * 90,000 = 9,000
    assert Decimal(str(holding["cost_basis"])) == Decimal("9000")
    # avg price from holdings route math would be 9000 / 0.1 = 90,000
