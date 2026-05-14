import asyncio
import logging
from datetime import date
from typing import Optional

import aiohttp

from domain.value_objects.money import AssetMetadata, Currency
from infrastructure.config import settings

logger = logging.getLogger(__name__)


class NgnMarketAdapter:
    _shared_session: Optional[aiohttp.ClientSession] = None
    _session_lock: Optional[asyncio.Lock] = None
    _shared_timeout = aiohttp.ClientTimeout(total=15)

    def __init__(self) -> None:
        self._base_url = (settings.NGNMARKET_API_BASE_URL or "").rstrip("/")
        self._api_key = settings.NGNMARKET_API_KEY
        self._enabled = bool(self._base_url and self._api_key)

    async def get_asset_metadata(
        self, ticker: str, currency: str = "NGN"
    ) -> Optional[AssetMetadata]:
        # NGNMarket currently exposes indices endpoints; use index detail as ETF-like fallback metadata.
        symbol = self._extract_symbol(ticker)
        if not symbol:
            return None

        detail = await self.get_index_detail(symbol)
        if not detail:
            return None

        try:
            resolved_currency = self._safe_currency(currency)
            return AssetMetadata(
                ticker=ticker,
                name=detail.get("name") or symbol,
                asset_class="etf",
                currency=resolved_currency,
                exchange="NGX",
                sector=None,
                industry=None,
                country="NG",
                isin=None,
            )
        except Exception as e:
            logger.debug(f"NGNMarket metadata mapping failed for {ticker}: {e}")
            return None

    async def get_current_forex_rates(self) -> Optional[dict]:
        payload = await self._get("/forex/current")
        if not payload or not payload.get("success"):
            return None
        return payload.get("data")

    async def get_historical_forex_rates(
        self,
        source: Currency,
        target: Currency,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[list[dict]]:
        params = {
            "source": source.value,
            "target": target.value,
        }
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()

        payload = await self._get("/forex/history", params=params)
        if not payload or not payload.get("success"):
            return None
        return payload.get("data") or []

    async def get_current_rate(
        self, from_currency: Currency, to_currency: Currency
    ) -> Optional[int]:
        if from_currency == to_currency:
            return 100

        rates_payload = await self.get_current_forex_rates()
        if not rates_payload:
            return None

        base = str(rates_payload.get("base", "")).upper()
        rates = rates_payload.get("rates", {})

        rate_float = self._extract_rate(
            from_currency=from_currency.value,
            to_currency=to_currency.value,
            base=base,
            rates=rates,
        )
        if rate_float is None:
            return None

        return round(rate_float * 100)

    async def get_fx_rate(
        self, from_currency: Currency, to_currency: Currency, on_date: date
    ) -> Optional[int]:
        if from_currency == to_currency:
            return 100

        history = await self.get_historical_forex_rates(
            source=from_currency,
            target=to_currency,
            start_date=on_date,
            end_date=on_date,
        )
        if not history:
            return None

        # choose exact date first; fallback to first returned datapoint
        target_row = next(
            (item for item in history if str(item.get("date")) == on_date.isoformat()),
            history[0],
        )

        rate = target_row.get("rate")
        if rate is None:
            return None

        try:
            return round(float(rate) * 100)
        except Exception:
            return None

    async def list_indices(self) -> Optional[list[dict]]:
        payload = await self._get("/indices")
        if not payload or not payload.get("success"):
            return None
        return payload.get("data") or []

    async def get_index_detail(self, symbol: str) -> Optional[dict]:
        payload = await self._get(f"/indices/{symbol.upper()}")
        if not payload or not payload.get("success"):
            return None
        return payload.get("data")

    async def get_index_chart(
        self, symbol: str, period: str = "30d", response_format: str = "detailed"
    ) -> Optional[dict]:
        payload = await self._get(
            f"/indices/{symbol.upper()}/chart",
            params={"period": period, "format": response_format},
        )
        if not payload or not payload.get("success"):
            return None
        return payload.get("data")

    async def _get(self, path: str, params: Optional[dict] = None) -> Optional[dict]:
        if not self._enabled:
            return None

        url = f"{self._base_url}{path}"
        headers = {"Authorization": f"Bearer {self._api_key}"}

        try:
            session = await self._get_shared_session()
            async with session.get(url, params=params, headers=headers) as response:
                status_code = response.status
                body_text = await response.text()

                if status_code >= 400:
                    self._log_api_error(path, status_code, body_text)
                    return None

                try:
                    return await response.json()
                except Exception:
                    logger.warning("NGNMarket GET %s returned non-JSON response", path)
                    return None
        except Exception as e:
            logger.warning(f"NGNMarket GET {path} failed: {e}")
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
                if left.strip().upper() in {"NGX", "NGNMARKET"}:
                    return right.strip().upper()
        return raw.upper()

    @staticmethod
    def _safe_currency(value: str) -> Currency:
        try:
            return Currency(value.upper())
        except ValueError:
            return Currency.USD

    @staticmethod
    def _extract_rate(
        from_currency: str, to_currency: str, base: str, rates: dict
    ) -> Optional[float]:
        # /forex/current returns rates relative to base currency (example: base NGN)
        # If base=NGN and rates[USD]=0.000623 then 1 NGN = 0.000623 USD
        # Therefore USD->NGN = 1 / rates[USD]
        from_ccy = from_currency.upper()
        to_ccy = to_currency.upper()
        base_ccy = base.upper()

        if from_ccy == to_ccy:
            return 1.0

        try:
            if from_ccy == base_ccy and to_ccy in rates:
                return float(rates[to_ccy])
            if to_ccy == base_ccy and from_ccy in rates:
                value = float(rates[from_ccy])
                return (1.0 / value) if value else None
            if from_ccy in rates and to_ccy in rates:
                from_v = float(rates[from_ccy])
                to_v = float(rates[to_ccy])
                return to_v / from_v if from_v else None
        except Exception:
            return None

        return None

    @staticmethod
    def _log_api_error(path: str, status_code: int, body_text: str) -> None:
        try:
            import json

            payload = json.loads(body_text)
            error = payload.get("error", {})
            code = error.get("code")
            message = error.get("message")
            meta = payload.get("meta", {})
            reset_at = meta.get("reset_at")
            logger.warning(
                "NGNMarket error on %s: status=%s code=%s message=%s reset_at=%s",
                path,
                status_code,
                code,
                message,
                reset_at,
            )
        except Exception:
            logger.warning(
                "NGNMarket error on %s: status=%s body=%s",
                path,
                status_code,
                body_text,
            )
