import asyncio
from collections.abc import Callable
from datetime import date
from typing import Protocol
from uuid import UUID

from application.trades.trade_interactor import TradeInteractor
from application.portfolio.portfolio_interactor import PortfolioInteractor
from domain.ports.inbound.use_cases import CreateTradeRequest
from domain.value_objects.money import TradeType


class TradeUnitOfWork(Protocol):
    interactor: TradeInteractor
    portfolio_interactor: PortfolioInteractor

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

    async def ensure_portfolio_access(self, portfolio_id: UUID, user_id: UUID) -> None:
        async with self.unit_of_work_factory() as unit_of_work:
            portfolio = await unit_of_work.portfolio_interactor.get_portfolio(
                portfolio_id
            )
            if portfolio.get("user_id") != str(user_id):
                raise PermissionError("Access denied")

    async def create_bulk(self, requests: list[tuple[int, CreateTradeRequest]]) -> dict:
        async def create_one(index: int, request: CreateTradeRequest):
            try:
                async with self.unit_of_work_factory() as unit_of_work:
                    trade_id = await unit_of_work.interactor.create_trade(request)
                    trade = await unit_of_work.interactor.get_trade(trade_id)
                    return index, trade, None
            except Exception as error:
                return index, None, str(error)

        results = await asyncio.gather(
            *(create_one(index, request) for index, request in requests)
        )
        trades = [trade for _, trade, error in results if error is None]
        errors = [
            {"index": index, "message": error}
            for index, _, error in results
            if error is not None
        ]
        return {"trades": trades, "errors": errors}
