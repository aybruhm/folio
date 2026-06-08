from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from domain.entities.models import Portfolio
from domain.ports.outbound.repositories import IPortfolioRepository
from domain.value_objects.money import Currency
from infrastructure.db.models import PortfolioModel


class PortfolioRepository(IPortfolioRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, portfolio: Portfolio) -> None:
        model = PortfolioModel(
            id=portfolio.id,
            user_id=portfolio.user_id,
            name=portfolio.name,
            base_currency=portfolio.base_currency.value,
            description=portfolio.description,
            created_at=portfolio.created_at,
            updated_at=portfolio.updated_at,
        )
        self.session.add(model)
        await self.session.flush()

    async def get_by_id(self, portfolio_id: UUID) -> Optional[Portfolio]:
        result = await self.session.execute(
            select(PortfolioModel).where(PortfolioModel.id == portfolio_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._to_domain(model)

    async def list_by_user(self, user_id: UUID) -> List[Portfolio]:
        result = await self.session.execute(
            select(PortfolioModel).where(PortfolioModel.user_id == user_id)
        )
        return [self._to_domain(m) for m in result.scalars().all()]

    async def list_all(self) -> List[Portfolio]:
        result = await self.session.execute(select(PortfolioModel))
        return [self._to_domain(m) for m in result.scalars().all()]

    async def update(self, portfolio: Portfolio) -> None:
        model = await self.session.get(PortfolioModel, portfolio.id)
        if model:
            model.name = portfolio.name
            model.description = portfolio.description
            model.updated_at = portfolio.updated_at
            await self.session.flush()

    async def delete(self, portfolio_id: UUID) -> None:
        model = await self.session.get(PortfolioModel, portfolio_id)
        if model:
            await self.session.delete(model)
            await self.session.flush()

    def _to_domain(self, model: PortfolioModel) -> Portfolio:
        return Portfolio(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            base_currency=Currency(model.base_currency),
            description=model.description,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
