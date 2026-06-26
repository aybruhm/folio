from datetime import date, datetime, timedelta, timezone

import aiohttp
import pytest

from adapters.outbound.market_data import ngxpulse_adapter as ngx_module
from domain.value_objects.money import Currency

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _enable_adapter(monkeypatch) -> ngx_module.NgxPulseAdapter:
    monkeypatch.setattr(
        ngx_module.settings,
        "NGXPULSE_API_BASE_URL",
        "https://www.ngxpulse.ng",
        raising=False,
    )
    monkeypatch.setattr(
        ngx_module.settings,
        "NGXPULSE_API_KEY",
        "test-ngxpulse-key",
        raising=False,
    )
    return ngx_module.NgxPulseAdapter()


def _reset_rate_limits(adapter: ngx_module.NgxPulseAdapter) -> None:
    adapter._minute_count = 0
    adapter._day_count = 0
    adapter._minute_window_start = datetime.now(timezone.utc).replace(
        second=0, microsecond=0
    )
    adapter._day_window_start = datetime.now(timezone.utc).date()


# ---------------------------------------------------------------------------
# get_asset_metadata
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_asset_metadata_from_stocks(monkeypatch):
    adapter = _enable_adapter(monkeypatch)

    async def fake_lookup_stock(symbol: str):
        return {
            "symbol": symbol,
            "name": "Dangote Cement Plc",
            "sector": "Industrial",
        }

    async def fake_lookup_etf(symbol: str):
        return None

    monkeypatch.setattr(adapter, "_lookup_stock", fake_lookup_stock)
    monkeypatch.setattr(adapter, "_lookup_etf", fake_lookup_etf)

    metadata = await adapter.get_asset_metadata("DANGCEM", "NGN")

    assert metadata is not None
    assert metadata.ticker == "DANGCEM"
    assert metadata.name == "Dangote Cement Plc"
    assert metadata.asset_class == "stock"
    assert metadata.currency == Currency.NGN
    assert metadata.exchange == "NGX"
    assert metadata.sector == "Industrial"
    assert metadata.country == "NG"


@pytest.mark.asyncio
async def test_get_asset_metadata_from_etfs(monkeypatch):
    adapter = _enable_adapter(monkeypatch)

    async def fake_lookup_stock(symbol: str):
        return None

    async def fake_lookup_etf(symbol: str):
        return {
            "symbol": "NEWGOLD",
            "name": "NewGold ETF",
            "isin": "NGNEWGOLD001",
            "sector": "Exchange Traded Fund",
        }

    monkeypatch.setattr(adapter, "_lookup_stock", fake_lookup_stock)
    monkeypatch.setattr(adapter, "_lookup_etf", fake_lookup_etf)

    metadata = await adapter.get_asset_metadata("NEWGOLD", "NGN", asset_class="etf")

    assert metadata is not None
    assert metadata.ticker == "NEWGOLD"
    assert metadata.name == "NewGold ETF"
    assert metadata.asset_class == "etf"
    assert metadata.isin == "NGNEWGOLD001"
    assert metadata.exchange == "NGX"
    assert metadata.country == "NG"


@pytest.mark.asyncio
async def test_get_asset_metadata_not_found(monkeypatch):
    adapter = _enable_adapter(monkeypatch)

    async def fake_lookup_stock(symbol: str):
        return None

    async def fake_lookup_etf(symbol: str):
        return None

    monkeypatch.setattr(adapter, "_lookup_stock", fake_lookup_stock)
    monkeypatch.setattr(adapter, "_lookup_etf", fake_lookup_etf)

    metadata = await adapter.get_asset_metadata("UNKNOWN", "NGN")
    assert metadata is None


@pytest.mark.asyncio
async def test_get_asset_metadata_disabled(monkeypatch):
    monkeypatch.setattr(ngx_module.settings, "NGXPULSE_API_KEY", "", raising=False)

    adapter = ngx_module.NgxPulseAdapter()
    metadata = await adapter.get_asset_metadata("DANGCEM", "NGN")
    assert metadata is None


