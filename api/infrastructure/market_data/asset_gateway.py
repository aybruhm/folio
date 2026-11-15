from datetime import date

import yfinance as yf

from domain.value_objects.money import Currency
from infrastructure.market_data.ngnmarket_adapter import NgnMarketAdapter
from infrastructure.market_data.ngxpulse_adapter import NgxPulseAdapter
from infrastructure.market_data.tiingo_adapter import TiingoAdapter
from infrastructure.market_data.tradingview_adapter import TradingviewAdapter
from infrastructure.market_data.yfinance_adapter import YFinanceAdapter
from infrastructure.market_data.yfinance_closes import valid_closes


class AssetGateway:
    adapters = {
        "yfinance": YFinanceAdapter,
        "tiingo": TiingoAdapter,
        "tradingview": TradingviewAdapter,
        "ngnmarket": NgnMarketAdapter,
        "ngxpulse": NgxPulseAdapter,
    }

    def adapter(self, provider: str):
        return self.adapters[provider]()

    async def fx_history(self, currency: str, start: date, end: date) -> dict[date, int]:
        if currency == "USD":
            return {}
        if currency == "NGN":
            try:
                history = await NgnMarketAdapter().get_historical_forex_rates(
                    Currency.NGN, Currency.USD, start_date=start, end_date=end
                )
                result = {
                    date.fromisoformat(str(item["date"])): round(float(item["rate"]) * 100)
                    for item in history
                    if item.get("date") and item.get("rate") is not None
                }
                if result:
                    return result
            except Exception:
                pass
        for ticker, multiplier in (
            (f"{currency}USD=X", 1),
            (f"USD{currency}=X", -1),
        ):
            try:
                closes = valid_closes(yf.Ticker(ticker).history(start=start, end=end))
                if not closes.empty:
                    return {
                        index.date(): multiplier * round(float(close) * 100)
                        for index, close in closes.items()
                    }
            except Exception:
                pass
        return {}
