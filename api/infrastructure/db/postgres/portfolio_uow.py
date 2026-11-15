from application.portfolio.portfolio_interactor import PortfolioInteractor
from infrastructure.db.postgres.portfolios.dao import PortfolioRepository
from infrastructure.db.postgres.engine import async_session


class PortfolioUnitOfWork:
    async def __aenter__(self):
        self.session = async_session()
        self.interactor = PortfolioInteractor(PortfolioRepository(self.session))
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type:
                await self.session.rollback()
            else:
                await self.session.commit()
        finally:
            await self.session.close()