@pytest.mark.asyncio
async def test_get_asset_metadata_stock_preferred_over_etf(monkeypatch):
    """When a symbol appears in both stocks and ETFs, stocks wins."""
    adapter = _enable_adapter(monkeypatch)

    async def fake_lookup_stock(symbol: str):
        return {"symbol": symbol, "name": "Stock Name", "sector": "Industrial"}

    async def fake_lookup_etf(symbol: str):
        return {"symbol": symbol, "name": "ETF Name", "isin": "NGETFX0001"}

    monkeypatch.setattr(adapter, "_lookup_stock", fake_lookup_stock)
    monkeypatch.setattr(adapter, "_lookup_etf", fake_lookup_etf)

    metadata = await adapter.get_asset_metadata("DUAL", "NGN")

    assert metadata is not None
    assert metadata.asset_class == "stock"
    assert metadata.name == "Stock Name"


# ---------------------------------------------------------------------------
# get_price_history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_price_history_from_index(monkeypatch):
    adapter = _enable_adapter(monkeypatch)

    async def fake_lookup_stock(symbol: str):
        return None

    async def fake_lookup_etf(symbol: str):
        return None

    async def fake_get_index_history(code, from_date=None, to_date=None):
        return {
            "success": True,
            "code": "ASI",
            "count": 2,
            "history": [
                {"date": "2026-01-02", "value": 26867.79},
                {"date": "2026-01-03", "value": 27000.50},
            ],
        }

    monkeypatch.setattr(adapter, "_lookup_stock", fake_lookup_stock)
    monkeypatch.setattr(adapter, "_lookup_etf", fake_lookup_etf)
    monkeypatch.setattr(adapter, "get_index_history", fake_get_index_history)

    history = await adapter.get_price_history("ASI", date(2026, 1, 1), date(2026, 1, 5))

    assert len(history) == 2
    assert history[0] == (date(2026, 1, 2), 2686779)
    assert history[1] == (date(2026, 1, 3), 2700050)


@pytest.mark.asyncio
async def test_get_price_history_skips_known_stock(monkeypatch):
    adapter = _enable_adapter(monkeypatch)
    index_called = False

    async def fake_lookup_stock(symbol: str):
        return {"symbol": "DANGCEM", "name": "Dangote Cement"}

    async def fake_lookup_etf(symbol: str):
        return None

    async def fake_get_index_history(code, from_date=None, to_date=None):
        nonlocal index_called
        index_called = True
        return None

    monkeypatch.setattr(adapter, "_lookup_stock", fake_lookup_stock)
    monkeypatch.setattr(adapter, "_lookup_etf", fake_lookup_etf)
    monkeypatch.setattr(adapter, "get_index_history", fake_get_index_history)

    history = await adapter.get_price_history(
        "DANGCEM", date(2026, 1, 1), date(2026, 1, 5)
    )

    assert history == []
    assert not index_called  # no API call wasted


@pytest.mark.asyncio
async def test_get_price_history_skips_known_etf(monkeypatch):
    adapter = _enable_adapter(monkeypatch)
    index_called = False

    async def fake_lookup_stock(symbol: str):
        return None

    async def fake_lookup_etf(symbol: str):
        return {"symbol": "NEWGOLD", "name": "NewGold ETF"}

    async def fake_get_index_history(code, from_date=None, to_date=None):
        nonlocal index_called
        index_called = True
        return None

    monkeypatch.setattr(adapter, "_lookup_stock", fake_lookup_stock)
    monkeypatch.setattr(adapter, "_lookup_etf", fake_lookup_etf)
    monkeypatch.setattr(adapter, "get_index_history", fake_get_index_history)

    history = await adapter.get_price_history(
        "NEWGOLD", date(2026, 1, 1), date(2026, 1, 5)
    )

    assert history == []
    assert not index_called


@pytest.mark.asyncio
async def test_get_price_history_disabled(monkeypatch):
    monkeypatch.setattr(ngx_module.settings, "NGXPULSE_API_KEY", "", raising=False)

    adapter = ngx_module.NgxPulseAdapter()
    history = await adapter.get_price_history("ASI", date(2026, 1, 1), date(2026, 1, 5))
    assert history == []


