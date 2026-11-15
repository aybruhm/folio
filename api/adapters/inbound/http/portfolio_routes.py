import asyncio
import re
from collections.abc import Callable, Coroutine
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.inbound.http.dependencies import (
    get_portfolio_analytics_service,
    get_portfolio_service,
    get_current_user,
    invalidate_benchmark_cache,
)
from infrastructure.market_data.benchmark_cache import BenchmarkCache
from infrastructure.market_data.providers import (
    BENCHMARK_PROVIDERS,
    PROVIDER_CURRENCY,
    PROVIDER_LABELS,
    build_adapter,
    is_configured,
)
from application.analytics.analytics_interactor import AnalyticsInteractor
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
from application.analytics.summary import (
    convert_analytics,
    make_factor_lookup,
    merge_analytics,
    scale_analytics,
)
from application.analytics.portfolio_analytics import (
    build_portfolio_analytics,
    dated_factor,
    fetch_fx_factor,
    fetch_fx_factor_history,
    portfolio_analytics_with_inputs,
)
from application.analytics.portfolio_analytics_service import PortfolioAnalyticsService
from application.analytics.timeframe import timeframe_start
from application.portfolio.portfolio_interactor import PortfolioInteractor
from application.portfolio.portfolio_service import PortfolioService
from domain.entities.models import User
from domain.ports.inbound.use_cases import CreatePortfolioRequest
from domain.services.performance import PerformanceInputs
from domain.value_objects.money import Currency
from infrastructure.db.postgres.engine import get_session

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


async def _fetch_fx_factor(from_ccy: str, to_ccy: str) -> float:
    return await fetch_fx_factor(from_ccy, to_ccy)


async def _fetch_fx_factor_history(
    from_ccy: str, to_ccy: str, start: date, end: date
) -> list[tuple[date, float]]:
    return await fetch_fx_factor_history(from_ccy, to_ccy, start, end)


async def _dated_factor(
    from_ccy: Currency, to_ccy: Currency, start: date, end: date
) -> Callable[[date], float] | None:
    if from_ccy == to_ccy:
        return lambda _day: 1.0
    current = await _fetch_fx_factor(from_ccy.value, to_ccy.value)
    if not current:
        return None
    lookup = make_factor_lookup(
        await _fetch_fx_factor_history(
            from_ccy.value, to_ccy.value, start - timedelta(days=7), end
        )
    )
    return lookup or (lambda _day: current)


async def _build_portfolio_analytics(
    session: AsyncSession,
    portfolio_id: UUID,
    timeframe: str,
    base_currency: Currency = Currency.USD,
) -> dict:
    return await build_portfolio_analytics(
        session, portfolio_id, timeframe, base_currency, AnalyticsInteractor
    )


async def _portfolio_analytics_with_inputs(
    session: AsyncSession,
    portfolio_id: UUID,
    timeframe: str,
    base_currency: Currency = Currency.USD,
) -> tuple[dict, PerformanceInputs | None]:
    return await portfolio_analytics_with_inputs(
        session, portfolio_id, timeframe, base_currency, AnalyticsInteractor
    )


def _check_ownership(portfolio: dict, current_user: User) -> None:
    if portfolio.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )


