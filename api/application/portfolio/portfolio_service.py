from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from application.portfolio.portfolio_interactor import PortfolioInteractor
from domain.ports.inbound.use_cases import CreatePortfolioRequest


class PortfolioUnitOfWork(Protocol):
    interactor: PortfolioInteractor

    async def __aenter__(self) -> "PortfolioUnitOfWork": ...

    async def __aexit__(self, exc_type, exc_value, traceback) -> None: ...


class PortfolioService:
    def __init__(
        self,
        unit_of_work_factory: Callable[[], PortfolioUnitOfWork],
    ):
        self.unit_of_work_factory = unit_of_work_factory

    async def list(self, user_id: UUID, include_archived: bool = False) -> list[dict]:
        async with self.unit_of_work_factory() as unit_of_work:
            return await unit_of_work.interactor.list_portfolios(
                user_id, include_archived
            )

    async def get(self, portfolio_id: UUID) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            return await unit_of_work.interactor.get_portfolio(portfolio_id)

    async def create(self, request: CreatePortfolioRequest, user_id: UUID) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            portfolio_id = await unit_of_work.interactor.create_portfolio(
                request, user_id
            )
            return await unit_of_work.interactor.get_portfolio(portfolio_id)

    async def update(
        self,
        portfolio_id: UUID,
        name: str | None = None,
        description: str | None = None,
    ) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            await unit_of_work.interactor.update_portfolio(
                portfolio_id, name, description
            )
            return await unit_of_work.interactor.get_portfolio(portfolio_id)

    async def delete(self, portfolio_id: UUID) -> None:
        async with self.unit_of_work_factory() as unit_of_work:
            await unit_of_work.interactor.delete_portfolio(portfolio_id)

    async def set_archived(self, portfolio_id: UUID, archived: bool) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            await unit_of_work.interactor.set_archived(portfolio_id, archived)
            return await unit_of_work.interactor.get_portfolio(portfolio_id)
