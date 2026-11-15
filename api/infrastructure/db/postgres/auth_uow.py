from infrastructure.db.postgres.engine import async_session
from infrastructure.db.postgres.tokens.dao import RefreshTokenRepository
from infrastructure.db.postgres.users.dao import UserRepository


class AuthUnitOfWork:
    async def __aenter__(self):
        self.session = async_session()
        self.user_repo = UserRepository(self.session)
        self.token_repo = RefreshTokenRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type:
                await self.session.rollback()
            else:
                await self.session.commit()
        finally:
            await self.session.close()
