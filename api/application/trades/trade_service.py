from collections.abc import Callable
from datetime import date
from typing import Protocol
from uuid import UUID

from application.trades.trade_interactor import TradeInteractor
from domain.ports.inbound.use_cases import CreateTradeRequest
from domain.value_objects.money import TradeType


class TradeUnitOfWork(Protocol):
    interactor: TradeInteractor

    async def __aenter__(self) -> "TradeUnitOfWork": ...

    async def __aexit__(self, exc_type, exc_value, traceback) -> None: ...


class TradeService:
    def __init__(self, unit_of_work_factory: Callable[[], TradeUnitOfWork]):
        self.unit_of_work_factory = unit_of_work_factory

    async def list_trades(
        self,
        portfolio_id: UUID,
        ticker: str | None = None,
        trade_type: TradeType | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[dict], int]:
        async with self.unit_of_work_factory() as unit_of_work:
            return await unit_of_work.interactor.list_trades(
                portfolio_id, ticker, trade_type, start_date, end_date, skip, limit
            )

    async def create(self, request: CreateTradeRequest) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            trade_id = await unit_of_work.interactor.create_trade(request)
            return await unit_of_work.interactor.get_trade(trade_id)

    async def get(self, trade_id: UUID) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            return await unit_of_work.interactor.get_trade(trade_id)

    async def update(self, trade_id: UUID, request: CreateTradeRequest) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            await unit_of_work.interactor.update_trade(trade_id, request)
            return await unit_of_work.interactor.get_trade(trade_id)

    async def delete(self, trade_id: UUID) -> None:
        async with self.unit_of_work_factory() as unit_of_work:
            await unit_of_work.interactor.delete_trade(trade_id)

    async def delete_batch(self, trade_ids: list[UUID]) -> None:
        async with self.unit_of_work_factory() as unit_of_work:
            await unit_of_work.interactor.delete_batch_trades(trade_ids)