# ---------------------------------------------------------------------------
# get_current_price
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_price_from_stocks(monkeypatch):
    adapter = _enable_adapter(monkeypatch)

    async def fake_lookup_stock(symbol: str):
        return {"symbol": symbol, "current_price": 665.00}

    async def fake_lookup_etf(symbol: str):
        return None

    monkeypatch.setattr(adapter, "_lookup_stock", fake_lookup_stock)
    monkeypatch.setattr(adapter, "_lookup_etf", fake_lookup_etf)

    price_date, price_cents = await adapter.get_current_price("DANGCEM")
    assert price_cents == 66500


@pytest.mark.asyncio
async def test_get_current_price_from_etfs(monkeypatch):
    adapter = _enable_adapter(monkeypatch)

    async def fake_lookup_stock(symbol: str):
        return None

    async def fake_lookup_etf(symbol: str):
        return {"symbol": symbol, "close": 58000, "previous_close": 57500}

    monkeypatch.setattr(adapter, "_lookup_stock", fake_lookup_stock)
    monkeypatch.setattr(adapter, "_lookup_etf", fake_lookup_etf)

    price_date, price_cents = await adapter.get_current_price("NEWGOLD")
    assert price_cents == 5800000  # 58000.00 * 100


@pytest.mark.asyncio
async def test_get_current_price_etf_fallback_to_previous_close(monkeypatch):
    """When 'close' is missing, use 'previous_close'."""
    adapter = _enable_adapter(monkeypatch)

    async def fake_lookup_stock(symbol: str):
        return None

    async def fake_lookup_etf(symbol: str):
        return {"symbol": symbol, "previous_close": 57500}

    monkeypatch.setattr(adapter, "_lookup_stock", fake_lookup_stock)
    monkeypatch.setattr(adapter, "_lookup_etf", fake_lookup_etf)

    price_date, price_cents = await adapter.get_current_price("NEWGOLD")
    assert price_cents == 5750000


@pytest.mark.asyncio
async def test_get_current_price_fallback_to_index(monkeypatch):
    adapter = _enable_adapter(monkeypatch)
    _reset_rate_limits(adapter)

    async def fake_lookup_stock(symbol: str):
        return None

    async def fake_lookup_etf(symbol: str):
        return None

    async def fake_get(path, params=None):
        return {
            "success": True,
            "history": [{"date": "2026-06-01", "value": 72000.00}],
        }

    monkeypatch.setattr(adapter, "_lookup_stock", fake_lookup_stock)
    monkeypatch.setattr(adapter, "_lookup_etf", fake_lookup_etf)
    monkeypatch.setattr(adapter, "_get", fake_get)

    price_date, price_cents = await adapter.get_current_price("ASI")
    assert price_cents == 7200000


@pytest.mark.asyncio
async def test_get_current_price_not_found(monkeypatch):
    adapter = _enable_adapter(monkeypatch)
    _reset_rate_limits(adapter)

    async def fake_lookup_stock(symbol: str):
        return None

    async def fake_lookup_etf(symbol: str):
        return None

    async def fake_get(path, params=None):
        return {"success": False}

    monkeypatch.setattr(adapter, "_lookup_stock", fake_lookup_stock)
    monkeypatch.setattr(adapter, "_lookup_etf", fake_lookup_etf)
    monkeypatch.setattr(adapter, "_get", fake_get)

    price_date, price_cents = await adapter.get_current_price("UNKNOWN")
    assert price_cents == 0


@pytest.mark.asyncio
async def test_get_current_price_disabled(monkeypatch):
    monkeypatch.setattr(ngx_module.settings, "NGXPULSE_API_KEY", "", raising=False)

    adapter = ngx_module.NgxPulseAdapter()
    price_date, price_cents = await adapter.get_current_price("DANGCEM")
    assert price_cents == 0


# ---------------------------------------------------------------------------
# get_stocks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_stocks_bare_list_response(monkeypatch):
    adapter = _enable_adapter(monkeypatch)
    _reset_rate_limits(adapter)

    async def fake_get(path, params=None):
        return [
            {"symbol": "DANGCEM", "name": "Dangote Cement"},
            {"symbol": "MTNN", "name": "MTN Nigeria"},
        ]

    monkeypatch.setattr(adapter, "_get", fake_get)

    stocks = await adapter.get_stocks()
    assert stocks is not None
    assert len(stocks) == 2
    assert stocks[0]["symbol"] == "DANGCEM"


