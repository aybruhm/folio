from application.trades.trade_interactor import TradeInteractor
from application.portfolio.portfolio_interactor import PortfolioInteractor
from infrastructure.db.postgres.engine import async_session


class TradeUnitOfWork:
    async def __aenter__(self):
        self.session = async_session()
        self.interactor = TradeInteractor(self.session)
        self.portfolio_interactor = PortfolioInteractor(self.session)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type:
                await self.session.rollback()
            else:
                await self.session.commit()
        finally:
            await self.session.close()
