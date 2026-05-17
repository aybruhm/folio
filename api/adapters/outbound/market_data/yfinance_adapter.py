import logging
from datetime import date, timedelta
from typing import List, Optional, Tuple

import yfinance as yf

from adapters.outbound.market_data.ngnmarket_adapter import NgnMarketAdapter
from adapters.outbound.market_data.price_cache import PriceCache
from adapters.outbound.market_data.tiingo_adapter import TiingoAdapter
from domain.ports.outbound.repositories import IAssetPricePort, IFxRatePort
from domain.value_objects.money import AssetMetadata, Currency

logger = logging.getLogger(__name__)


class YFinanceAdapter(IAssetPricePort, IFxRatePort):
    def __init__(self) -> None:
        self.tiingo = TiingoAdapter()
        self.ngnmarket = NgnMarketAdapter()
        self.cache = PriceCache()
        # Lazy-init TradingView adapter to avoid importing it at module level
        self._tradingview = None

    @property
    def tradingview(self):
        if self._tradingview is None:
            from adapters.outbound.market_data.tradingview_adapter import (
                TradingviewAdapter,
            )

            self._tradingview = TradingviewAdapter()
        return self._tradingview

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
        try:
            t = yf.Ticker(ticker)
            data = t.history(start=start, end=end)
            if data.empty:
                logger.warning(f"No price history found for {ticker}")
                return []

            return [
                (idx.date(), round(float(row["Close"]) * 100))
                for idx, row in data.iterrows()
            ]
        except Exception as e:
            logger.error(f"Error fetching price history for {ticker}: {e}")
            return []

    async def get_current_price(self, ticker: str) -> Tuple[date, int]:
        # Check Valkey cache first
        cached = await self.cache.get_price(ticker)
        if cached is not None:
            return cached

        try:
            t = yf.Ticker(ticker)
            data = t.history(period="1d")
            if data.empty:
                logger.warning(f"No current price found for {ticker}")
                # Cache sentinel so we don't retry within TTL
                await self.cache.set_price(ticker, date.today(), 0)
                return (date.today(), 0)

            price_date = data.index[-1].date()
            close = round(float(data["Close"].iloc[-1]) * 100)

            # Populate Valkey cache
            await self.cache.set_price(ticker, price_date, close)

            return (price_date, close)
        except Exception as e:
            logger.error(f"Error fetching current price for {ticker}: {e}")
            # Cache sentinel so we don't retry within TTL
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
            try:
                info = yf.Ticker(symbol).info
                if not info or "currency" not in info:
                    continue

                asset_class = self._determine_asset_class(symbol, info)
                metadata = AssetMetadata(
                    ticker=ticker,
                    name=info.get("longName") or info.get("shortName") or ticker,
                    asset_class=asset_class,
                    currency=Currency(info.get("currency", currency)),
                    exchange=info.get("exchange"),
                    sector=info.get("sector"),
                    industry=info.get("industry"),
                    country=info.get("country"),
                    isin=info.get("isin"),
                )
                await self.cache.set_metadata(metadata)
                return metadata
            except Exception as e:
                logger.error(f"Error fetching metadata for {symbol}: {e}")

        tiingo_metadata = await self.tiingo.get_asset_metadata(ticker, currency)
        if tiingo_metadata:
            logger.info(f"Using Tiingo fallback metadata for {ticker}")
            await self.cache.set_metadata(tiingo_metadata)
            return tiingo_metadata

        ngnmarket_metadata = await self.ngnmarket.get_asset_metadata(ticker, currency)
        if ngnmarket_metadata:
            logger.info(f"Using NGNMarket fallback metadata for {ticker}")
            await self.cache.set_metadata(ngnmarket_metadata)
            return ngnmarket_metadata

        tradingview_metadata = await self.tradingview.get_asset_metadata(
            ticker, currency
        )
        if tradingview_metadata:
            logger.info(f"Using TradingView fallback metadata for {ticker}")
            await self.cache.set_metadata(tradingview_metadata)
            return tradingview_metadata

        logger.warning(f"Incomplete metadata for {ticker}")
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

        try:
            ticker = f"{from_currency.value}{to_currency.value}=X"
            t = yf.Ticker(ticker)
            data = t.history(start=on_date, end=on_date + timedelta(days=1))

            if data.empty:
                logger.warning(f"No FX rate found for {ticker} on {on_date}")
                rate = await self.ngnmarket.get_fx_rate(
                    from_currency, to_currency, on_date
                )
                if rate is not None:
                    await self.cache.set_historical_fx_rate(
                        from_currency.value, to_currency.value, on_date, rate
                    )
                return rate

            rate = round(float(data["Close"].iloc[-1]) * 100)
            await self.cache.set_historical_fx_rate(
                from_currency.value, to_currency.value, on_date, rate
            )
            return rate
        except Exception as e:
            logger.error(f"Error fetching FX rate {from_currency}/{to_currency}: {e}")
            return await self.ngnmarket.get_fx_rate(from_currency, to_currency, on_date)

    async def get_current_rate(
        self, from_currency: Currency, to_currency: Currency
    ) -> Optional[int]:
        if from_currency == to_currency:
            return 100  # 1.00 × 100

        # Check Valkey cache first
        cached = await self.cache.get_fx_rate(from_currency.value, to_currency.value)
        if cached is not None:
            return cached

        try:
            ticker = f"{from_currency.value}{to_currency.value}=X"
            t = yf.Ticker(ticker)
            data = t.history(period="1d")

            if data.empty:
                logger.warning(f"No current rate found for {ticker}")
                rate = await self.ngnmarket.get_current_rate(from_currency, to_currency)
                if rate is not None:
                    await self.cache.set_fx_rate(
                        from_currency.value, to_currency.value, rate
                    )
                return rate

            rate = round(float(data["Close"].iloc[-1]) * 100)
            await self.cache.set_fx_rate(from_currency.value, to_currency.value, rate)
            return rate
        except Exception as e:
            logger.error(
                f"Error fetching current FX rate {from_currency}/{to_currency}: {e}"
            )
            return await self.ngnmarket.get_current_rate(from_currency, to_currency)

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
