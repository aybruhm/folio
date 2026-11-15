from application.analytics.analytics_interactor import AnalyticsInteractor
from application.portfolio.portfolio_interactor import PortfolioInteractor
from domain.value_objects.money import Currency
from infrastructure.db.postgres.engine import async_session


class PortfolioAnalyticsUnitOfWork:
    async def __aenter__(self):
        self.session = async_session()
        self.portfolio_interactor = PortfolioInteractor(self.session)
        return self

    def analytics_interactor(self, currency: Currency) -> AnalyticsInteractor:
        return AnalyticsInteractor(self.session, currency)

    async def __aexit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type:
                await self.session.rollback()
            else:
                await self.session.commit()
        finally:
            await self.session.close()
