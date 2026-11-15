import re
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from domain.entities.models import Portfolio
from domain.ports.outbound.repositories import IPortfolioRepository
from domain.value_objects.money import Currency
from infrastructure.db.models import PortfolioModel

_DIGITS = re.compile(r"(\d+)")


def natural_name_key(name: str) -> tuple:
    """Sort key: case-insensitive, with runs of digits compared as numbers, so
    "2 - Savings" comes before "10 - Crypto" and "01 - A" before "02 - B".
    Done here rather than in SQL so the order doesn't depend on the database's
    locale. Digits sort before letters."""
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in _DIGITS.split(name.casefold())
        if part
    )


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
            archived_at=portfolio.archived_at,
        )
        self.session.add(model)
        await self.session.flush()

    async def get_by_id(self, portfolio_id: UUID) -> Portfolio | None:
        result = await self.session.execute(
            select(PortfolioModel).where(PortfolioModel.id == portfolio_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._to_domain(model)

    async def list_by_user(
        self, user_id: UUID, include_archived: bool = False
    ) -> list[Portfolio]:
        query = select(PortfolioModel).where(PortfolioModel.user_id == user_id)
        if not include_archived:
            query = query.where(PortfolioModel.archived_at.is_(None))
        # Oldest first, so the stable sort below keeps equal names in that order.
        result = await self.session.execute(query.order_by(PortfolioModel.created_at))
        portfolios = [self._to_domain(m) for m in result.scalars().all()]
        return sorted(portfolios, key=lambda p: natural_name_key(p.name))

    async def list_all(self) -> list[Portfolio]:
        result = await self.session.execute(select(PortfolioModel))
        return [self._to_domain(m) for m in result.scalars().all()]

    async def update(self, portfolio: Portfolio) -> None:
        model = await self.session.get(PortfolioModel, portfolio.id)
        if model:
            model.name = portfolio.name
            model.description = portfolio.description
            model.updated_at = portfolio.updated_at
            model.archived_at = portfolio.archived_at
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
            archived_at=model.archived_at,
        )
