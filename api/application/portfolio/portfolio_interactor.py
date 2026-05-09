from uuid import UUID, uuid4
from typing import List, Optional
from datetime import datetime

from domain.entities.models import Portfolio
from domain.value_objects.money import Currency
from domain.ports.inbound.use_cases import IPortfolioUseCase, CreatePortfolioRequest
from domain.ports.outbound.repositories import IPortfolioRepository
from adapters.outbound.persistence.portfolio_repository import PortfolioRepository
from sqlalchemy.ext.asyncio import AsyncSession


class PortfolioInteractor(IPortfolioUseCase):
    def __init__(self, session: AsyncSession):
        self.repository: IPortfolioRepository = PortfolioRepository(session)

    async def create_portfolio(
        self, request: CreatePortfolioRequest, user_id: UUID
    ) -> UUID:
        portfolio = Portfolio(
            id=uuid4(),
            user_id=user_id,
            name=request.name,
            base_currency=request.base_currency,
            description=request.description,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        await self.repository.add(portfolio)
        return portfolio.id

    async def get_portfolio(self, portfolio_id: UUID) -> dict:
        portfolio = await self.repository.get_by_id(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        return {
            "id": str(portfolio.id),
            "user_id": str(portfolio.user_id),
            "name": portfolio.name,
            "base_currency": portfolio.base_currency.value,
            "description": portfolio.description,
            "created_at": portfolio.created_at.isoformat(),
            "updated_at": portfolio.updated_at.isoformat(),
        }

    async def list_portfolios(self, user_id: UUID) -> List[dict]:
        portfolios = await self.repository.list_by_user(user_id)
        return [
            {
                "id": str(p.id),
                "user_id": str(p.user_id),
                "name": p.name,
                "base_currency": p.base_currency.value,
                "description": p.description,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
            }
            for p in portfolios
        ]

    async def update_portfolio(
        self,
        portfolio_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        portfolio = await self.repository.get_by_id(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        if name:
            portfolio.name = name
        if description is not None:
            portfolio.description = description

        portfolio.updated_at = datetime.now()
        await self.repository.update(portfolio)

    async def delete_portfolio(self, portfolio_id: UUID) -> None:
        portfolio = await self.repository.get_by_id(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        await self.repository.delete(portfolio_id)
