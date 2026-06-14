import logging
from datetime import date, timedelta
from typing import List, Optional, Tuple

import yfinance as yf

from adapters.outbound.market_data.price_cache import PriceCache
from domain.ports.outbound.repositories import IAssetPricePort, IFxRatePort
from domain.value_objects.money import AssetMetadata, Currency

logger = logging.getLogger(__name__)


class YFinanceAdapter(IAssetPricePort, IFxRatePort):
    def __init__(self) -> None:
        self.cache = PriceCache()

    @staticmethod
    def _scalar(value) -> float:
        """Extract a plain float from a value that may be a pandas Series or scalar."""
        if hasattr(value, "item"):
            return value.item()
        if hasattr(value, "iloc"):
            return float(value.iloc[0])
        return float(value)

    async def get_price_history(
        self, ticker: str, start: date, end: date
    ) -> List[Tuple[date, int]]:
        logger.debug("yfinance: fetching price history for %s (%s → %s)", ticker, start, end)
        try:
            t = yf.Ticker(ticker)
            data = t.history(start=start, end=end)
            if data.empty:
                logger.warning("yfinance: no price history returned for %s (%s → %s)", ticker, start, end)
                return []

            result = [
                (idx.date(), round(float(row["Close"]) * 100))
                for idx, row in data.iterrows()
            ]
            logger.info("yfinance: price history OK for %s — %d data points", ticker, len(result))
            return result
        except Exception as e:
            logger.error("yfinance: price history failed for %s: %s", ticker, e)
            return []

    async def get_current_price(self, ticker: str) -> Tuple[date, int]:
        # Check Valkey cache first
        cached = await self.cache.get_price(ticker)
        if cached is not None:
            return cached

        logger.debug("yfinance: fetching current price for %s", ticker)
        try:
            t = yf.Ticker(ticker)
            data = t.history(period="1d")
            if data.empty:
                logger.warning("yfinance: no current price returned for %s", ticker)
                await self.cache.set_price(ticker, date.today(), 0)
                return (date.today(), 0)

            price_date = data.index[-1].date()
            close = round(float(data["Close"].iloc[-1]) * 100)
            logger.info("yfinance: current price OK for %s — %.2f on %s", ticker, close / 100, price_date)

            await self.cache.set_price(ticker, price_date, close)
            return (price_date, close)
        except Exception as e:
            logger.error("yfinance: current price failed for %s: %s", ticker, e)
            await self.cache.set_price(ticker, date.today(), 0)
            return (date.today(), 0)

    async def get_asset_metadata(
        self, ticker: str, currency: str = "USD"
    ) -> Optional[AssetMetadata]:
        # Check Valkey cache first
        cached = await self.cache.get_metadata(ticker)
        if cached is not None:
            return cached

        symbols = [ticker, f"{ticker.upper()}-{currency}"]

        if self._is_fx_pair(ticker):
            symbols.extend(
                [f"{ticker.upper()}=X", f"{ticker[:3].upper()}{ticker[3:].upper()}=X"]
            )
        for symbol in symbols:
            logger.debug("yfinance: fetching metadata for %s (symbol=%s)", ticker, symbol)
            try:
                info = yf.Ticker(symbol).info
                if not info or "currency" not in info:
                    logger.debug("yfinance: no usable metadata for symbol=%s", symbol)
                    continue

                asset_class = self._determine_asset_class(symbol, info)
                name = info.get("longName") or info.get("shortName") or ticker
                metadata = AssetMetadata(
                    ticker=ticker,
                    name=name,
                    asset_class=asset_class,
                    currency=Currency(info.get("currency", currency)),
                    exchange=info.get("exchange"),
                    sector=info.get("sector"),
                    industry=info.get("industry"),
                    country=info.get("country"),
                    isin=info.get("isin"),
                )
                logger.info(
                    "yfinance: metadata OK for %s — name=%r asset_class=%s currency=%s",
                    ticker, name, asset_class, info.get("currency", currency),
                )
                await self.cache.set_metadata(metadata)
                return metadata
            except Exception as e:
                logger.error("yfinance: metadata failed for symbol=%s: %s", symbol, e)

        logger.warning("yfinance: no metadata found for %s (tried %d symbols)", ticker, len(symbols))
        return None

    async def get_fx_rate(
        self, from_currency: Currency, to_currency: Currency, on_date: date
    ) -> Optional[int]:
        if from_currency == to_currency:
            return 100  # 1.00 × 100

        # Check Valkey historical FX cache
        cached = await self.cache.get_historical_fx_rate(
            from_currency.value, to_currency.value, on_date
        )
        if cached is not None:
            return cached

        ticker = f"{from_currency.value}{to_currency.value}=X"
        logger.debug(
            "yfinance: fetching historical FX rate %s/%s on %s",
            from_currency.value, to_currency.value, on_date,
        )
        try:
            t = yf.Ticker(ticker)
            data = t.history(start=on_date, end=on_date + timedelta(days=1))

            if data.empty:
                logger.warning(
                    "yfinance: no historical FX rate returned for %s/%s on %s",
                    from_currency.value, to_currency.value, on_date,
                )
                return None

            rate = round(float(data["Close"].iloc[-1]) * 100)
            logger.info(
                "yfinance: historical FX rate OK for %s/%s on %s — %.4f",
                from_currency.value, to_currency.value, on_date, rate / 100,
            )
            await self.cache.set_historical_fx_rate(
                from_currency.value, to_currency.value, on_date, rate
            )
            return rate
        except Exception as e:
            logger.error(
                "yfinance: historical FX rate failed for %s/%s on %s: %s",
                from_currency.value, to_currency.value, on_date, e,
            )
            return None

    async def get_current_rate(
        self, from_currency: Currency, to_currency: Currency
    ) -> Optional[int]:
        if from_currency == to_currency:
            return 100  # 1.00 × 100

        # Check Valkey cache first
        cached = await self.cache.get_fx_rate(from_currency.value, to_currency.value)
        if cached is not None:
            return cached

        ticker = f"{from_currency.value}{to_currency.value}=X"
        logger.debug(
            "yfinance: fetching current FX rate %s/%s",
            from_currency.value, to_currency.value,
        )
        try:
            t = yf.Ticker(ticker)
            data = t.history(period="1d")

            if data.empty:
                logger.warning(
                    "yfinance: no current FX rate returned for %s/%s",
                    from_currency.value, to_currency.value,
                )
                return None

            rate = round(float(data["Close"].iloc[-1]) * 100)
            logger.info(
                "yfinance: current FX rate OK for %s/%s — %.4f",
                from_currency.value, to_currency.value, rate / 100,
            )
            await self.cache.set_fx_rate(from_currency.value, to_currency.value, rate)
            return rate
        except Exception as e:
            logger.error(
                "yfinance: current FX rate failed for %s/%s: %s",
                from_currency.value, to_currency.value, e,
            )
            return None

    @staticmethod
    def _determine_asset_class(ticker: str, info: dict) -> str:
        if ticker.endswith("=X"):
            return "cash"

        if "-" in ticker:
            return "crypto"

        if "quoteType" in info:
            quote_type = info["quoteType"].lower()
            if quote_type == "cryptocurrency":
                return "crypto"
            if quote_type in ["etf", "fund"]:
                return "etf"
            if quote_type == "equity":
                return "stock"

        return "stock"

    @staticmethod
    def _is_fx_pair(ticker: str) -> bool:
        upper_ticker = ticker.upper()
        return len(upper_ticker) == 6 and upper_ticker.isalpha()