@router.get("/", response_model=list[dict])
async def list_portfolios(
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    return await service.list(current_user.id, include_archived)


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    request: CreatePortfolioRequest,
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    try:
        return await service.create(request, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analytics", response_model=list[dict])
async def list_portfolio_analytics(
    timeframe: str = "1y",
    in_currency: str | None = None,
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        portfolio_interactor = PortfolioInteractor(session)
        portfolios = await portfolio_interactor.list_portfolios(
            current_user.id, include_archived
        )
        if not portfolios:
            return []

        analytics_tasks: list[Coroutine] = []
        for portfolio in portfolios:
            base_ccy = Currency(portfolio.get("base_currency", "USD"))
            analytics_tasks.append(
                _build_portfolio_analytics(
                    session, UUID(portfolio["id"]), timeframe, base_ccy
                )
            )

        analytics = await asyncio.gather(*analytics_tasks)

        # If a display currency is requested, convert monetary fields
        if in_currency:
            display_ccy = Currency(in_currency)
            for i, item in enumerate(analytics):
                portfolio_ccy = Currency(portfolios[i].get("base_currency", "USD"))
                if portfolio_ccy != display_ccy:
                    factor = await _fetch_fx_factor(
                        portfolio_ccy.value, display_ccy.value
                    )
                    if factor and factor != 1:
                        scale_analytics(item, factor)
        return list(analytics)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analytics/summary")
async def get_analytics_summary(
    timeframe: str = "1y",
    in_currency: str = "USD",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """All active portfolios merged into one analytics view in *in_currency*.

    Portfolios whose FX rate can't be fetched are left out rather than mixed
    in unconverted; their ids are listed in `excluded_portfolio_ids`.
    """
    try:
        display_ccy = Currency(in_currency)
        portfolios = await PortfolioInteractor(session).list_portfolios(current_user.id)

        items: list[tuple[dict, PerformanceInputs | None]] = []
        excluded: list[str] = []
        # Sequential: the portfolios share one AsyncSession.
        for portfolio in portfolios:
            base_ccy = Currency(portfolio.get("base_currency", "USD"))
            analytics, inputs = await _portfolio_analytics_with_inputs(
                session, UUID(portfolio["id"]), timeframe, base_ccy
            )
            if base_ccy != display_ccy:
                factor = await _fetch_fx_factor(base_ccy.value, display_ccy.value)
                if not factor:
                    excluded.append(portfolio["id"])
                    continue
                # Past values at their own date's rate; falls back to today's
                # rate when no history is available.
                factor_on = None
                if inputs:
                    factor_on = make_factor_lookup(
                        await _fetch_fx_factor_history(
                            base_ccy.value,
                            display_ccy.value,
                            inputs.start_date - timedelta(days=7),
                            date.today(),
                        )
                    )
                inputs = convert_analytics(analytics, inputs, factor, factor_on)
            items.append((analytics, inputs))

        summary = merge_analytics(items, display_ccy.value, timeframe)
        summary["excluded_portfolio_ids"] = excluded
        return summary
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


_BENCHMARK_SYMBOL = re.compile(r"^[A-Z0-9^.=:\-]{1,24}$")
_MIN_COMPARISON_DAYS = 7


@router.get("/analytics/benchmark")
async def get_benchmark_comparison(
    benchmark: str,
    response: Response,
    period: str = "1y",
    in_currency: str = "USD",
    portfolio_id: UUID | None = None,
    provider: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Cumulative return of a portfolio (or all of them) against a benchmark.

    `period` is one of ytd, 3m, 6m, 1y, 3y, 5y, 10y. Both lines are shown from
    the same day, in `in_currency`: the latest of the period start, the first
    trade and the benchmark's first price (`limited_by` says which). Money
    added or withdrawn is not counted as performance.

    `provider` says where the benchmark's prices come from (yfinance, ngxpulse
    or ngnmarket); it defaults to the catalog's choice for known tickers and
    to yfinance otherwise. Results are cached for 35 minutes.
    """
    symbol = benchmark.strip().upper()
    if not _BENCHMARK_SYMBOL.match(symbol):
        raise HTTPException(status_code=422, detail="Invalid benchmark ticker")
    period_key = period.strip().lower()
    if period_key not in PERIODS:
        raise HTTPException(
            status_code=422, detail=f"period must be one of: {', '.join(PERIODS)}"
        )
    try:
        display_ccy = Currency(in_currency)
    except ValueError:
        raise HTTPException(status_code=422, detail="Unknown currency")
    source = (provider or benchmark_provider(symbol)).strip().lower()
    if source not in BENCHMARK_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"provider must be one of: {', '.join(BENCHMARK_PROVIDERS)}",
        )
    adapter = build_adapter(source)
    if not is_configured(adapter):
        raise HTTPException(
            status_code=503,
            detail=(
                f"{PROVIDER_LABELS[source]} isn't set up on this server, so "
                f"{symbol} can't be loaded."
            ),
        )

    try:
        portfolio_interactor = PortfolioInteractor(session)
        if portfolio_id:
            try:
                portfolio = await portfolio_interactor.get_portfolio(portfolio_id)
            except ValueError:
                raise HTTPException(status_code=404, detail="Portfolio not found")
            _check_ownership(portfolio, current_user)
            portfolios = [portfolio]
        else:
            portfolios = await portfolio_interactor.list_portfolios(current_user.id)
        if not portfolios:
            raise HTTPException(status_code=404, detail="No portfolios to benchmark")

        today = date.today()
        cache = BenchmarkCache()
        cache_key = await cache.key(
            str(current_user.id),
            str(portfolio_id) if portfolio_id else "all",
            symbol,
            source,
            period_key,
            display_ccy.value,
            today.isoformat(),
        )
        cached = await cache.get(cache_key)
        if cached is not None:
            response.headers["X-Cache"] = "HIT"
            return cached
        response.headers["X-Cache"] = "MISS"

        period_start = timeframe_start(period_key, today) or today

        history = await adapter.get_price_history(
            symbol, period_start - timedelta(days=14), today
        )
        closes = sorted((d, price / 100) for d, price in history if price > 0)
        if not closes:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No price history found for {symbol} on "
                    f"{PROVIDER_LABELS[source]}"
                    + (
                        ""
                        if source == "yfinance"
                        else ". Check the index code and that the server's "
                        "API key for it is valid."
                    )
                ),
            )

        interactors: dict[str, AnalyticsInteractor] = {}
        first_trades: list[date] = []
        for p in portfolios:
            interactor = AnalyticsInteractor(session, Currency(p["base_currency"]))
            interactors[p["id"]] = interactor
            first = await interactor.get_first_trade_date(UUID(p["id"]))
            if first:
                first_trades.append(first)
        if not first_trades:
            raise HTTPException(status_code=404, detail="No trades to benchmark yet")

        start, limited_by = effective_start(
            period_start, min(first_trades), closes[0][0]
        )
        if (today - start).days < _MIN_COMPARISON_DAYS:
            raise HTTPException(
                status_code=422,
                detail="Not enough history to compare yet: at least a week is needed.",
            )
        dates = sample_dates(start, today)

        totals = [0.0] * len(dates)
        flows: list[tuple[date, float]] = []
        excluded: list[str] = []
        used = 0
        for p in portfolios:
            series = await interactors[p["id"]].get_value_series(UUID(p["id"]), dates)
            if series is None:
                continue
            factor_on = await _dated_factor(
                Currency(p["base_currency"]), display_ccy, start, today
            )
            if factor_on is None:
                excluded.append(p["id"])
                continue
            values, portfolio_flows = series
            for i, (day, value) in enumerate(zip(dates, values)):
                totals[i] += value * factor_on(day)
            flows += [(day, amount * factor_on(day)) for day, amount in portfolio_flows]
            used += 1
        if not used:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Exchange rates to {display_ccy.value} are unavailable "
                    "right now."
                ),
            )

        # The benchmark in the same currency, at each day's rate, so a falling
        # local currency doesn't flatter or hide the comparison.
        quote_ccy = normalize_currency(
            await adapter.get_quote_currency(symbol)
            if source == "yfinance"
            else benchmark_currency(symbol) or PROVIDER_CURRENCY.get(source)
        )
        converted = False
        if quote_ccy and quote_ccy != display_ccy.value:
            try:
                bench_factor = await _dated_factor(
                    Currency(quote_ccy), display_ccy, start, today
                )
            except ValueError:
                bench_factor = None
            if bench_factor:
                closes = [(d, price * bench_factor(d)) for d, price in closes]
                converted = True

        portfolio_cumulative = chain_returns(dates, totals, flows)
        benchmark_cumulative = price_return_series(closes, dates)
        if not benchmark_cumulative:
            raise HTTPException(
                status_code=404, detail=f"No usable prices for {symbol}"
            )

        days = (today - start).days
        portfolio_return = portfolio_cumulative[-1]
        benchmark_return = benchmark_cumulative[-1]

        def pct(fraction: float | None) -> float | None:
            return None if fraction is None else round(fraction * 100, 2)

        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "period": period_key,
            "currency": display_ccy.value,
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
                "quote_currency": quote_ccy,
                # False when the benchmark is quoted in another currency and no
                # rate was available, so its return is in its own currency.
                "converted": converted or quote_ccy in (None, display_ccy.value),
                "return_pct": pct(benchmark_return),
                "annualized_pct": pct(annualized(benchmark_return, days)),
            },
            "excess_return_pct": pct(portfolio_return - benchmark_return),
            "series": [
                {
                    "date": day.isoformat(),
                    "portfolio": pct(p_value),
                    "benchmark": pct(b_value),
                }
                for day, p_value, b_value in zip(
                    dates, portfolio_cumulative, benchmark_cumulative
                )
            ],
        }
        await cache.set(cache_key, payload)
        return payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{portfolio_id}", response_model=dict)
async def get_portfolio(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    try:
        portfolio = await service.get(portfolio_id)
        _check_ownership(portfolio, current_user)
        return portfolio
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{portfolio_id}", dependencies=[Depends(invalidate_benchmark_cache)])
async def update_portfolio(
    portfolio_id: UUID,
    name: str | None = None,
    description: str | None = None,
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    try:
        portfolio = await service.get(portfolio_id)
        _check_ownership(portfolio, current_user)

        return await service.update(portfolio_id, name, description)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(invalidate_benchmark_cache)])
async def delete_portfolio(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    try:
        portfolio = await service.get(portfolio_id)
        _check_ownership(portfolio, current_user)

        await service.delete(portfolio_id)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def _set_archived(
    portfolio_id: UUID,
    archived: bool,
    current_user: User,
    service: PortfolioService,
) -> dict:
    try:
        portfolio = await service.get(portfolio_id)
        _check_ownership(portfolio, current_user)

        return await service.set_archived(portfolio_id, archived)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{portfolio_id}/archive", dependencies=[Depends(invalidate_benchmark_cache)])
async def archive_portfolio(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    return await _set_archived(portfolio_id, True, current_user, service)


@router.post("/{portfolio_id}/unarchive", dependencies=[Depends(invalidate_benchmark_cache)])
async def unarchive_portfolio(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    return await _set_archived(portfolio_id, False, current_user, service)


@router.get("/{portfolio_id}/analytics")
async def get_portfolio_analytics(
    portfolio_id: UUID,
    timeframe: str = "1y",
    current_user: User = Depends(get_current_user),
    service: PortfolioAnalyticsService = Depends(get_portfolio_analytics_service),
):

    try:
        return await service.get_portfolio_analytics(
            portfolio_id, timeframe, current_user.id
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{portfolio_id}/holdings")
async def get_holdings(
    portfolio_id: UUID,
    in_currency: str | None = None,
    current_user: User = Depends(get_current_user),
    service: PortfolioAnalyticsService = Depends(get_portfolio_analytics_service),
):

    try:
        currency = Currency(in_currency) if in_currency else None
        return await service.get_holdings(portfolio_id, current_user.id, currency)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{portfolio_id}/performance")
async def get_performance(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user),
    service: PortfolioAnalyticsService = Depends(get_portfolio_analytics_service),
):

    try:
        return await service.get_performance(portfolio_id, current_user.id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{portfolio_id}/allocation")
async def get_allocation(
    portfolio_id: UUID,
    group_by: str = "asset_class",
    current_user: User = Depends(get_current_user),
    service: PortfolioAnalyticsService = Depends(get_portfolio_analytics_service),
):

    try:
        return await service.get_allocation(
            portfolio_id, current_user.id, group_by
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