@pytest.mark.asyncio
async def test_get_stocks_wrapped_dict_response(monkeypatch):
    adapter = _enable_adapter(monkeypatch)
    _reset_rate_limits(adapter)

    async def fake_get(path, params=None):
        return {
            "success": True,
            "data": [{"symbol": "DANGCEM"}, {"symbol": "MTNN"}],
        }

    monkeypatch.setattr(adapter, "_get", fake_get)

    stocks = await adapter.get_stocks()
    assert stocks is not None
    assert len(stocks) == 2


@pytest.mark.asyncio
async def test_get_stocks_scans_dict_values_for_list(monkeypatch):
    """When the dict doesn't use key 'data', scan all values for a list."""
    adapter = _enable_adapter(monkeypatch)
    _reset_rate_limits(adapter)

    async def fake_get(path, params=None):
        return {"error": False, "results": [{"symbol": "DANGCEM"}]}

    monkeypatch.setattr(adapter, "_get", fake_get)

    stocks = await adapter.get_stocks()
    assert stocks is not None
    assert len(stocks) == 1


@pytest.mark.asyncio
async def test_get_stocks_cached(monkeypatch):
    adapter = _enable_adapter(monkeypatch)
    _reset_rate_limits(adapter)
    call_count = 0

    async def fake_get(path, params=None):
        nonlocal call_count
        call_count += 1
        return [{"symbol": f"STOCK{call_count}"}]

    monkeypatch.setattr(adapter, "_get", fake_get)

    stocks1 = await adapter.get_stocks()
    stocks2 = await adapter.get_stocks()

    assert call_count == 1  # second call served from cache
    assert stocks1 is stocks2
    assert stocks1[0]["symbol"] == "STOCK1"


@pytest.mark.asyncio
async def test_get_stocks_rate_limited(monkeypatch):
    adapter = _enable_adapter(monkeypatch)
    adapter._minute_count = adapter._MAX_REQUESTS_PER_MINUTE  # exhausted

    stocks = await adapter.get_stocks()
    assert stocks is None


# ---------------------------------------------------------------------------
# get_etfs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_etfs_success(monkeypatch):
    adapter = _enable_adapter(monkeypatch)
    _reset_rate_limits(adapter)

    async def fake_get(path, params=None):
        return {
            "success": True,
            "count": 1,
            "data": [{"symbol": "NEWGOLD", "name": "NewGold ETF"}],
        }

    monkeypatch.setattr(adapter, "_get", fake_get)

    etfs = await adapter.get_etfs()
    assert etfs is not None
    assert etfs["count"] == 1
    assert etfs["data"][0]["symbol"] == "NEWGOLD"


@pytest.mark.asyncio
async def test_get_etfs_cached(monkeypatch):
    adapter = _enable_adapter(monkeypatch)
    _reset_rate_limits(adapter)
    call_count = 0

    async def fake_get(path, params=None):
        nonlocal call_count
        call_count += 1
        return {"success": True, "count": 1, "data": []}

    monkeypatch.setattr(adapter, "_get", fake_get)

    etfs1 = await adapter.get_etfs()
    etfs2 = await adapter.get_etfs()

    assert call_count == 1
    assert etfs1 is etfs2


@pytest.mark.asyncio
async def test_get_etfs_rate_limited(monkeypatch):
    adapter = _enable_adapter(monkeypatch)
    adapter._minute_count = adapter._MAX_REQUESTS_PER_MINUTE

    etfs = await adapter.get_etfs()
    assert etfs is None


# ---------------------------------------------------------------------------
# get_index_history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_index_history_success(monkeypatch):
    adapter = _enable_adapter(monkeypatch)
    _reset_rate_limits(adapter)

    async def fake_get(path, params=None):
        assert "asi" in path
        return {
            "success": True,
            "code": "ASI",
            "count": 2,
            "history": [
                {"date": "2020-01-02", "value": 26867.79},
                {"date": "2020-01-03", "value": 27000.00},
            ],
        }

    monkeypatch.setattr(adapter, "_get", fake_get)

    result = await adapter.get_index_history("ASI")
    assert result is not None
    assert result["count"] == 2
    assert result["history"][0]["value"] == 26867.79


