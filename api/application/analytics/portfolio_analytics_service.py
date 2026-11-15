from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
import re
from typing import Protocol
from uuid import UUID

from application.analytics.benchmark import (
    PERIODS,
    annualized,
    chain_returns,
    effective_start,
    normalize_currency,
    price_return_series,
    sample_dates,
)
from application.analytics.benchmarks import (
    benchmark_currency,
    benchmark_name,
    benchmark_provider,
)
from application.analytics.analytics_interactor import AnalyticsInteractor
from application.analytics.portfolio_analytics import (
    build_portfolio_analytics,
    fetch_fx_factor,
    fetch_fx_factor_history,
    portfolio_analytics_with_inputs,
)
from application.analytics.summary import (
    convert_analytics,
    make_factor_lookup,
    merge_analytics,
    scale_analytics,
)
from application.portfolio.portfolio_interactor import PortfolioInteractor
from domain.value_objects.money import Currency


class BenchmarkError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class PortfolioAnalyticsUnitOfWork(Protocol):
    session: object
    portfolio_interactor: PortfolioInteractor

    def analytics_interactor(self, currency: Currency) -> AnalyticsInteractor: ...

    async def __aenter__(self) -> "PortfolioAnalyticsUnitOfWork": ...

    async def __aexit__(self, exc_type, exc_value, traceback) -> None: ...


