from application.trades.trade_interactor import TradeInteractor
from infrastructure.db.postgres.engine import async_session


class TradeUnitOfWork:
    async def __aenter__(self):
        self.session = async_session()
        self.interactor = TradeInteractor(self.session)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type:
                await self.session.rollback()
            else:
                await self.session.commit()
        finally:
            await self.session.close()
