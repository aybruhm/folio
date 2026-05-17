import json
import logging
from datetime import date, timedelta
from typing import Optional

import valkey.asyncio as valkey

from domain.value_objects.money import AssetMetadata, Currency
from infrastructure.cache.valkey_client import get_valkey_client
from infrastructure.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Key builders
# ---------------------------------------------------------------------------

_PREFIX = "folio"

_KEY_PRICE = f"{_PREFIX}:price:{{ticker}}"
_KEY_META = f"{_PREFIX}:meta:{{ticker}}"
_KEY_FX_CURRENT = f"{_PREFIX}:fx:{{from_ccy}}_{{to_ccy}}"
_KEY_FX_HISTORICAL = f"{_PREFIX}:fx:{{from_ccy}}_{{to_ccy}}:{{date_val}}"


def _price_key(ticker: str) -> str:
    return _KEY_PRICE.format(ticker=ticker.upper())


def _meta_key(ticker: str) -> str:
    return _KEY_META.format(ticker=ticker.upper())


def _fx_current_key(from_ccy: str, to_ccy: str) -> str:
    return _KEY_FX_CURRENT.format(from_ccy=from_ccy.upper(), to_ccy=to_ccy.upper())


def _fx_historical_key(from_ccy: str, to_ccy: str, date_val: date) -> str:
    return _KEY_FX_HISTORICAL.format(
        from_ccy=from_ccy.upper(),
        to_ccy=to_ccy.upper(),
        date_val=date_val.isoformat(),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class PriceCache:
    """Async cache facade over Valkey for market data: prices, metadata, and FX rates.

    Cache key convention
    --------------------
    All keys are prefixed with ``folio:`` and namespaced by data type:

    * ``folio:price:{ticker}``      — current price as ``date_iso,int``
    * ``folio:meta:{ticker}``       — JSON-serialised ``AssetMetadata``
    * ``folio:fx:{from}_{to}``      — current FX rate as ``int`` (×100)
    * ``folio:fx:{from}_{to}:{date}`` — historical FX rate as ``int`` (×100)

    Default TTL is 30 minutes (1800 s), configurable via
    ``MARKET_DATA_CACHE_TTL``.
    """

    def __init__(self, ttl_seconds: int | None = None) -> None:
        self._ttl = (
            ttl_seconds if ttl_seconds is not None else settings.MARKET_DATA_CACHE_TTL
        )

    # -- client -----------------------------------------------------------

    @property
    def _client(self) -> valkey.Valkey:
        return get_valkey_client()

    # -- price ------------------------------------------------------------

    async def get_price(self, ticker: str) -> Optional[tuple[date, int]]:
        """Return ``(date, price×100)`` if cached, else ``None``.

        A cached value of ``(date.min, 0)`` is the sentinel meaning
        "not found / price unavailable" — it is treated as a cache hit
        so the caller does NOT re-query upstream providers.
        """
        try:
            raw = await self._client.get(_price_key(ticker))
            if raw is None:
                logger.info("Cache MISS (price): %s", ticker)
                return None
            date_str, price_str = raw.split(",", 1)
            p = int(price_str)
            logger.info(
                "Cache HIT (price): %s → %s,%s %s",
                ticker,
                date_str,
                price_str,
                "(SENTINEL — not found)" if p == 0 else "",
            )
            return (date.fromisoformat(date_str), p)
        except Exception as exc:
            logger.warning("Valkey get_price(%s) failed: %s", ticker, exc)
            return None

    async def set_price(self, ticker: str, price_date: date, price: int) -> None:
        """Cache *price* (×100 int) for *ticker*.

        Pass ``price=0`` to cache a "not found" sentinel and prevent
        repeated upstream calls for unsupported tickers.
        """
        try:
            value = f"{price_date.isoformat()},{price}"
            await self._client.set(_price_key(ticker), value, ex=self._ttl)
            logger.info(
                "Cache SET (price): %s → %s,%s (TTL=%ss)%s",
                ticker,
                price_date,
                price,
                self._ttl,
                " [SENTINEL]" if price == 0 else "",
            )
        except Exception as exc:
            logger.warning("Valkey set_price(%s) failed: %s", ticker, exc)

    # -- metadata ---------------------------------------------------------

    async def get_metadata(self, ticker: str) -> Optional[AssetMetadata]:
        """Return cached ``AssetMetadata`` or ``None``."""
        try:
            raw = await self._client.get(_meta_key(ticker))
            if raw is None:
                logger.info("Cache MISS (metadata): %s", ticker)
                return None
            data = json.loads(raw)
            logger.info("Cache HIT (metadata): %s → %s", ticker, data.get("name", ""))
            return AssetMetadata(
                ticker=data["ticker"],
                name=data["name"],
                asset_class=data["asset_class"],
                currency=Currency(data["currency"]),
                exchange=data.get("exchange"),
                sector=data.get("sector"),
                industry=data.get("industry"),
                country=data.get("country"),
                isin=data.get("isin"),
            )
        except Exception as exc:
            logger.warning("Valkey get_metadata(%s) failed: %s", ticker, exc)
            return None

    async def set_metadata(self, metadata: AssetMetadata) -> None:
        """Cache *metadata*."""
        try:
            payload = {
                "ticker": metadata.ticker,
                "name": metadata.name,
                "asset_class": metadata.asset_class,
                "currency": metadata.currency.value,
                "exchange": metadata.exchange,
                "sector": metadata.sector,
                "industry": metadata.industry,
                "country": metadata.country,
                "isin": metadata.isin,
            }
            await self._client.set(
                _meta_key(metadata.ticker),
                json.dumps(payload),
                ex=self._ttl,
            )
            logger.info(
                "Cache SET (metadata): %s → %s (TTL=%ss)",
                metadata.ticker,
                metadata.name,
                self._ttl,
            )
        except Exception as exc:
            logger.warning("Valkey set_metadata(%s) failed: %s", metadata.ticker, exc)

    # -- FX rates ---------------------------------------------------------

    async def get_fx_rate(self, from_ccy: str, to_ccy: str) -> Optional[int]:
        """Return cached current FX rate (×100 int) or ``None``."""
        try:
            raw = await self._client.get(_fx_current_key(from_ccy, to_ccy))
            if raw is None:
                logger.info("Cache MISS (FX): %s/%s", from_ccy, to_ccy)
                return None
            rate = int(raw)
            logger.info("Cache HIT (FX): %s/%s → %s", from_ccy, to_ccy, rate)
            return rate
        except Exception as exc:
            logger.warning(
                "Valkey get_fx_rate(%s,%s) failed: %s", from_ccy, to_ccy, exc
            )
            return None

    async def set_fx_rate(self, from_ccy: str, to_ccy: str, rate: int) -> None:
        """Cache *rate* (×100 int) for the given currency pair."""
        try:
            await self._client.set(
                _fx_current_key(from_ccy, to_ccy), str(rate), ex=self._ttl
            )
            logger.info(
                "Cache SET (FX): %s/%s → %s (TTL=%ss)",
                from_ccy,
                to_ccy,
                rate,
                self._ttl,
            )
        except Exception as exc:
            logger.warning(
                "Valkey set_fx_rate(%s,%s) failed: %s", from_ccy, to_ccy, exc
            )

    async def get_historical_fx_rate(
        self, from_ccy: str, to_ccy: str, date_val: date
    ) -> Optional[int]:
        """Return cached historical FX rate or ``None``."""
        try:
            raw = await self._client.get(_fx_historical_key(from_ccy, to_ccy, date_val))
            if raw is None:
                logger.info(
                    "Cache MISS (FX hist): %s/%s @ %s", from_ccy, to_ccy, date_val
                )
                return None
            rate = int(raw)
            logger.info(
                "Cache HIT (FX hist): %s/%s @ %s → %s",
                from_ccy,
                to_ccy,
                date_val,
                rate,
            )
            return rate
        except Exception as exc:
            logger.warning(
                "Valkey get_historical_fx_rate(%s,%s,%s) failed: %s",
                from_ccy,
                to_ccy,
                date_val,
                exc,
            )
            return None

    async def set_historical_fx_rate(
        self, from_ccy: str, to_ccy: str, date_val: date, rate: int
    ) -> None:
        """Cache a historical FX rate (longer TTL — 7 days)."""
        try:
            await self._client.set(
                _fx_historical_key(from_ccy, to_ccy, date_val),
                str(rate),
                ex=int(timedelta(days=7).total_seconds()),
            )
            logger.info(
                "Cache SET (FX hist): %s/%s @ %s → %s",
                from_ccy,
                to_ccy,
                date_val,
                rate,
            )
        except Exception as exc:
            logger.warning(
                "Valkey set_historical_fx_rate(%s,%s,%s) failed: %s",
                from_ccy,
                to_ccy,
                date_val,
                exc,
            )

    # -- bulk invalidation ------------------------------------------------

    async def invalidate_ticker(self, ticker: str) -> None:
        """Remove price + metadata keys for *ticker*."""
        try:
            await self._client.delete(_price_key(ticker), _meta_key(ticker))
        except Exception as exc:
            logger.warning("Valkey invalidate_ticker(%s) failed: %s", ticker, exc)

    async def invalidate_fx(self, from_ccy: str, to_ccy: str) -> None:
        """Remove current FX rate key for the currency pair."""
        try:
            await self._client.delete(_fx_current_key(from_ccy, to_ccy))
        except Exception as exc:
            logger.warning(
                "Valkey invalidate_fx(%s,%s) failed: %s", from_ccy, to_ccy, exc
            )
