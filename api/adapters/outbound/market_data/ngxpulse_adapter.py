import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import aiohttp

from adapters.outbound.market_data.price_cache import PriceCache
from domain.value_objects.money import AssetMetadata, Currency
from infrastructure.config import settings

logger = logging.getLogger(__name__)


class NgxPulseAdapter:
    """Adapter for the NGXPulse market data API.

    Endpoints:
      - GET /api/ngxdata/stocks           — 150+ NGX equities snapshot
      - GET /api/ngxdata/etfs             — NGX ETF universe snapshot
      - GET /api/ngxdata/indices/{code}/history — index daily value series

    Auth: X-API-Key header
    Base URL: https://www.ngxpulse.ng

    Rate limits:
      - 10 requests per minute
      - 100 requests per day
    """

    _shared_session: Optional[aiohttp.ClientSession] = None
    _session_lock: Optional[asyncio.Lock] = None
    _shared_timeout = aiohttp.ClientTimeout(total=15)

    # Rate limits (per-process rolling windows)
    _MAX_REQUESTS_PER_MINUTE = 8  # headroom below the 10/min cap
    _MAX_REQUESTS_PER_DAY = 90  # headroom below the 100/day cap

    # In-memory cache for the bulk stocks / ETFs endpoints
    _CACHE_TTL = timedelta(minutes=30)

    def __init__(self) -> None:
        self._base_url = (settings.NGXPULSE_API_BASE_URL or "").rstrip("/")
        self._api_key = settings.NGXPULSE_API_KEY
        self._enabled = bool(self._base_url and self._api_key)

        # Rate-limit windows
        self._minute_window_start: datetime = datetime.now(timezone.utc).replace(
            second=0, microsecond=0
        )
        self._minute_count = 0

        self._day_window_start: date = datetime.now(timezone.utc).date()
        self._day_count = 0

        # Cached bulk responses
        self._stocks_cache: Optional[list[dict]] = None
        self._stocks_cached_at: Optional[datetime] = None

        self._etfs_cache: Optional[dict] = None
        self._etfs_cached_at: Optional[datetime] = None

        # Valkey-backed cache for individual ticker results (shared
        # across processes, same infrastructure as the other adapters).
        self._cache = PriceCache()

    # ------------------------------------------------------------------
    # Public API — asset metadata
    # ------------------------------------------------------------------

    async def get_asset_metadata(
        self, ticker: str, currency: str = "NGN", asset_class: str = ""
    ) -> Optional[AssetMetadata]:
        """Resolve metadata for *ticker* from the stocks or ETFs snapshots.

        Individual ticker results are cached in Valkey via PriceCache
        so repeated lookups don't re-scan the bulk snapshots.
        """
        if not self._enabled:
            return None

        symbol = self._extract_symbol(ticker)
        if not symbol:
            return None

        # Check the shared Valkey cache first (same infra as other adapters).
        cached = await self._cache.get_metadata(ticker)
        if cached is not None:
            return cached

        # Try stocks first, then ETFs (scans the in-memory bulk cache).
        detail = await self._lookup_stock(symbol)
        resolved_class = "stock"
        if not detail:
            detail = await self._lookup_etf(symbol)
            resolved_class = "etf"

        if not detail:
            return None

        try:
            resolved_currency = self._safe_currency(currency)
            metadata = AssetMetadata(
                ticker=ticker,
                name=detail.get("name") or symbol,
                asset_class=resolved_class,
                currency=resolved_currency,
                exchange="NGX",
                sector=detail.get("sector"),
                industry=None,
                country="NG",
                isin=detail.get("isin"),
            )
            # Persist to shared cache for subsequent lookups.
            await self._cache.set_metadata(metadata)
            return metadata
        except Exception as e:
            logger.debug("NgxPulse metadata mapping failed for %s: %s", ticker, e)
            return None

    # ------------------------------------------------------------------
    # Public API — price history
    # ------------------------------------------------------------------

    async def get_price_history(
        self, ticker: str, start: date, end: date
    ) -> list[tuple[date, int]]:
        """Return daily index values for an NGX index code.

        Individual stock/ETF price history is not provided by this API;
        only index history is available. Checks the stocks/ETFs cache
        first to avoid wasting API calls on non-index tickers.
        """
        if not self._enabled:
            return []

        symbol = self._extract_symbol(ticker)
        if not symbol:
            return []

        # Skip index history call if this ticker is a known stock or ETF —
        # NGXPulse only provides historical data for indices.
        if await self._lookup_stock(symbol) or await self._lookup_etf(symbol):
            return []

        # Try to fetch as an index history
        index_data = await self.get_index_history(
            code=symbol,
            from_date=start,
            to_date=end,
        )
        if not index_data:
            return []

        history = index_data.get("history") or []
        result = []
        for entry in history:
            date_str = entry.get("date")
            value = entry.get("value")
            if not date_str or value is None:
                continue
            try:
                d = date.fromisoformat(date_str)
            except Exception:
                continue
            if start <= d <= end:
                result.append((d, round(float(value) * 100)))

        if result:
            logger.info(
                "NgxPulse: price history OK for %s — %d data points",
                ticker,
                len(result),
            )
        else:
            logger.debug(
                "NgxPulse: no price history data for %s (%s → %s)",
                ticker,
                start,
                end,
            )
        return sorted(result)

    async def get_current_price(
        self, ticker: str, currency: str = "NGN"
    ) -> tuple[date, int]:
        """Return (date, price×100) for *ticker*.

        Checks the shared PriceCache first, then falls back to the
        in-memory stocks/ETFs snapshots, then the index history endpoint.
        Results are persisted to PriceCache on success.
        """
        if not self._enabled:
            return (date.today(), 0)

        symbol = self._extract_symbol(ticker)
        if not symbol:
            return (date.today(), 0)

        # Check the shared Valkey cache first.
        cached = await self._cache.get_price(ticker)
        if cached is not None:
            # A sentinel (price=0) means not found — skip upstream.
            if cached[1] == 0 and cached[0] == date.min:
                return (date.today(), 0)
            return cached

        # Try stocks snapshot
        stock = await self._lookup_stock(symbol)
        if stock:
            price = stock.get("current_price")
            if price is not None:
                try:
                    price_cents = round(float(price) * 100)
                    await self._cache.set_price(ticker, date.today(), price_cents)
                    return (date.today(), price_cents)
                except Exception:
                    pass

        # Try ETFs snapshot
        etf = await self._lookup_etf(symbol)
        if etf:
            price = etf.get("close") or etf.get("previous_close")
            if price is not None:
                try:
                    price_cents = round(float(price) * 100)
                    await self._cache.set_price(ticker, date.today(), price_cents)
                    return (date.today(), price_cents)
                except Exception:
                    pass

        # Fallback: try index history (real API call — check rate limit)
        if not self._can_make_request():
            await self._cache.set_price(ticker, date.min, 0)
            return (date.today(), 0)

        chart = await self._get(f"/api/ngxdata/indices/{symbol}/history")
        if isinstance(chart, dict) and chart.get("success") and chart.get("history"):
            history_list = chart["history"]
            if not isinstance(history_list, list) or not history_list:
                await self._cache.set_price(ticker, date.min, 0)
                return (date.today(), 0)
            last = history_list[-1]
            value = last.get("value")
            if value is not None:
                try:
                    price_cents = round(float(value) * 100)
                    await self._cache.set_price(ticker, date.today(), price_cents)
                    return (date.today(), price_cents)
                except Exception:
                    pass

        # Cache sentinel so repeated lookups don't hit the API again.
        await self._cache.set_price(ticker, date.min, 0)
        return (date.today(), 0)

    # ------------------------------------------------------------------
    # Public API — bulk data
    # ------------------------------------------------------------------

    async def get_stocks(self) -> Optional[list[dict]]:
        """Return the full NGX equities list (cached for 30 min)."""
        now = datetime.now(timezone.utc)
        if (
            self._stocks_cache is not None
            and self._stocks_cached_at is not None
            and now - self._stocks_cached_at <= self._CACHE_TTL
        ):
            return self._stocks_cache

        if not self._can_make_request():
            return None

        payload = await self._get("/api/ngxdata/stocks")
        if isinstance(payload, list):
            self._stocks_cache = payload
            self._stocks_cached_at = now
            logger.info("NgxPulse: stocks snapshot fetched — %d entries", len(payload))
            return payload

        # The API may return a wrapped dict — try several unwrapping strategies.
        if isinstance(payload, dict):
            # Strategy 1: {"success": true, "data": [...], ...}
            data = payload.get("data")
            if isinstance(data, list):
                self._stocks_cache = data
                self._stocks_cached_at = now
                logger.info(
                    "NgxPulse: stocks snapshot fetched (wrapped by 'data') — %d entries",
                    len(data),
                )
                return data

            # Strategy 2: {"success": true, "stocks": [...], ...} etc.
            for key, val in payload.items():
                if isinstance(val, list) and len(val) > 0:
                    self._stocks_cache = val
                    self._stocks_cached_at = now
                    logger.info(
                        "NgxPulse: stocks snapshot found under key '%s' — %d entries",
                        key,
                        len(val),
                    )
                    return val

            # Strategy 3: log the actual keys for debugging
            logger.warning(
                "NgxPulse: unexpected stocks response dict — keys=%s",
                list(payload.keys())[:10],
            )
            return None

        logger.warning("NgxPulse: unexpected stocks response type: %s", type(payload))
        return None

    async def get_etfs(self) -> Optional[dict]:
        """Return the full NGX ETF snapshot (cached for 30 min)."""
        now = datetime.now(timezone.utc)
        if (
            self._etfs_cache is not None
            and self._etfs_cached_at is not None
            and now - self._etfs_cached_at <= self._CACHE_TTL
        ):
            return self._etfs_cache

        if not self._can_make_request():
            return None

        payload = await self._get("/api/ngxdata/etfs")
        if isinstance(payload, dict) and payload.get("success"):
            self._etfs_cache = payload
            self._etfs_cached_at = now
            count = payload.get("count", 0)
            logger.info("NgxPulse: ETFs snapshot fetched — %d entries", count)
            return payload

        logger.warning("NgxPulse: unexpected ETFs response: %s", payload)
        return None

    async def get_index_history(
        self,
        code: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> Optional[dict]:
        """Return daily value series for an NGX index (ASI, ngx-30, etc.)."""
        if not self._can_make_request():
            return None

        params = {}
        if from_date:
            params["from"] = from_date.isoformat()
        if to_date:
            params["to"] = to_date.isoformat()

        payload = await self._get(
            f"/api/ngxdata/indices/{code.lower()}/history", params=params
        )
        if isinstance(payload, dict) and payload.get("success"):
            logger.info(
                "NgxPulse: index history OK for %s — %d entries",
                code,
                payload.get("count", 0),
            )
            return payload

        logger.debug("NgxPulse: no index history for %s", code)
        return None

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _can_make_request(self) -> bool:
        now = datetime.now(timezone.utc)

        minute_start = now.replace(second=0, microsecond=0)
        if minute_start != self._minute_window_start:
            self._minute_window_start = minute_start
            self._minute_count = 0

        day_start = now.date()
        if day_start != self._day_window_start:
            self._day_window_start = day_start
            self._day_count = 0

        if self._minute_count >= self._MAX_REQUESTS_PER_MINUTE:
            logger.warning(
                "NgxPulse per-minute request limit reached (%d/%d); skipping request",
                self._minute_count,
                self._MAX_REQUESTS_PER_MINUTE,
            )
            return False

        if self._day_count >= self._MAX_REQUESTS_PER_DAY:
            logger.warning(
                "NgxPulse daily request limit reached (%d/%d); skipping request",
                self._day_count,
                self._MAX_REQUESTS_PER_DAY,
            )
            return False

        self._minute_count += 1
        self._day_count += 1
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _lookup_stock(self, symbol: str) -> Optional[dict]:
        """Find a stock by symbol from the cached stocks snapshot."""
        stocks = await self.get_stocks()
        if not stocks:
            return None

        upper = symbol.upper()
        for stock in stocks:
            if str(stock.get("symbol", "")).upper() == upper:
                return stock
        return None

    async def _lookup_etf(self, symbol: str) -> Optional[dict]:
        """Find an ETF by symbol or canonical_symbol from the cached ETF snapshot."""
        etfs_payload = await self.get_etfs()
        if not etfs_payload:
            return None

        data = etfs_payload.get("data") or []
        upper = symbol.upper()
        for etf in data:
            sym = str(etf.get("symbol", "")).upper()
            canonical = str(etf.get("canonical_symbol", "")).upper()
            if sym == upper or canonical == upper:
                return etf
        return None

    async def _get(
        self, path: str, params: Optional[dict] = None
    ) -> Optional[dict | list]:
        if not self._enabled:
            return None

        url = f"{self._base_url}{path}"
        headers = {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
        }

        logger.debug("NgxPulse: GET %s params=%s", path, params)
        try:
            session = await self._get_shared_session()
            async with session.get(url, params=params, headers=headers) as response:
                status_code = response.status
                body_text = await response.text()

                if status_code >= 400:
                    self._log_api_error(path, status_code, body_text)
                    return None

                try:
                    data = await response.json()
                    logger.debug("NgxPulse: GET %s → %s OK", path, status_code)
                    return data
                except Exception:
                    logger.warning("NgxPulse GET %s returned non-JSON response", path)
                    return None
        except Exception as e:
            logger.warning("NgxPulse: GET %s failed: %s", path, e)
            return None

    @classmethod
    async def _get_shared_session(cls) -> aiohttp.ClientSession:
        if cls._session_lock is None:
            cls._session_lock = asyncio.Lock()

        async with cls._session_lock:
            if cls._shared_session is None or cls._shared_session.closed:
                cls._shared_session = aiohttp.ClientSession(timeout=cls._shared_timeout)

            return cls._shared_session

    @classmethod
    async def close_shared_session(cls) -> None:
        if cls._session_lock is None:
            cls._session_lock = asyncio.Lock()

        async with cls._session_lock:
            if cls._shared_session and not cls._shared_session.closed:
                await cls._shared_session.close()
            cls._shared_session = None

    @staticmethod
    def _extract_symbol(ticker: str) -> str:
        raw = (ticker or "").strip()
        if not raw:
            return ""

        for separator in (":", "/", "|"):
            if separator in raw:
                left, right = raw.split(separator, 1)
                if left.strip().upper() in {"NGX", "NGXPULSE"}:
                    return right.strip().upper()
        return raw.upper()

    @staticmethod
    def _safe_currency(value: str) -> Currency:
        try:
            return Currency(value.upper())
        except ValueError:
            return Currency.NGN

    @staticmethod
    def _log_api_error(path: str, status_code: int, body_text: str) -> None:
        try:
            import json

            payload = json.loads(body_text)
            message = payload.get("message", "")
            error_flag = payload.get("error")
            logger.warning(
                "NgxPulse error on %s: status=%s error=%s message=%s",
                path,
                status_code,
                error_flag,
                message or body_text[:200],
            )
        except Exception:
            logger.warning(
                "NgxPulse error on %s: status=%s body=%.200s",
                path,
                status_code,
                body_text,
            )
