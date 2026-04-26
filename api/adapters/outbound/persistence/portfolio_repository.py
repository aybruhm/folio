from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List, Optional

from domain.entities.models import Portfolio
from domain.value_objects.money import Currency
from domain.ports.outbound.repositories import IPortfolioRepository
from infrastructure.db.models import PortfolioModel


class PortfolioRepository(IPortfolioRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, portfolio: Portfolio) -> None:
        model = PortfolioModel(
            id=portfolio.id,
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

        return Portfolio(
            id=model.id,
            name=model.name,
            base_currency=Currency(model.base_currency),
            description=model.description,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def list_all(self) -> List[Portfolio]:
        result = await self.session.execute(select(PortfolioModel))
        models = result.scalars().all()

        return [
            Portfolio(
                id=m.id,
                name=m.name,
                base_currency=Currency(m.base_currency),
                description=m.description,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in models
        ]

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
