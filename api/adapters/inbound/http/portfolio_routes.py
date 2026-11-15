from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from adapters.inbound.http.dependencies import (
    get_portfolio_analytics_service,
    get_portfolio_service,
    get_current_user,
    invalidate_benchmark_cache,
)
from application.analytics.portfolio_analytics_service import (
    BenchmarkError,
    PortfolioAnalyticsService,
)
from application.portfolio.portfolio_service import PortfolioService
from domain.entities.models import User
from domain.ports.inbound.use_cases import CreatePortfolioRequest
from domain.value_objects.money import Currency

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


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
    service: PortfolioAnalyticsService = Depends(get_portfolio_analytics_service),
):
    try:
        display_currency = Currency(in_currency) if in_currency else None
        return await service.list_analytics(
            current_user.id, timeframe, display_currency, include_archived
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analytics/summary")
async def get_analytics_summary(
    timeframe: str = "1y",
    in_currency: str = "USD",
    current_user: User = Depends(get_current_user),
    service: PortfolioAnalyticsService = Depends(get_portfolio_analytics_service),
):
    """All active portfolios merged into one analytics view in *in_currency*.

    Portfolios whose FX rate can't be fetched are left out rather than mixed
    in unconverted; their ids are listed in `excluded_portfolio_ids`.
    """
    try:
        display_ccy = Currency(in_currency)
        return await service.get_summary(current_user.id, timeframe, display_ccy)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analytics/benchmark")
async def get_benchmark_comparison(
    benchmark: str,
    response: Response,
    period: str = "1y",
    in_currency: str = "USD",
    portfolio_id: UUID | None = None,
    provider: str | None = None,
    current_user: User = Depends(get_current_user),
    service: PortfolioAnalyticsService = Depends(get_portfolio_analytics_service),
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
    try:
        payload, cache_status = await service.get_benchmark_comparison(
            benchmark,
            period,
            in_currency,
            portfolio_id,
            provider,
            current_user.id,
        )
        response.headers["X-Cache"] = cache_status
        return payload
    except BenchmarkError as error:
        raise HTTPException(error.status_code, detail=error.detail)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))

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
