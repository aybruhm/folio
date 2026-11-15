from infrastructure.market_data.yfinance_adapter import YFinanceAdapter


class BenchmarkFxGateway:
    def adapter(self):
        return YFinanceAdapter()
