import yfinance as yf

from infrastructure.cache.valkey_client import get_valkey_client
from infrastructure.market_data.ngnmarket_adapter import NgnMarketAdapter
from infrastructure.market_data.ngxpulse_adapter import NgxPulseAdapter
from infrastructure.market_data.price_cache import PriceCache
from infrastructure.market_data.tiingo_adapter import TiingoAdapter
from infrastructure.market_data.tradingview_adapter import TradingviewAdapter
from infrastructure.market_data.yfinance_adapter import YFinanceAdapter
from infrastructure.market_data.yfinance_closes import last_close


class AnalyticsMarketDataGateway:
    def __init__(self):
        self.adapters = {
            "yfinance": YFinanceAdapter(),
            "tiingo": TiingoAdapter(),
            "ngnmarket": NgnMarketAdapter(),
            "ngxpulse": NgxPulseAdapter(),
            "tradingview": TradingviewAdapter(),
        }

    async def current_price(self, provider, symbol):
        if provider == "ngnmarket":
            chart = await self.adapters[provider].get_index_chart(symbol)
            if chart and chart.get("data"):
                item = chart["data"][-1]
                price = item.get("index_value")
                if price is not None:
                    from datetime import date

                    return date.today(), round(float(price) * 100)
            from datetime import date

            return date.today(), 0
        return await self.adapters[provider].get_current_price(symbol)

    def cache(self):
        return PriceCache()

    def ticker(self, symbol):
        return yf.Ticker(symbol)

    def last_close(self, history):
        return last_close(history)