class PortfolioAnalyticsService:
    def __init__(
        self,
        unit_of_work_factory: Callable[[], PortfolioAnalyticsUnitOfWork],
        benchmark_gateway=None,
    ):
        self.unit_of_work_factory = unit_of_work_factory
        self.benchmark_gateway = benchmark_gateway

    async def get_portfolio_analytics(
        self, portfolio_id: UUID, timeframe: str, user_id: UUID
    ) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            portfolio = await self._owned_portfolio(unit_of_work, portfolio_id, user_id)
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

    async def list_analytics(
        self,
        user_id: UUID,
        timeframe: str,
        in_currency: Currency | None,
        include_archived: bool,
    ) -> list[dict]:
        async with self.unit_of_work_factory() as unit_of_work:
            portfolios = await unit_of_work.portfolio_interactor.list_portfolios(
                user_id, include_archived
            )
            analytics = []
            for portfolio in portfolios:
                base_currency = Currency(portfolio.get("base_currency", "USD"))
                item = await build_portfolio_analytics(
                    unit_of_work.session,
                    UUID(portfolio["id"]),
                    timeframe,
                    base_currency,
                    lambda _, currency: unit_of_work.analytics_interactor(currency),
                )
                if in_currency and base_currency != in_currency:
                    factor = await fetch_fx_factor(
                        base_currency.value, in_currency.value
                    )
                    if factor and factor != 1:
                        scale_analytics(item, factor)
                analytics.append(item)
            return analytics

    async def get_summary(
        self, user_id: UUID, timeframe: str, display_currency: Currency
    ) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            portfolios = await unit_of_work.portfolio_interactor.list_portfolios(
                user_id
            )
            items = []
            excluded = []
            for portfolio in portfolios:
                base_currency = Currency(portfolio.get("base_currency", "USD"))
                analytics, inputs = await portfolio_analytics_with_inputs(
                    unit_of_work.session,
                    UUID(portfolio["id"]),
                    timeframe,
                    base_currency,
                    lambda _, currency: unit_of_work.analytics_interactor(currency),
                )
                if base_currency != display_currency:
                    factor = await fetch_fx_factor(
                        base_currency.value, display_currency.value
                    )
                    if not factor:
                        excluded.append(portfolio["id"])
                        continue
                    factor_on = None
                    if inputs:
                        factor_on = make_factor_lookup(
                            await fetch_fx_factor_history(
                                base_currency.value,
                                display_currency.value,
                                inputs.start_date - timedelta(days=7),
                                date.today(),
                            )
                        )
                    inputs = convert_analytics(analytics, inputs, factor, factor_on)
                items.append((analytics, inputs))
            summary = merge_analytics(items, display_currency.value, timeframe)
            summary["excluded_portfolio_ids"] = excluded
            return summary

    async def get_benchmark_comparison(
        self,
        benchmark: str,
        period: str,
        in_currency: str,
        portfolio_id: UUID | None,
        provider: str | None,
        user_id: UUID,
    ) -> tuple[dict, str]:
        symbol = benchmark.strip().upper()
        if not re.fullmatch(r"[A-Z0-9^.=:\-]{1,24}", symbol):
            raise BenchmarkError(422, "Invalid benchmark ticker")
        period_key = period.strip().lower()
        if period_key not in PERIODS:
            raise BenchmarkError(422, f"period must be one of: {', '.join(PERIODS)}")
        try:
            display_currency = Currency(in_currency)
        except ValueError:
            raise BenchmarkError(422, "Unknown currency")

        gateway = self.benchmark_gateway
        source = (provider or benchmark_provider(symbol)).strip().lower()
        if source not in gateway.providers:
            raise BenchmarkError(
                422,
                f"provider must be one of: {', '.join(gateway.providers)}",
            )
        adapter = gateway.build_adapter(source)
        if not gateway.is_configured(adapter):
            raise BenchmarkError(
                503,
                f"{gateway.provider_labels[source]} isn't set up on this server, "
                f"so {symbol} can't be loaded.",
            )

        async with self.unit_of_work_factory() as unit_of_work:
            if portfolio_id:
                try:
                    portfolio = await unit_of_work.portfolio_interactor.get_portfolio(
                        portfolio_id
                    )
                except ValueError:
                    raise BenchmarkError(404, "Portfolio not found")
                if portfolio.get("user_id") != str(user_id):
                    raise BenchmarkError(403, "Access denied")
                portfolios = [portfolio]
            else:
                portfolios = await unit_of_work.portfolio_interactor.list_portfolios(
                    user_id
                )
            if not portfolios:
                raise BenchmarkError(404, "No portfolios to benchmark")

            today = date.today()
            cache = gateway.cache
            cache_key = await cache.key(
                str(user_id),
                str(portfolio_id) if portfolio_id else "all",
                symbol,
                source,
                period_key,
                display_currency.value,
                today.isoformat(),
            )
            cached = await cache.get(cache_key)
            if cached is not None:
                return cached, "HIT"

            period_start = self._timeframe_start(period_key, today)
            history = await adapter.get_price_history(
                symbol, period_start - timedelta(days=14), today
            )
            closes = sorted((d, price / 100) for d, price in history if price > 0)
            if not closes:
                detail = (
                    f"No price history found for {symbol} on "
                    f"{gateway.provider_labels[source]}"
                )
                if source != "yfinance":
                    detail += ". Check the index code and that the server's API key for it is valid."
                raise BenchmarkError(404, detail)

            interactors = {}
            first_trades = []
            for portfolio in portfolios:
                interactor = unit_of_work.analytics_interactor(
                    Currency(portfolio["base_currency"])
                )
                interactors[portfolio["id"]] = interactor
                first = await interactor.get_first_trade_date(UUID(portfolio["id"]))
                if first:
                    first_trades.append(first)
            if not first_trades:
                raise BenchmarkError(404, "No trades to benchmark yet")

            start, limited_by = effective_start(
                period_start, min(first_trades), closes[0][0]
            )
            if (today - start).days < 7:
                raise BenchmarkError(
                    422,
                    "Not enough history to compare yet: at least a week is needed.",
                )
            dates = sample_dates(start, today)
            totals = [0.0] * len(dates)
            flows = []
            excluded = []
            used = 0
            for portfolio in portfolios:
                series = await interactors[portfolio["id"]].get_value_series(
                    UUID(portfolio["id"]), dates
                )
                if series is None:
                    continue
                factor_on = await self._dated_factor(
                    Currency(portfolio["base_currency"]),
                    display_currency,
                    start,
                    today,
                )
                if factor_on is None:
                    excluded.append(portfolio["id"])
                    continue
                values, portfolio_flows = series
                for index, (day, value) in enumerate(zip(dates, values)):
                    totals[index] += value * factor_on(day)
                flows += [
                    (day, amount * factor_on(day)) for day, amount in portfolio_flows
                ]
                used += 1
            if not used:
                raise BenchmarkError(
                    422,
                    f"Exchange rates to {display_currency.value} are unavailable right now.",
                )

            quote_currency = normalize_currency(
                await adapter.get_quote_currency(symbol)
                if source == "yfinance"
                else benchmark_currency(symbol)
                or gateway.provider_currencies.get(source)
            )
            converted = False
            if quote_currency and quote_currency != display_currency.value:
                try:
                    benchmark_factor = await self._dated_factor(
                        Currency(quote_currency), display_currency, start, today
                    )
                except ValueError:
                    benchmark_factor = None
                if benchmark_factor:
                    closes = [
                        (day, price * benchmark_factor(day)) for day, price in closes
                    ]
                    converted = True

            portfolio_cumulative = chain_returns(dates, totals, flows)
            benchmark_cumulative = price_return_series(closes, dates)
            if not benchmark_cumulative:
                raise BenchmarkError(404, f"No usable prices for {symbol}")

            days = (today - start).days
            portfolio_return = portfolio_cumulative[-1]
            benchmark_return = benchmark_cumulative[-1]

            def pct(fraction):
                return None if fraction is None else round(fraction * 100, 2)

            payload = {
                "generated_at": datetime.now(UTC).isoformat(),
                "period": period_key,
                "currency": display_currency.value,
                "requested_start": period_start.isoformat(),
                "start_date": start.isoformat(),
                "end_date": today.isoformat(),
                "limited_by": limited_by,
                "portfolio_count": used,
                "excluded_portfolio_ids": excluded,
                "portfolio": {
                    "return_pct": pct(portfolio_return),
                    "annualized_pct": pct(annualized(portfolio_return, days)),
                },
                "benchmark": {
                    "ticker": symbol,
                    "provider": source,
                    "name": benchmark_name(symbol),
                    "quote_currency": quote_currency,
                    "converted": converted
                    or quote_currency in (None, display_currency.value),
                    "return_pct": pct(benchmark_return),
                    "annualized_pct": pct(annualized(benchmark_return, days)),
                },
                "excess_return_pct": pct(portfolio_return - benchmark_return),
                "series": [
                    {
                        "date": day.isoformat(),
                        "portfolio": pct(portfolio_value),
                        "benchmark": pct(benchmark_value),
                    }
                    for day, portfolio_value, benchmark_value in zip(
                        dates, portfolio_cumulative, benchmark_cumulative
                    )
                ],
            }
            await cache.set(cache_key, payload)
            return payload, "MISS"

    @staticmethod
    def _timeframe_start(period: str, today: date) -> date:
        from application.analytics.timeframe import timeframe_start

        return timeframe_start(period, today) or today

    @staticmethod
    async def _dated_factor(
        from_currency: Currency,
        to_currency: Currency,
        start: date,
        end: date,
    ):
        if from_currency == to_currency:
            return lambda _day: 1.0
        current = await fetch_fx_factor(from_currency.value, to_currency.value)
        if not current:
            return None
        lookup = make_factor_lookup(
            await fetch_fx_factor_history(
                from_currency.value,
                to_currency.value,
                start - timedelta(days=7),
                end,
            )
        )
        return lookup or (lambda _day: current)

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