@pytest.mark.asyncio
async def test_get_index_history_with_date_params(monkeypatch):
    adapter = _enable_adapter(monkeypatch)
    _reset_rate_limits(adapter)

    captured_params = {}

    async def fake_get(path, params=None):
        nonlocal captured_params
        captured_params = params or {}
        return {"success": True, "count": 1, "history": []}

    monkeypatch.setattr(adapter, "_get", fake_get)

    await adapter.get_index_history(
        "ASI", from_date=date(2026, 1, 1), to_date=date(2026, 6, 1)
    )

    assert captured_params["from"] == "2026-01-01"
    assert captured_params["to"] == "2026-06-01"


@pytest.mark.asyncio
async def test_get_index_history_rate_limited(monkeypatch):
    adapter = _enable_adapter(monkeypatch)
    adapter._day_count = adapter._MAX_REQUESTS_PER_DAY

    result = await adapter.get_index_history("ASI")
    assert result is None


# ---------------------------------------------------------------------------
# Rate limiting — _can_make_request
# ---------------------------------------------------------------------------


def test_can_make_request_allows_under_limit():
    adapter = ngx_module.NgxPulseAdapter()
    _reset_rate_limits(adapter)

    for _ in range(adapter._MAX_REQUESTS_PER_MINUTE):
        assert adapter._can_make_request()

    # Now at limit
    assert not adapter._can_make_request()


def test_can_make_request_day_limit():
    adapter = ngx_module.NgxPulseAdapter()
    _reset_rate_limits(adapter)
    adapter._day_count = adapter._MAX_REQUESTS_PER_DAY

    assert not adapter._can_make_request()


def test_can_make_request_minute_window_resets():
    adapter = ngx_module.NgxPulseAdapter()
    adapter._minute_count = adapter._MAX_REQUESTS_PER_MINUTE
    adapter._minute_window_start = datetime.now(timezone.utc).replace(
        second=0, microsecond=0
    ) - timedelta(minutes=2)

    # Window is in the past, so it should reset
    assert adapter._can_make_request()
    assert adapter._minute_count == 1


def test_can_make_request_day_window_resets():
    adapter = ngx_module.NgxPulseAdapter()
    adapter._day_count = adapter._MAX_REQUESTS_PER_DAY
    adapter._day_window_start = date.today() - timedelta(days=1)

    assert adapter._can_make_request()
    assert adapter._day_count == 1


# ---------------------------------------------------------------------------
# _extract_symbol
# ---------------------------------------------------------------------------


def test_extract_symbol_ngx_prefix():
    assert ngx_module.NgxPulseAdapter._extract_symbol("NGX:DANGCEM") == "DANGCEM"
    assert (
        ngx_module.NgxPulseAdapter._extract_symbol("NGX/STANBICETF30") == "STANBICETF30"
    )
    assert ngx_module.NgxPulseAdapter._extract_symbol("NGX|ASI") == "ASI"


def test_extract_symbol_ngxpulse_prefix():
    assert ngx_module.NgxPulseAdapter._extract_symbol("NGXPULSE:DANGCEM") == "DANGCEM"
    assert ngx_module.NgxPulseAdapter._extract_symbol("NGXPULSE/NEWGOLD") == "NEWGOLD"


def test_extract_symbol_bare_ticker():
    assert ngx_module.NgxPulseAdapter._extract_symbol("DANGCEM") == "DANGCEM"
    assert ngx_module.NgxPulseAdapter._extract_symbol("asi") == "ASI"


def test_extract_symbol_empty():
    assert ngx_module.NgxPulseAdapter._extract_symbol("") == ""
    assert ngx_module.NgxPulseAdapter._extract_symbol("  ") == ""


# ---------------------------------------------------------------------------
# _safe_currency
# ---------------------------------------------------------------------------


def test_safe_currency_valid():
    assert ngx_module.NgxPulseAdapter._safe_currency("NGN") == Currency.NGN
    assert ngx_module.NgxPulseAdapter._safe_currency("usd") == Currency.USD


def test_safe_currency_invalid_falls_back_to_ngn():
    assert ngx_module.NgxPulseAdapter._safe_currency("XYZ") == Currency.NGN


