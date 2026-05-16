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


class _FakeYFinanceTicker:
    """Mocks yf.Ticker for FX rate lookups in tests."""

    _fx_rates: dict[str, float] = {}  # ticker → close price
    _calls: list[str] = []

    @classmethod
    def set_rate(cls, ticker: str, close: float):
        cls._fx_rates[ticker] = close

    @classmethod
    def reset(cls):
        cls._fx_rates.clear()
        cls._calls.clear()

    def __init__(self, ticker: str):
        self._ticker = ticker
        _FakeYFinanceTicker._calls.append(ticker)

    def history(self, period: str = "1d"):
        import pandas as pd

        close_val = _FakeYFinanceTicker._fx_rates.get(self._ticker, 0.0)
        idx = pd.DatetimeIndex([pd.Timestamp("2024-01-01")])
        return pd.DataFrame({"Close": [close_val]}, index=idx)


class FakeTiingoAdapter:
    def __init__(self, price=12345):
        self.current_price_calls = []
        self._price = price

    async def get_current_price(self, symbol):
        self.current_price_calls.append(symbol)
        if self._price:
            return date(2024, 1, 1), self._price
        return date(2024, 1, 1), 0


class FakeNgnMarketAdapter:
    _SENTINEL = object()

    def __init__(self, chart_data=_SENTINEL):
        self.chart_calls = []
        self._chart_data = chart_data

    async def get_index_chart(self, symbol):
        self.chart_calls.append(symbol)
        if self._chart_data is not self._SENTINEL:
            return self._chart_data
        return {
            "data": [
                {"date": "2026-04-17", "index_value": 2841.45},
            ]
        }


class FakeTradingviewAdapter:
    def __init__(self, price=0):
        self.current_price_calls = []
        self._price = price

    async def get_current_price(self, ticker, currency="USD"):
        self.current_price_calls.append(ticker)
        if self._price:
            return date(2024, 1, 1), self._price
        return date(2024, 1, 1), 0


