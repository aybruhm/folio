from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from application.analytics.analytics_interactor import AnalyticsInteractor
from application.analytics.portfolio_analytics import build_portfolio_analytics
from application.portfolio.portfolio_interactor import PortfolioInteractor
from domain.value_objects.money import Currency


class PortfolioAnalyticsUnitOfWork(Protocol):
    session: object
    portfolio_interactor: PortfolioInteractor

    def analytics_interactor(self, currency: Currency) -> AnalyticsInteractor: ...

    async def __aenter__(self) -> "PortfolioAnalyticsUnitOfWork": ...

    async def __aexit__(self, exc_type, exc_value, traceback) -> None: ...


class PortfolioAnalyticsService:
    def __init__(
        self, unit_of_work_factory: Callable[[], PortfolioAnalyticsUnitOfWork]
    ):
        self.unit_of_work_factory = unit_of_work_factory

    async def get_portfolio_analytics(
        self, portfolio_id: UUID, timeframe: str, user_id: UUID
    ) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            portfolio = await self._owned_portfolio(
                unit_of_work, portfolio_id, user_id
            )
            base_currency = Currency(portfolio.get("base_currency", "USD"))
            return await build_portfolio_analytics(
                unit_of_work.session,
                portfolio_id,
                timeframe,
                base_currency,
                lambda _, currency: unit_of_work.analytics_interactor(currency),
            )

    async def get_holdings(
        self, portfolio_id: UUID, user_id: UUID, in_currency: Currency | None = None
    ) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            base_currency = Currency(
                (await self._owned_portfolio(unit_of_work, portfolio_id, user_id)).get(
                    "base_currency", "USD"
                )
            )
            currency = in_currency or base_currency
            holdings = await unit_of_work.analytics_interactor(
                base_currency
            ).get_holdings(portfolio_id, currency)

            data = [
                {
                    "ticker": h["ticker"],
                    "name": h.get("name", h["ticker"]),
                    "quantity": h["quantity"],
                    "avg_price": (
                        float(h["cost_basis"]) / float(h["quantity"])
                        if float(h["quantity"]) > 0
                        else 0.0
                    ),
                    "current_price": h["current_price"],
                    "total_value": h["market_value"],
                    "total_invested": h["total_invested"],
                    "gain_loss": h["total_return"],
                    "gain_loss_percent": h["total_return_percent"],
                }
                for h in holdings
            ]
            total_value = sum(float(h["market_value"]) for h in holdings)
            total_invested = sum(float(h["total_invested"]) for h in holdings)
            return {
                "data": data,
                "currency": currency.value,
                "total_value": float(total_value),
                "total_invested": float(total_invested),
            }

    async def get_performance(self, portfolio_id: UUID, user_id: UUID) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            await self._owned_portfolio(unit_of_work, portfolio_id, user_id)
            performance = await unit_of_work.analytics_interactor(
                Currency.USD
            ).calculate_performance(portfolio_id)
            return {
                "portfolio_id": str(portfolio_id),
                "returns": float(performance.get("twr", 0)),
                "returns_percent": float(performance.get("twr", 0)),
                "start_date": performance.get("start_date", ""),
                "end_date": performance.get("end_date", ""),
                "data_points": [],
            }

    async def get_allocation(
        self, portfolio_id: UUID, user_id: UUID, group_by: str
    ) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            await self._owned_portfolio(unit_of_work, portfolio_id, user_id)
            allocation = await unit_of_work.analytics_interactor(
                Currency.USD
            ).get_allocation(portfolio_id, group_by)
            return {
                "portfolio_id": str(portfolio_id),
                "allocations": [
                    {
                        "category": item["name"],
                        "value": item["value"],
                        "percent": item.get("weight_percent", 0),
                        "holdings": item.get("holdings", []),
                    }
                    for item in allocation
                ],
                "group_by": group_by,
            }

    @staticmethod
    async def _owned_portfolio(
        unit_of_work: PortfolioAnalyticsUnitOfWork,
        portfolio_id: UUID,
        user_id: UUID,
    ) -> dict:
        portfolio = await unit_of_work.portfolio_interactor.get_portfolio(portfolio_id)
        if portfolio.get("user_id") != str(user_id):
            raise PermissionError("Access denied")
        return portfolio