# ---------------------------------------------------------------------------
# _log_api_error
# ---------------------------------------------------------------------------


def test_log_api_error_json_body(caplog):
    import logging

    caplog.set_level(logging.WARNING)

    body = '{"error": true, "status": 401, "message": "Invalid or missing API key"}'
    ngx_module.NgxPulseAdapter._log_api_error("/test", 401, body)

    assert "NgxPulse error" in caplog.text
    assert "401" in caplog.text
    assert "Invalid or missing API key" in caplog.text


def test_log_api_error_non_json_body(caplog):
    import logging

    caplog.set_level(logging.WARNING)

    body = "<html>Server Error</html>"
    ngx_module.NgxPulseAdapter._log_api_error("/test", 500, body)

    assert "NgxPulse error" in caplog.text
    assert "500" in caplog.text
    assert "Server Error" in caplog.text


# ---------------------------------------------------------------------------
# Shared session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shared_session_reused(monkeypatch):
    monkeypatch.setattr(
        ngx_module.settings,
        "NGXPULSE_API_BASE_URL",
        "https://www.ngxpulse.ng",
        raising=False,
    )
    monkeypatch.setattr(
        ngx_module.settings,
        "NGXPULSE_API_KEY",
        "test-ngxpulse-key",
        raising=False,
    )

    adapter_a = ngx_module.NgxPulseAdapter()
    adapter_b = ngx_module.NgxPulseAdapter()

    session_a = await adapter_a._get_shared_session()
    session_b = await adapter_b._get_shared_session()

    assert session_a is session_b
    assert isinstance(session_a, aiohttp.ClientSession)

    await ngx_module.NgxPulseAdapter.close_shared_session()


@pytest.mark.asyncio
async def test_shared_session_close_and_recreate(monkeypatch):
    monkeypatch.setattr(
        ngx_module.settings,
        "NGXPULSE_API_BASE_URL",
        "https://www.ngxpulse.ng",
        raising=False,
    )
    monkeypatch.setattr(
        ngx_module.settings,
        "NGXPULSE_API_KEY",
        "test-ngxpulse-key",
        raising=False,
    )

    adapter = ngx_module.NgxPulseAdapter()
    session_a = await adapter._get_shared_session()

    await ngx_module.NgxPulseAdapter.close_shared_session()

    session_b = await adapter._get_shared_session()
    assert session_b is not session_a

    await ngx_module.NgxPulseAdapter.close_shared_session()


# ---------------------------------------------------------------------------
# _lookup_stock / _lookup_etf
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lookup_stock_finds_by_symbol_case_insensitive(monkeypatch):
    adapter = _enable_adapter(monkeypatch)
    _reset_rate_limits(adapter)

    async def fake_get(path, params=None):
        return [{"symbol": "DANGCEM", "name": "Dangote Cement"}]

    monkeypatch.setattr(adapter, "_get", fake_get)

    result = await adapter._lookup_stock("dangcem")
    assert result is not None
    assert result["symbol"] == "DANGCEM"


@pytest.mark.asyncio
async def test_lookup_stock_not_found(monkeypatch):
    adapter = _enable_adapter(monkeypatch)
    _reset_rate_limits(adapter)

    async def fake_get(path, params=None):
        return [{"symbol": "MTNN", "name": "MTN Nigeria"}]

    monkeypatch.setattr(adapter, "_get", fake_get)

    result = await adapter._lookup_stock("DANGCEM")
    assert result is None


@pytest.mark.asyncio
async def test_lookup_etf_finds_by_symbol_or_canonical(monkeypatch):
    adapter = _enable_adapter(monkeypatch)
    _reset_rate_limits(adapter)

    async def fake_get(path, params=None):
        return {
            "success": True,
            "data": [
                {
                    "symbol": "NEWGOLD",
                    "canonical_symbol": "NGNEWGOLD",
                    "name": "NewGold ETF",
                }
            ],
        }

    monkeypatch.setattr(adapter, "_get", fake_get)

    # Match by symbol
    assert await adapter._lookup_etf("NEWGOLD") is not None
    # Match by canonical_symbol
    assert await adapter._lookup_etf("NGNEWGOLD") is not None
    # No match
    assert await adapter._lookup_etf("UNKNOWN") is None
