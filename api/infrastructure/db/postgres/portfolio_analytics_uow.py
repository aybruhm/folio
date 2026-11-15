from application.analytics.analytics_interactor import AnalyticsInteractor
from application.portfolio.portfolio_interactor import PortfolioInteractor
from domain.value_objects.money import Currency
from infrastructure.db.postgres.engine import async_session
from infrastructure.db.postgres.assets.dao import AssetRepository
from infrastructure.db.postgres.prices.dao import FxRateRepository, PriceHistoryRepository
from infrastructure.db.postgres.trades.dao import TradeRepository
from infrastructure.market_data.analytics_gateway import AnalyticsMarketDataGateway


class PortfolioAnalyticsUnitOfWork:
    async def __aenter__(self):
        self.session = async_session()
        from infrastructure.db.postgres.portfolios.dao import PortfolioRepository

        self.portfolio_interactor = PortfolioInteractor(
            PortfolioRepository(self.session)
        )
        return self

    def analytics_interactor(self, currency: Currency) -> AnalyticsInteractor:
        return AnalyticsInteractor(
            TradeRepository(self.session),
            AssetRepository(self.session),
            PriceHistoryRepository(self.session),
            FxRateRepository(self.session),
            currency,
            AnalyticsMarketDataGateway(),
        )

    async def __aexit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type:
                await self.session.rollback()
            else:
                await self.session.commit()
        finally:
            await self.session.close()
