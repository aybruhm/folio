from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from domain.ports.outbound.repositories import ITokenRepository
from infrastructure.db.models import RefreshTokenModel


class RefreshTokenRepository(ITokenRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, user_id: UUID, token: str, family_id: UUID, expires_at: datetime
    ) -> None:
        model = RefreshTokenModel(
            id=uuid4(),
            user_id=user_id,
            token=token,
            family_id=family_id,
            is_revoked=False,
            expires_at=expires_at,
            created_at=datetime.now(),
        )
        self.session.add(model)
        await self.session.flush()

    async def get_by_token(self, token: str) -> Optional[dict]:
        result = await self.session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token == token)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        expires_at = model.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace()
        return {
            "id": model.id,
            "user_id": model.user_id,
            "token": model.token,
            "family_id": model.family_id,
            "is_revoked": model.is_revoked,
            "expires_at": expires_at,
        }

    async def revoke(self, token: str) -> None:
        result = await self.session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token == token)
        )
        model = result.scalar_one_or_none()
        if model:
            model.is_revoked = True
            await self.session.flush()

    async def revoke_family(self, family_id: UUID) -> None:
        result = await self.session.execute(
            select(RefreshTokenModel).where(
                RefreshTokenModel.family_id == family_id,
                RefreshTokenModel.is_revoked == False,
            )
        )
        for model in result.scalars().all():
            model.is_revoked = True
        await self.session.flush()
