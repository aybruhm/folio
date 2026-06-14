import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import aiohttp

from domain.value_objects.money import AssetMetadata, Currency
from infrastructure.config.env import get_environ_settings

logger = logging.getLogger(__name__)


class TradingviewAdapter:
    """Adapter for the TradingView Data API via RapidAPI.

    Endpoint used: GET /api/price/{symbol}
    (candlestick historical data — includes current OHLCV + history).

    Rate limits (RapidAPI free tier):
      - 50 real-time token generation requests / month (hard limit)
      - 150 requests / month (hard limit)
      - ~1000 requests / hour

    Implementation avoids token generation—only simple price lookups are used
    so that the 150-request monthly cap is the governing constraint.
    """

    _shared_session: Optional[aiohttp.ClientSession] = None
    _session_lock: Optional[asyncio.Lock] = None
    _shared_timeout = aiohttp.ClientTimeout(total=15)

    # Rolling-window rate tracking (per-process, not distributed)
    _MAX_REQUESTS_PER_HOUR = 900  # stay under 1000 with headroom
    _MAX_REQUESTS_PER_MONTH = 140  # leave breathing room below 150

    # Default query params for the /api/price endpoint
    _DEFAULT_TIMEFRAME = "5"
    _DEFAULT_RANGE = 10

    def __init__(self) -> None:
        settings = get_environ_settings()
        self._base_url = (settings.RAPID_API_BASE_URL or "").rstrip("/")
        self._api_key = settings.RAPID_API_KEY
        self._enabled = bool(self._base_url and self._api_key)

        # Rate-limit windows
        self._hour_window_start: datetime = datetime.now(timezone.utc).replace(
            minute=0, second=0, microsecond=0
        )
        self._hour_count = 0

        self._month_window_start: datetime = datetime.now(timezone.utc).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        self._month_count = 0

        # Quick in-memory metadata cache to avoid redundant requests
        self._metadata_cache: dict[str, AssetMetadata] = {}
        self._metadata_cache_ttl = timedelta(hours=24)
        self._metadata_cache_timestamps: dict[str, datetime] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_asset_metadata(
        self, ticker: str, currency: str = "USD"
    ) -> Optional[AssetMetadata]:
        """Return metadata for *ticker* using the TradingView price endpoint."""
        if not self._enabled:
            logger.debug("TradingView (RapidAPI) is not configured; skipping lookup")
            return None

        # Check in-memory cache first
        cached = self._metadata_cache.get(ticker)
        ts = self._metadata_cache_timestamps.get(ticker)
        if (
            cached
            and ts
            and (datetime.now(timezone.utc) - ts) < self._metadata_cache_ttl
        ):
            return cached

        if not self._can_make_request():
            return None

        symbol = self._normalise_symbol(ticker)

        try:
            payload = await self._get_price(symbol)
            if not payload:
                return None

            metadata = self._parse_metadata(ticker, symbol, payload, currency)
            if metadata:
                self._metadata_cache[ticker] = metadata
                self._metadata_cache_timestamps[ticker] = datetime.now(timezone.utc)

            return metadata
        except Exception as e:
            logger.warning(f"TradingView metadata lookup failed for {ticker}: {e}")
            return None

    async def get_price_history(
        self, ticker: str, start: date, end: date
    ) -> list[tuple[date, int]]:
        if not self._enabled or not self._can_make_request():
            return []

        symbol = self._normalise_symbol(ticker)
        days = max((end - start).days + 1, 1)
        raw = await self._get(
            f"/api/price/{symbol}", params={"timeframe": "1D", "range": str(days)}
        )
        if not raw or not raw.get("success"):
            return []

        data = raw.get("data") or {}
        history = data.get("history") or []

        result: list[tuple[date, int]] = []
        for candle in history:
            ts = candle.get("time")
            close = candle.get("close")
            if ts is None or close is None:
                continue
            try:
                candle_date = datetime.fromtimestamp(ts, tz=timezone.utc).date()
            except Exception:
                continue
            if start <= candle_date <= end:
                result.append((candle_date, round(float(close) * 100)))

        return sorted(result)

    async def get_current_price(
        self, ticker: str, currency: str = "USD"
    ) -> tuple[date, int]:
        """Return (date, price×100) for *ticker*."""
        if not self._enabled or not self._can_make_request():
            return (date.today(), 0)

        symbol = self._normalise_symbol(ticker)
        try:
            payload = await self._get_price(symbol)
            if not payload:
                return (date.today(), 0)

            price = self._extract_price(payload)
            if price is None:
                return (date.today(), 0)

            return (date.today(), round(price * 100))
        except Exception as e:
            logger.warning(f"TradingView current price failed for {ticker}: {e}")
            return (date.today(), 0)

    # ------------------------------------------------------------------
    # Price endpoint
    # ------------------------------------------------------------------

    async def _get_price(self, symbol: str) -> Optional[dict]:
        """Call GET /api/price/{symbol} and return the inner 'data' dict on success."""
        params = {
            "timeframe": self._DEFAULT_TIMEFRAME,
            "range": str(self._DEFAULT_RANGE),
        }
        path = f"/api/price/{symbol}"
        logger.debug("TradingView: fetching price for %s", symbol)
        raw = await self._get(path, params=params)
        if not raw:
            return None

        # The API wraps responses in {"success": true, "data": {...}, "msg": "..."}
        if not raw.get("success"):
            msg = raw.get("msg", "Unknown error")
            logger.warning(
                "TradingView: price API returned failure for %s: %s", symbol, msg
            )
            return None

        data = raw.get("data")
        if not isinstance(data, dict):
            logger.warning("TradingView: price API missing 'data' for %s", symbol)
            return None

        current = data.get("current") or {}
        close = current.get("close")
        logger.info(
            "TradingView: price OK for %s — close=%s history_len=%d",
            symbol,
            close,
            len(data.get("history") or []),
        )
        return data

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str, params: Optional[dict] = None) -> Optional[dict]:
        url = f"{self._base_url.rstrip('/')}{path}"
        headers = {
            "x-rapidapi-host": "tradingview-data1.p.rapidapi.com",
            "x-rapidapi-key": self._api_key,
        }

        logger.debug("TradingView: GET %s params=%s", path, params)
        try:
            session = await self._get_shared_session()
            async with session.get(url, headers=headers, params=params) as response:
                if response.status >= 400:
                    body = await response.text()
                    logger.warning(
                        "TradingView: GET %s → %s error: %s",
                        path,
                        response.status,
                        body[:300],
                    )
                    return None

                try:
                    data = await response.json()
                    logger.debug("TradingView: GET %s → %s OK", path, response.status)
                    return data
                except Exception:
                    logger.warning("TradingView: GET %s returned non-JSON", path)
                    return None
        except Exception as e:
            logger.warning("TradingView: GET %s failed: %s", path, e)
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

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _can_make_request(self) -> bool:
        now = datetime.now(timezone.utc)

        hour_start = now.replace(minute=0, second=0, microsecond=0)
        if hour_start != self._hour_window_start:
            self._hour_window_start = hour_start
            self._hour_count = 0

        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start != self._month_window_start:
            self._month_window_start = month_start
            self._month_count = 0

        if self._hour_count >= self._MAX_REQUESTS_PER_HOUR:
            logger.warning("TradingView hourly request limit reached; skipping")
            return False

        if self._month_count >= self._MAX_REQUESTS_PER_MONTH:
            logger.warning("TradingView monthly request limit reached; skipping")
            return False

        self._hour_count += 1
        self._month_count += 1
        return True

    # ------------------------------------------------------------------
    # Symbol normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_symbol(ticker: str) -> str:
        """Convert a user-provided ticker into a TradingView-qualified symbol.

        Rules applied in order:
        1. If the ticker already contains ':' (e.g. NASDAQ:AAPL), use as-is.
        2. If the ticker contains '/' (e.g. BTC/USD), treat as crypto pair
           → BINANCE:BTCUSD.
        3. If the ticker ends with '=X' or '=x', treat as FX pair → FX:...
        4. If the ticker is 6 alpha chars (possible FX pair, e.g. EURUSD),
           prepend 'FX:'.
        5. Default: prepend 'NASDAQ:' for US-like tickers (1-5 uppercase letters)
           or 'NYSE:' for everything else.
        """
        raw = (ticker or "").strip()
        if not raw:
            return raw

        # Already qualified with an exchange prefix
        if ":" in raw:
            return raw

        # Crypto pair: e.g. BTC/USD
        if "/" in raw:
            parts = raw.split("/", 1)
            return f"BINANCE:{parts[0].upper()}{parts[1].upper()}"

        # Yahoo-style FX suffix
        if raw.upper().endswith("=X"):
            base = raw[:-2]
            return f"FX:{base.upper()}"

        # 6-letter alpha = likely FX pair
        upper = raw.upper()
        if len(upper) == 6 and upper.isalpha():
            return f"FX:{upper}"

        # Stock / ETF heuristics: 1-5 uppercase chars → NASDAQ, else NYSE
        if len(upper) <= 5 and upper.isalpha():
            return f"NASDAQ:{upper}"

        return f"NYSE:{upper}"

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_metadata(
        ticker: str, symbol: str, data: dict, currency_hint: str
    ) -> Optional[AssetMetadata]:
        """Extract AssetMetadata from the 'data' portion of a /api/price response.

        The shape of *data*:
            {
                "symbol": "NASDAQ:AAPL",
                "current": {"time":..., "open":..., "high":..., "low":..., "close":..., "volume":...},
                "history": [...],
                "info": {...},
                ...
            }
        """
        try:
            info = data.get("info") or {}

            # Name: prefer info.name, then the raw ticker
            name = info.get("name") or info.get("description") or ticker

            # Exchange: extract from the qualified symbol or info
            exchange = TradingviewAdapter._extract_exchange(symbol, info)

            # Currency: from info, then hint
            currency_str = (
                info.get("currency")
                or info.get("currency_code")
                or TradingviewAdapter._guess_currency_from_symbol(symbol)
                or currency_hint
            )
            try:
                currency = Currency(currency_str.upper())
            except ValueError:
                currency = (
                    Currency(currency_hint.upper()) if currency_hint else Currency.USD
                )

            # Asset class
            type_info = str(info.get("type") or "").lower()
            asset_class = TradingviewAdapter._derive_asset_class(
                ticker, symbol, type_info, exchange
            )

            return AssetMetadata(
                ticker=ticker,
                name=name,
                asset_class=asset_class,
                currency=currency,
                exchange=exchange,
                sector=info.get("sector"),
                industry=info.get("industry"),
                country=info.get("country"),
                isin=info.get("isin"),
            )
        except Exception as e:
            logger.debug(f"TradingView metadata parse failed for {ticker}: {e}")
            return None

    @staticmethod
    def _extract_exchange(symbol: str, info: dict) -> Optional[str]:
        """Derive exchange from the qualified symbol or info dict."""
        if ":" in symbol:
            return symbol.split(":")[0]
        return info.get("exchange") or info.get("market") or info.get("provider")

    @staticmethod
    def _guess_currency_from_symbol(symbol: str) -> Optional[str]:
        """Try to infer currency from the symbol's quote portion."""
        if ":" not in symbol:
            return None
        _, right = symbol.split(":", 1)
        # Crypto pairs often end with USDT, USD, BTC, etc.
        known_quote_currencies = {
            "USDT": "USD",
            "USDC": "USD",
            "USD": "USD",
            "BTC": "BTC",
            "ETH": "ETH",
            "EUR": "EUR",
            "GBP": "GBP",
            "JPY": "JPY",
            "NGN": "NGN",
        }
        for suffix, currency_code in known_quote_currencies.items():
            if right.upper().endswith(suffix):
                return currency_code
        return None

    @staticmethod
    def _derive_asset_class(
        ticker: str, symbol: str, type_info: str, exchange: Optional[str]
    ) -> str:
        """Heuristically determine asset class from type string, symbol, and exchange."""
        type_lower = type_info.lower()

        if "crypto" in type_lower or "digital" in type_lower:
            return "crypto"
        if "etf" in type_lower or "fund" in type_lower or "trust" in type_lower:
            return "etf"
        if "index" in type_lower:
            return "etf"
        if "forex" in type_lower or "currency" in type_lower:
            return "cash"

        # Exchange-based heuristics (extracted from qualified symbol)
        prefix = symbol.split(":")[0].upper() if ":" in symbol else ""
        if prefix in {"BINANCE", "COINBASE", "KRAKEN", "BITFINEX", "BITSTAMP"}:
            return "crypto"
        if prefix in {"OANDA", "FXCM", "FX"}:
            return "cash"

        # Ticker-based heuristics
        upper = ticker.upper()
        if upper.endswith("=X") or prefix == "FX":
            return "cash"
        if "/" in upper or prefix == "BINANCE":
            return "crypto"

        return "stock"

    @staticmethod
    def _extract_price(data: dict) -> Optional[float]:
        """Extract the current closing price from the 'data' portion of a /api/price response.

        Prefers ``data.current.close``, falls back to ``data.current.open``,
        then the last entry in ``data.history``.
        """
        current = data.get("current") or {}

        for field in ("close", "open", "high", "low"):
            val = current.get(field)
            if val is not None:
                try:
                    f = float(val)
                    if f > 0:
                        return f
                except (ValueError, TypeError):
                    pass

        # Fallback: last candle in history
        history = data.get("history") or []
        if isinstance(history, list) and history:
            last = history[-1]
            if isinstance(last, dict):
                for field in ("close", "open"):
                    val = last.get(field)
                    if val is not None:
                        try:
                            f = float(val)
                            if f > 0:
                                return f
                        except (ValueError, TypeError):
                            pass

        return None
