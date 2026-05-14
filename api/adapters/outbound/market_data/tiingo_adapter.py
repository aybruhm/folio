import json
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Optional

from tiingo import TiingoClient

from domain.value_objects.money import AssetMetadata, Currency
from infrastructure.config import settings

logger = logging.getLogger(__name__)


class TiingoAdapter:
    _SUPPORTED_EXCHANGES = {
        "NYSE": "NYSE",
        "NYSE ARCA": "NYSE Arca",
        "ARCA": "NYSE Arca",
        "NYSE AMERICAN": "NYSE American",
        "AMEX": "NYSE American",
        "NASDAQ": "NASDAQ",
        "BATS": "BATS/CBOE Equities",
        "CBOE": "BATS/CBOE Equities",
        "BATS/CBOE EQUITIES": "BATS/CBOE Equities",
        "IEX": "IEX",
        "OTC": "OTC",
        "MUTUAL FUNDS": "Mutual Funds",
        "MUTF": "Mutual Funds",
        "SHENZEN": "Shenzen",
        "SHENZHEN": "Shenzen",
        "SZSE": "Shenzen",
        "SHANGHAI": "Shanghai",
        "SSE": "Shanghai",
    }

    # Tiingo subscription guardrails
    _MAX_REQUESTS_PER_HOUR = 50
    _MAX_REQUESTS_PER_DAY = 1000
    _MAX_BANDWIDTH_BYTES_PER_MONTH = 1_000_000_000  # 1 GB

    def __init__(self) -> None:
        self._client: Optional[TiingoClient] = None
        self._enabled = bool(settings.TIINGO_API_KEY)

        self._hour_window_start: datetime = datetime.now(UTC).replace(
            minute=0, second=0, microsecond=0
        )
        self._hour_count = 0

        self._day_window_start = datetime.now(UTC).date()
        self._day_count = 0

        self._month_window_start = datetime.now(UTC).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        self._month_bandwidth_bytes = 0

        self._ticker_catalog_cache: Optional[list[dict]] = None
        self._ticker_catalog_cached_at: Optional[datetime] = None

    def _get_client(self) -> Optional[TiingoClient]:
        if not self._enabled:
            return None

        if self._client is None:
            config = {
                "session": True,
                "api_key": settings.TIINGO_API_KEY,
            }
            self._client = TiingoClient(config)

        return self._client

    async def get_current_price(self, ticker: str) -> tuple[date, int]:
        client = self._get_client()
        if client is None:
            return (date.today(), 0)

        candidates = self._build_symbol_candidates(ticker, "USD")

        for symbol in candidates:
            if not self._can_make_request():
                return (date.today(), 0)

            try:
                payload = client.get_ticker_price(symbol)
                self._register_usage_bytes(self._estimate_bytes(payload))

                rows = payload if isinstance(payload, list) else []
                if not rows:
                    continue

                row = rows[-1]
                close = row.get("close") or row.get("adjClose")
                if close is None:
                    continue

                date_str = str(row.get("date") or "")
                parsed_date = date.today()
                if date_str:
                    try:
                        parsed_date = datetime.fromisoformat(
                            date_str.replace("Z", "+00:00")
                        ).date()
                    except Exception:
                        parsed_date = date.today()

                return (parsed_date, round(float(close) * 100))
            except Exception:
                continue

        return (date.today(), 0)

    async def get_asset_metadata(
        self, ticker: str, currency: str = "USD"
    ) -> Optional[AssetMetadata]:
        client = self._get_client()
        if client is None:
            logger.debug("TIINGO_API_KEY is not configured; skipping Tiingo lookup")
            return None

        exchange_hint, base_ticker = self._parse_exchange_qualified_ticker(ticker)

        candidates = self._build_symbol_candidates(base_ticker, currency)

        if exchange_hint:
            resolved = self._resolve_ticker_for_exchange(
                client, base_ticker=base_ticker, exchange_hint=exchange_hint
            )
            if resolved:
                candidates = [resolved, *candidates]

        info = self._lookup_metadata(client, candidates)

        if not info:
            return None

        metadata_currency = info.get("currency", currency)
        currency_value = self._safe_currency(metadata_currency, currency)

        return AssetMetadata(
            ticker=ticker,
            name=info.get("name") or base_ticker,
            asset_class=self._determine_asset_class(info),
            currency=currency_value,
            exchange=info.get("exchangeCode") or info.get("exchange"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            country=info.get("countryCode") or info.get("country"),
            isin=info.get("isin"),
        )

    def _lookup_metadata(
        self, client: TiingoClient, candidates: list[str]
    ) -> Optional[dict]:
        seen = set()
        for symbol in candidates:
            if not symbol or symbol in seen:
                continue

            seen.add(symbol)
            if not self._can_make_request():
                return None

            try:
                info = client.get_ticker_metadata(symbol)
                self._register_usage_bytes(self._estimate_bytes(info))
                if info and info.get("ticker"):
                    return info
            except Exception as e:
                logger.debug(f"Tiingo metadata lookup failed for {symbol}: {e}")

        return None

    def _resolve_ticker_for_exchange(
        self, client: TiingoClient, base_ticker: str, exchange_hint: str
    ) -> Optional[str]:
        canonical_exchange = self._canonical_exchange(exchange_hint)
        if not canonical_exchange:
            return None

        tickers = self._get_cached_stock_tickers(client)
        if tickers is None:
            return None

        target = base_ticker.upper()
        for item in tickers:
            symbol = str(item.get("ticker", "")).upper()
            exchange = str(item.get("exchange", ""))
            if symbol == target and self._exchange_matches(
                exchange, canonical_exchange
            ):
                return symbol

        return None

    def _get_cached_stock_tickers(self, client: TiingoClient) -> Optional[list[dict]]:
        now = datetime.now(UTC)
        if (
            self._ticker_catalog_cache is not None
            and self._ticker_catalog_cached_at is not None
            and now - self._ticker_catalog_cached_at <= timedelta(hours=12)
        ):
            return self._ticker_catalog_cache

        if not self._can_make_request():
            return None

        try:
            tickers = client.list_stock_tickers()
            self._register_usage_bytes(self._estimate_bytes(tickers))
            self._ticker_catalog_cache = tickers
            self._ticker_catalog_cached_at = now
            return tickers
        except Exception as e:
            logger.debug(f"Tiingo ticker-list lookup failed: {e}")
            return None

    def _can_make_request(self) -> bool:
        now = datetime.now(UTC)

        hour_start = now.replace(minute=0, second=0, microsecond=0)
        if hour_start != self._hour_window_start:
            self._hour_window_start = hour_start
            self._hour_count = 0

        day_start = now.date()
        if day_start != self._day_window_start:
            self._day_window_start = day_start
            self._day_count = 0

        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start != self._month_window_start:
            self._month_window_start = month_start
            self._month_bandwidth_bytes = 0

        if self._hour_count >= self._MAX_REQUESTS_PER_HOUR:
            logger.warning("Tiingo hourly request limit reached; skipping request")
            return False

        if self._day_count >= self._MAX_REQUESTS_PER_DAY:
            logger.warning("Tiingo daily request limit reached; skipping request")
            return False

        if self._month_bandwidth_bytes >= self._MAX_BANDWIDTH_BYTES_PER_MONTH:
            logger.warning("Tiingo monthly bandwidth limit reached; skipping request")
            return False

        self._hour_count += 1
        self._day_count += 1
        return True

    def _register_usage_bytes(self, bytes_used: int) -> None:
        self._month_bandwidth_bytes += max(bytes_used, 0)

    @staticmethod
    def _estimate_bytes(payload: object) -> int:
        try:
            return len(json.dumps(payload, default=str).encode("utf-8"))
        except Exception:
            return 0

    def _canonical_exchange(self, exchange_hint: str) -> Optional[str]:
        normalized = " ".join(exchange_hint.upper().split())
        return self._SUPPORTED_EXCHANGES.get(normalized, exchange_hint)

    @staticmethod
    def _exchange_matches(exchange: str, expected: str) -> bool:
        return exchange.strip().lower() == expected.strip().lower()

    @staticmethod
    def _parse_exchange_qualified_ticker(ticker: str) -> tuple[Optional[str], str]:
        normalized = ticker.strip()
        for separator in (":", "/", "|"):
            if separator in normalized:
                left, right = normalized.split(separator, 1)
                left = left.strip()
                right = right.strip()
                if left and right:
                    return left, right
        return None, normalized

    @staticmethod
    def _build_symbol_candidates(base_ticker: str, currency: str) -> list[str]:
        raw = base_ticker.upper().strip()

        variants = [raw]
        if "." in raw:
            variants.append(raw.replace(".", "-"))
        if "-" in raw:
            variants.append(raw.replace("-", "."))

        candidates: list[str] = []
        seen = set()
        for variant in variants:
            for symbol in (variant, f"{variant}-{currency.upper()}"):
                if symbol not in seen:
                    seen.add(symbol)
                    candidates.append(symbol)

        return candidates

    @staticmethod
    def _safe_currency(value: str, fallback: str) -> Currency:
        try:
            return Currency(value)
        except ValueError:
            try:
                return Currency(fallback)
            except ValueError:
                return Currency.USD

    @staticmethod
    def _determine_asset_class(info: dict) -> str:
        raw_type = str(info.get("assetType", "")).lower()
        if "etf" in raw_type or "fund" in raw_type:
            return "etf"
        if "crypto" in raw_type:
            return "crypto"
        return "stock"
