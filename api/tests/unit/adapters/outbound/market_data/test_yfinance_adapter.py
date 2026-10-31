from datetime import date

import pandas as pd
import pytest

from adapters.outbound.market_data import yfinance_adapter as yfinance_module
from adapters.outbound.market_data.yfinance_closes import last_close, valid_closes


def _frame(closes):
    """Daily history frame like yfinance returns; None becomes NaN."""
    index = pd.to_datetime(
        ["2026-10-28", "2026-10-29", "2026-10-30"][: len(closes)]
    ).tz_localize("America/New_York")
    return pd.DataFrame(
        {"Close": [float("nan") if c is None else c for c in closes]}, index=index
    )


class _FakeTicker:
    frame = _frame([])

    def __init__(self, _symbol):
        pass

    def history(self, **_kwargs):
        return _FakeTicker.frame


class _FakeCache:
    def __init__(self):
        self.prices = {}

    async def get_price(self, ticker):
        return self.prices.get(ticker)

    async def set_price(self, ticker, price_date, price):
        self.prices[ticker] = (price_date, price)


def _adapter(monkeypatch, closes):
    _FakeTicker.frame = _frame(closes)
    monkeypatch.setattr(yfinance_module.yf, "Ticker", _FakeTicker)
    monkeypatch.setattr(yfinance_module, "PriceCache", _FakeCache)
    return yfinance_module.YFinanceAdapter()


@pytest.mark.edge_case
def test_valid_closes_drops_incomplete_bars():
    closes = valid_closes(_frame([709.9, 0.0, None]))

    assert list(closes) == [709.9]
    assert last_close(_frame([709.9, 707.32, None])) == 707.32
    assert last_close(_frame([None])) is None
    assert last_close(None) is None
    assert valid_closes(pd.DataFrame()).empty


@pytest.mark.asyncio
@pytest.mark.edge_case
async def test_price_history_skips_nan_bar_instead_of_failing(monkeypatch):
    # Real case: yfinance returned 2026-10-30 with NaN prices but a volume.
    adapter = _adapter(monkeypatch, [709.9, 707.32, None])

    history = await adapter.get_price_history(
        "VOO", date(2026, 10, 1), date(2026, 10, 31)
    )

    assert history == [(date(2026, 10, 28), 70990), (date(2026, 10, 29), 70732)]


@pytest.mark.asyncio
@pytest.mark.edge_case
async def test_current_price_uses_last_complete_bar(monkeypatch):
    adapter = _adapter(monkeypatch, [709.9, 707.32, None])

    price = await adapter.get_current_price("VOO")

    assert price == (date(2026, 10, 29), 70732)
    assert adapter.cache.prices["VOO"] == (date(2026, 10, 29), 70732)


@pytest.mark.asyncio
@pytest.mark.grumpy_path
async def test_current_price_is_zero_when_no_complete_bar(monkeypatch):
    adapter = _adapter(monkeypatch, [None])

    _price_date, price = await adapter.get_current_price("VOO")

    assert price == 0
