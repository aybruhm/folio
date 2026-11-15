from domain.services.market_data import normalize_provider
from infrastructure.market_data.ngnmarket_adapter import NgnMarketAdapter
from infrastructure.market_data.ngxpulse_adapter import NgxPulseAdapter
from infrastructure.market_data.tiingo_adapter import TiingoAdapter
from infrastructure.market_data.tradingview_adapter import TradingviewAdapter
from infrastructure.market_data.yfinance_adapter import YFinanceAdapter


class TradeMarketDataGateway:
    def __init__(self):
        self.adapters = {
            "yfinance": YFinanceAdapter(),
            "tiingo": TiingoAdapter(),
            "ngnmarket": NgnMarketAdapter(),
            "ngxpulse": NgxPulseAdapter(),
            "tradingview": TradingviewAdapter(),
        }

    async def get_asset_metadata(self, ticker, currency, provider):
        return await self.adapters[normalize_provider(provider)].get_asset_metadata(
            ticker, currency.value
        )
