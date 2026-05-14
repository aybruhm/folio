from datetime import date

import aiohttp
import pytest

from adapters.outbound.market_data import ngnmarket_adapter as ngn_module
from domain.value_objects.money import Currency


@pytest.mark.asyncio
async def test_get_asset_metadata_from_index_detail(monkeypatch):
    monkeypatch.setattr(
        ngn_module.settings,
        "NGNMARKET_API_BASE_URL",
        "https://api.ngnmarket.com/v1",
        raising=False,
    )
    monkeypatch.setattr(
        ngn_module.settings,
        "NGNMARKET_API_KEY",
        "test-ngn-key",
        raising=False,
    )

    adapter = ngn_module.NgnMarketAdapter()

    async def fake_get_index_detail(symbol: str):
        assert symbol == "NGX30"
        return {
            "symbol": "NGX30",
            "name": "NGX 30 Index",
            "description": "Top 30 companies",
        }

    monkeypatch.setattr(adapter, "get_index_detail", fake_get_index_detail)

    metadata = await adapter.get_asset_metadata("NGX:NGX30", "NGN")

    assert metadata is not None
    assert metadata.ticker == "NGX:NGX30"
    assert metadata.name == "NGX 30 Index"
    assert metadata.asset_class == "etf"
    assert metadata.currency == Currency.NGN
    assert metadata.exchange == "NGX"
    assert metadata.country == "NG"


@pytest.mark.asyncio
async def test_get_current_rate_inverts_when_target_is_base():
    adapter = ngn_module.NgnMarketAdapter()

    async def fake_current_forex():
        return {
            "base": "NGN",
            "rates": {
                "USD": 0.000623,
                "EUR": 0.000572,
            },
        }

    adapter.get_current_forex_rates = fake_current_forex  # type: ignore[method-assign]

    rate = await adapter.get_current_rate(Currency.USD, Currency.NGN)

    assert rate is not None
    assert abs((rate / 100) - (1 / 0.000623)) < 0.1


@pytest.mark.asyncio
async def test_get_fx_rate_uses_history_rows():
    adapter = ngn_module.NgnMarketAdapter()

    async def fake_history(source, target, start_date=None, end_date=None):
        assert source == Currency.USD
        assert target == Currency.NGN
        assert start_date == date(2026, 4, 17)
        return [
            {"date": "2026-04-17", "currency": "USD", "rate": 1604.2},
            {"date": "2026-04-16", "currency": "USD", "rate": 1610.0},
        ]

    adapter.get_historical_forex_rates = fake_history  # type: ignore[method-assign]

    rate = await adapter.get_fx_rate(Currency.USD, Currency.NGN, date(2026, 4, 17))

    assert rate == 160420


def test_extract_symbol_understands_provider_prefixes():
    assert ngn_module.NgnMarketAdapter._extract_symbol("NGX:ngx30") == "NGX30"
    assert ngn_module.NgnMarketAdapter._extract_symbol("NGNMARKET/ngxbnk") == "NGXBNK"
    assert ngn_module.NgnMarketAdapter._extract_symbol("mtnn") == "MTNN"


@pytest.mark.asyncio
async def test_shared_session_is_reused_and_close_resets(monkeypatch):
    monkeypatch.setattr(
        ngn_module.settings,
        "NGNMARKET_API_BASE_URL",
        "https://api.ngnmarket.com/v1",
        raising=False,
    )
    monkeypatch.setattr(
        ngn_module.settings,
        "NGNMARKET_API_KEY",
        "test-ngn-key",
        raising=False,
    )

    adapter_a = ngn_module.NgnMarketAdapter()
    adapter_b = ngn_module.NgnMarketAdapter()

    session_a = await adapter_a._get_shared_session()
    session_b = await adapter_b._get_shared_session()

    assert session_a is session_b
    assert isinstance(session_a, aiohttp.ClientSession)

    await ngn_module.NgnMarketAdapter.close_shared_session()

    session_c = await adapter_a._get_shared_session()
    assert session_c is not session_a

    await ngn_module.NgnMarketAdapter.close_shared_session()
