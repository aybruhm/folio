import logging
from datetime import date, timedelta
from typing import List, Optional, Tuple

import yfinance as yf

from adapters.outbound.market_data.ngnmarket_adapter import NgnMarketAdapter
from adapters.outbound.market_data.tiingo_adapter import TiingoAdapter
from domain.ports.outbound.repositories import IAssetPricePort, IFxRatePort
from domain.value_objects.money import AssetMetadata, Currency

logger = logging.getLogger(__name__)


class YFinanceAdapter(IAssetPricePort, IFxRatePort):
    def __init__(self) -> None:
        self.tiingo = TiingoAdapter()
        self.ngnmarket = NgnMarketAdapter()

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
        try:
            t = yf.Ticker(ticker)
            data = t.history(period="1d")
            if data.empty:
                logger.warning(f"No current price found for {ticker}")
                return (date.today(), 0)

            close = float(data["Close"].iloc[-1])
            return (data.index[-1].date(), round(close * 100))
        except Exception as e:
            logger.error(f"Error fetching current price for {ticker}: {e}")
            return (date.today(), 0)

    async def get_asset_metadata(
        self, ticker: str, currency: str = "USD"
    ) -> Optional[AssetMetadata]:
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
                return AssetMetadata(
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
            except Exception as e:
                logger.error(f"Error fetching metadata for {symbol}: {e}")

        tiingo_metadata = await self.tiingo.get_asset_metadata(ticker, currency)
        if tiingo_metadata:
            logger.info(f"Using Tiingo fallback metadata for {ticker}")
            return tiingo_metadata

        ngnmarket_metadata = await self.ngnmarket.get_asset_metadata(ticker, currency)
        if ngnmarket_metadata:
            logger.info(f"Using NGNMarket fallback metadata for {ticker}")
            return ngnmarket_metadata

        logger.warning(f"Incomplete metadata for {ticker}")
        return None

    async def get_fx_rate(
        self, from_currency: Currency, to_currency: Currency, date: date
    ) -> Optional[int]:
        if from_currency == to_currency:
            return 100  # 1.00 × 100

        try:
            ticker = f"{from_currency.value}{to_currency.value}=X"
            t = yf.Ticker(ticker)
            data = t.history(start=date, end=date + timedelta(days=1))

            if data.empty:
                logger.warning(f"No FX rate found for {ticker} on {date}")
                return await self.ngnmarket.get_fx_rate(
                    from_currency, to_currency, date
                )

            return round(float(data["Close"].iloc[-1]) * 100)
        except Exception as e:
            logger.error(f"Error fetching FX rate {from_currency}/{to_currency}: {e}")
            return await self.ngnmarket.get_fx_rate(from_currency, to_currency, date)

    async def get_current_rate(
        self, from_currency: Currency, to_currency: Currency
    ) -> Optional[int]:
        if from_currency == to_currency:
            return 100  # 1.00 × 100

        try:
            ticker = f"{from_currency.value}{to_currency.value}=X"
            t = yf.Ticker(ticker)
            data = t.history(period="1d")

            if data.empty:
                logger.warning(f"No current rate found for {ticker}")
                return await self.ngnmarket.get_current_rate(from_currency, to_currency)

            return round(float(data["Close"].iloc[-1]) * 100)
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