def _patch_analytics_deps(
    monkeypatch,
    *,
    trades=None,
    assets=None,
    latest=None,
    history=None,
    tiingo_price=12345,
    tradingview_price=0,
    ngnmarket_chart=True,
    base_currency=Currency.USD,
):
    trade_repo = FakeTradeRepository(trades)
    asset_repo = FakeAssetRepository(assets)
    price_repo = FakePriceRepository(latest=latest, history=history)
    yfinance = FakeYFinanceAdapter()
    tiingo = FakeTiingoAdapter(price=tiingo_price)
    ngnmarket = FakeNgnMarketAdapter(
        chart_data=(
            {
                "data": [
                    {"date": "2026-04-17", "index_value": 2841.45},
                ]
            }
            if ngnmarket_chart
            else None
        )
    )
    tradingview = FakeTradingviewAdapter(price=tradingview_price)

    monkeypatch.setattr(analytics_module, "TradeRepository", lambda session: trade_repo)
    monkeypatch.setattr(analytics_module, "AssetRepository", lambda session: asset_repo)
    monkeypatch.setattr(
        analytics_module, "PriceHistoryRepository", lambda session: price_repo
    )
    monkeypatch.setattr(analytics_module, "FxRateRepository", lambda session: object())
    monkeypatch.setattr(analytics_module, "YFinanceAdapter", lambda: yfinance)
    monkeypatch.setattr(analytics_module, "TiingoAdapter", lambda: tiingo)
    monkeypatch.setattr(analytics_module, "NgnMarketAdapter", lambda: ngnmarket)
    monkeypatch.setattr(analytics_module, "TradingviewAdapter", lambda: tradingview)

    interactor = analytics_module.AnalyticsInteractor(
        session=object(), portfolio_base_currency=base_currency
    )
    interactor.trade_repo = trade_repo
    interactor.asset_repo = asset_repo
    interactor.price_repo = price_repo
    interactor.yfinance = yfinance
    interactor.tiingo = tiingo
    interactor.ngnmarket = ngnmarket
    interactor.tradingview = tradingview
    interactor.base_currency = base_currency
    # Inject fake Ticker for FX rate lookups in _get_fx_rate
    interactor._fx_ticker_factory = _FakeYFinanceTicker
    # Reset class-level state between tests
    _FakeYFinanceTicker.reset()
    return (
        interactor,
        trade_repo,
        asset_repo,
        price_repo,
        yfinance,
        tiingo,
        ngnmarket,
        tradingview,
    )


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
        tiingo_price=0,
        ngnmarket_chart=False,
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
    async def _resolve_price_zero(_asset_id, _ticker, provider_hint=None):
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

    async def _resolve_price_zero(_asset_id, _ticker, provider_hint=None):
        return 0

    interactor._resolve_price = _resolve_price_zero

    result = await interactor.get_holdings(portfolio.id)

    assert len(result) == 1
    holding = result[0]
    assert holding["quantity"] == 0.1
    # remaining FIFO lot cost basis = 0.1 * 90,000 = 9,000
    assert Decimal(str(holding["cost_basis"])) == Decimal("9000")
    # avg price from holdings route math would be 9000 / 0.1 = 90,000


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_get_holdings_uses_trade_market_data_provider_for_price_source(
    monkeypatch,
):
    portfolio = Portfolio(
        id=uuid4(), user_id=uuid4(), name="Core", base_currency=Currency.USD
    )
    asset = Asset(
        id=uuid4(),
        ticker="BRK.B",
        name="Berkshire Hathaway B",
        asset_class=AssetClass.STOCK,
        currency=Currency.USD,
        market_data_provider="yfinance",
    )
    trades = [
        Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            ticker="BRK.B",
            trade_type=TradeType.BUY,
            trade_date=datetime(2025, 1, 1, 9, 30),
            quantity=10000,
            price=50000,
            trade_currency=Currency.USD,
            market_data_provider="tiingo",
        )
    ]

    interactor, _trade_repo, _asset_repo, _price_repo, yfinance, tiingo, _ngn, _tv = (
        _patch_analytics_deps(
            monkeypatch,
            trades=trades,
            assets={asset.id: asset},
            history={asset.id: []},
        )
    )

    holdings = await interactor.get_holdings(portfolio.id)

    assert len(holdings) == 1
    assert tiingo.current_price_calls == ["BRK-B"]


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_get_holdings_uses_tradingview_provider_for_price_source(
    monkeypatch,
):
    portfolio = Portfolio(
        id=uuid4(), user_id=uuid4(), name="Crypto", base_currency=Currency.USD
    )
    asset = Asset(
        id=uuid4(),
        ticker="BTC/USD",
        name="Bitcoin",
        asset_class=AssetClass.CRYPTO,
        currency=Currency.USD,
        market_data_provider="tradingview",
    )
    trades = [
        Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            ticker="BTC/USD",
            trade_type=TradeType.BUY,
            trade_date=datetime(2025, 3, 1, 9, 30),
            quantity=10000,
            price=6500000,
            trade_currency=Currency.USD,
            market_data_provider="tradingview",
        )
    ]

    interactor, _tr, _ar, _pr, _yf, _ti, _ng, tradingview = _patch_analytics_deps(
        monkeypatch,
        trades=trades,
        assets={asset.id: asset},
        history={asset.id: []},
        tiingo_price=0,
        ngnmarket_chart=False,
        tradingview_price=6800000,
    )

    holdings = await interactor.get_holdings(portfolio.id)

    assert len(holdings) == 1
    assert tradingview.current_price_calls == ["BTC/USD-USD"]
    assert holdings[0]["current_price"] == 68000.0


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_resolve_price_cascades_through_fallback_providers(monkeypatch):
    """When the primary provider returns 0, every other provider is tried in order."""
    portfolio = Portfolio(
        id=uuid4(), user_id=uuid4(), name="Mixed", base_currency=Currency.USD
    )
    asset = Asset(
        id=uuid4(),
        ticker="AAPL",
        name="Apple",
        asset_class=AssetClass.STOCK,
        currency=Currency.USD,
        market_data_provider="yfinance",
    )
    trades = [
        Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            ticker="AAPL",
            trade_type=TradeType.BUY,
            trade_date=datetime(2025, 3, 1, 9, 30),
            quantity=10000,
            price=19000,
            trade_currency=Currency.USD,
            market_data_provider="yfinance",
        )
    ]

    interactor, _tr, _ar, _pr, yfinance, tiingo, ngnmarket, tradingview = (
        _patch_analytics_deps(
            monkeypatch,
            trades=trades,
            assets={asset.id: asset},
            history={asset.id: []},
            tiingo_price=0,
            tradingview_price=0,
            ngnmarket_chart=False,
        )
    )

    holdings = await interactor.get_holdings(portfolio.id)

    assert len(holdings) == 1
    # yfinance returns 0, tiingo returns 0, tradingview returns 0, ngnmarket returns 0
    # so fallback to price history (empty) → 0
    assert holdings[0]["current_price"] == 0.0
    # Every provider was consulted
    assert yfinance.current_price_calls == ["AAPL"]
    assert tiingo.current_price_calls == ["AAPL"]
    assert tradingview.current_price_calls == ["AAPL"]
    assert ngnmarket.chart_calls == ["AAPL"]


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_get_holdings_converts_foreign_currency_to_base_currency(monkeypatch):
    """When a trade is in NGN and the portfolio base is USD, values are converted."""
    portfolio = Portfolio(
        id=uuid4(), user_id=uuid4(), name="Nigeria", base_currency=Currency.USD
    )
    asset = Asset(
        id=uuid4(),
        ticker="NGX:STANBICETF30",
        name="Stanbic ETF 30",
        asset_class=AssetClass.ETF,
        currency=Currency.NGN,
        market_data_provider="ngnmarket",
    )
    trades = [
        Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            ticker="NGX:STANBICETF30",
            trade_type=TradeType.BUY,
            trade_date=datetime(2025, 3, 1, 9, 30),
            quantity=10000,  # 1.0 units
            price=284145,  # 2841.45 NGN per unit
            trade_currency=Currency.NGN,
            market_data_provider="ngnmarket",
        )
    ]

    interactor, _tr, _ar, _pr, yfinance, _ti, ngnmarket, _tv = _patch_analytics_deps(
        monkeypatch,
        trades=trades,
        assets={asset.id: asset},
        history={asset.id: []},
        tiingo_price=0,
        ngnmarket_chart=True,
        tradingview_price=0,
    )

    # Simulate NGN→USD direct rate rounding to 0 (1 NGN ≈ 0.000645 USD → ×100 = 0)
    # So the adapter will try USD→NGN inverse: 1 USD = 1550 NGN
    _FakeYFinanceTicker.set_rate("USDNGN=X", 1550.0)

    holdings = await interactor.get_holdings(portfolio.id)

    assert len(holdings) == 1
    # NGN→USD direct rate is 0 (no data), so inverse USD→NGN=1550 is used.
    # Conversion: value_ngn * 100 / 155000 = value_usd
    # current_price: 284145 * 100 // 155000 = 183 (×100), /100 = 1.83
    # market_value: same as current_price since 1 unit
    assert holdings[0]["current_price"] == 1.83
    assert holdings[0]["market_value"] == 1.83
    # Should have tried NGNUSD=X first (no data → 0), then USDNGN=X (1550)
    assert _FakeYFinanceTicker._calls == ["NGNUSD=X", "USDNGN=X"]


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_get_holdings_converts_with_direct_rate_when_nonzero(monkeypatch):
    """When the direct rate is non-zero (strong→weak), use multiplication."""
    portfolio = Portfolio(
        id=uuid4(), user_id=uuid4(), name="US", base_currency=Currency.NGN
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
            trade_date=datetime(2025, 3, 1, 9, 30),
            quantity=10000,
            price=19000,  # $190.00
            trade_currency=Currency.USD,
        )
    ]

    interactor, _tr, _ar, _pr, yfinance, _ti, _ng, _tv = _patch_analytics_deps(
        monkeypatch,
        trades=trades,
        assets={asset.id: asset},
        history={asset.id: []},
        tiingo_price=19000,  # provide a price via tiingo cascade
        ngnmarket_chart=False,
        tradingview_price=0,
        base_currency=Currency.NGN,
    )

    # Direct USD→NGN rate: 1 USD = 1550 NGN
    _FakeYFinanceTicker.set_rate("USDNGN=X", 1550.0)

    holdings = await interactor.get_holdings(portfolio.id)

    assert len(holdings) == 1
    # USD→NGN direct: 19000 * 1550 * 100 // 100... wait:
    # price=19000 (×100 = $190), rate=1550 (×100 = 155000 after round)
    # Conversion: 19000 USD * 155000 // 100 = 29450000 (×100 NGN)
    # /100 = 294500 NGN
    assert holdings[0]["current_price"] == 294500.0
    assert _FakeYFinanceTicker._calls == ["USDNGN=X"]


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_get_holdings_skips_fx_conversion_when_currencies_match(monkeypatch):
    """When trade and portfolio are both USD, no FX conversion is performed."""
    portfolio = Portfolio(
        id=uuid4(), user_id=uuid4(), name="US", base_currency=Currency.USD
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
            trade_date=datetime(2025, 3, 1, 9, 30),
            quantity=10000,
            price=19000,
            trade_currency=Currency.USD,
        )
    ]

    interactor, _tr, _ar, _pr, yfinance, _ti, _ng, _tv = _patch_analytics_deps(
        monkeypatch,
        trades=trades,
        assets={asset.id: asset},
        history={asset.id: []},
        tiingo_price=0,
        ngnmarket_chart=False,
        tradingview_price=0,
    )

    holdings = await interactor.get_holdings(portfolio.id)

    assert len(holdings) == 1
    # No FX rate lookup should happen (USD == USD)
    assert _FakeYFinanceTicker._calls == []


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_get_holdings_multi_currency_btc_trades(monkeypatch):
    """BTC-USD with trades in both USD and GBP should compute correct cost basis."""
    portfolio = Portfolio(
        id=uuid4(), user_id=uuid4(), name="Mixed", base_currency=Currency.USD
    )
    asset = Asset(
        id=uuid4(),
        ticker="BTC-USD",
        name="Bitcoin",
        asset_class=AssetClass.CRYPTO,
        currency=Currency.USD,  # asset is priced in USD
    )
    # Buy 0.1 BTC @ $80,000 (USD)  +  Buy 0.1 BTC @ £60,000 (GBP)
    # Cost: 0.1×$80,000=$8,000 + 0.1×£60,000=$7,620(GBP→USD) = $15,620
    # Current price: $85,000
    # Value: 0.2 BTC × $85,000 = $17,000
    trades = [
        Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            ticker="BTC-USD",
            trade_type=TradeType.BUY,
            trade_date=datetime(2025, 1, 1, 9, 30),
            quantity=1000,  # 0.1 BTC
            price=8000000,  # $80,000.00 per BTC
            trade_currency=Currency.USD,
        ),
        Trade(
            id=uuid4(),
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            ticker="BTC-USD",
            trade_type=TradeType.BUY,
            trade_date=datetime(2025, 1, 2, 9, 30),
            quantity=1000,  # 0.1 BTC
            price=6000000,  # £60,000.00 per BTC
            trade_currency=Currency.GBP,
        ),
    ]

    interactor, _tr, _ar, _pr, yfinance, _ti, _ng, _tv = _patch_analytics_deps(
        monkeypatch,
        trades=trades,
        assets={asset.id: asset},
        history={asset.id: []},
        tiingo_price=8500000,  # $85,000.00 current price via cascade
        ngnmarket_chart=False,
        tradingview_price=0,
    )

    # GBP→USD rate: 1 GBP = 1.27 USD
    _FakeYFinanceTicker.set_rate("GBPUSD=X", 1.27)

    holdings = await interactor.get_holdings(portfolio.id)

    assert len(holdings) == 1
    h = holdings[0]

    # Quantity: 0.1 + 0.1 = 0.2 BTC
    assert h["quantity"] == 0.2

    # Current price: $85,000 (in USD, no conversion needed since asset=USD, base=USD)
    assert h["current_price"] == 85000.0

    # Market value: 0.2 × $85,000 = $17,000
    assert h["market_value"] == 17000.0

    # Cost basis:
    #   Lot 1: 0.1 × $80,000 = $8,000 (already USD, no conversion)
    #   Lot 2: 0.1 × £60,000 = £6,000 → $7,620 (GBP→USD at 1.27)
    #   Total cost basis: $8,000 + $7,620 = $15,620
    assert h["cost_basis"] == 15620.0

    # Total return: $17,000 - $15,620 = $1,380
    assert h["total_return"] == 1380.0

    # FX calls: only GBPUSD=X (USDUSD=X is skipped since same currency)
    assert _FakeYFinanceTicker._calls == ["GBPUSD=X"]
