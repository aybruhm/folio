from infrastructure.market_data.ngnmarket_adapter import NgnMarketAdapter
from infrastructure.market_data.ngxpulse_adapter import NgxPulseAdapter
from infrastructure.market_data.tiingo_adapter import TiingoAdapter
from infrastructure.market_data.tradingview_adapter import TradingviewAdapter
from infrastructure.market_data.yfinance_adapter import YFinanceAdapter
from domain.services.market_data import normalize_provider


class CsvImportMarketDataGateway:
    def __init__(self):
        self.adapters = {
            "yfinance": YFinanceAdapter(),
            "tiingo": TiingoAdapter(),
            "ngnmarket": NgnMarketAdapter(),
            "ngxpulse": NgxPulseAdapter(),
            "tradingview": TradingviewAdapter(),
        }

    async def get_asset_metadata(self, ticker, currency, provider, asset_class):
        order = {
            "tiingo": ["tiingo", "tradingview", "ngnmarket", "yfinance"],
            "ngnmarket": ["ngnmarket", "tradingview", "tiingo", "yfinance"],
            "tradingview": ["tradingview", "tiingo", "ngnmarket", "yfinance"],
            "ngxpulse": ["ngxpulse", "tiingo", "tradingview", "yfinance"],
            "yfinance": ["yfinance"],
        }[normalize_provider(provider)]
        for name in order:
            adapter = self.adapters[name]
            if name in {"ngnmarket", "ngxpulse"}:
                metadata = await adapter.get_asset_metadata(
                    ticker, currency.value, asset_class
                )
            else:
                metadata = await adapter.get_asset_metadata(ticker, currency.value)
            if metadata:
                return metadata
        return None
