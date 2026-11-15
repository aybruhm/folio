from infrastructure.db.postgres.assets.dao import AssetRepository
from infrastructure.db.postgres.engine import async_session


class AssetUnitOfWork:
    async def __aenter__(self):
        self.session = async_session()
        self.repository = AssetRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type:
                await self.session.rollback()
            else:
                await self.session.commit()
        finally:
            await self.session.close()
