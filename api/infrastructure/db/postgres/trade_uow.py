from application.trades.trade_interactor import TradeInteractor
from application.portfolio.portfolio_interactor import PortfolioInteractor
from infrastructure.db.postgres.engine import async_session
from infrastructure.db.postgres.assets.dao import AssetRepository
from infrastructure.db.postgres.portfolios.dao import PortfolioRepository
from infrastructure.db.postgres.trades.dao import TradeRepository
from infrastructure.market_data.trade_gateway import TradeMarketDataGateway


class TradeUnitOfWork:
    async def __aenter__(self):
        self.session = async_session()
        self.interactor = TradeInteractor(
            TradeRepository(self.session),
            AssetRepository(self.session),
            PortfolioRepository(self.session),
            TradeMarketDataGateway(),
        )
        self.portfolio_interactor = PortfolioInteractor(
            PortfolioRepository(self.session)
        )
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type:
                await self.session.rollback()
            else:
                await self.session.commit()
        finally:
            await self.session.close()
