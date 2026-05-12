from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.inbound.http.dependencies import get_current_user
from application.analytics.analytics_interactor import AnalyticsInteractor
from application.portfolio.portfolio_interactor import PortfolioInteractor
from domain.entities.models import User
from domain.ports.inbound.use_cases import CreatePortfolioRequest
from domain.value_objects.money import Currency
from infrastructure.db.session import get_session

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


def _check_ownership(portfolio: dict, current_user: User) -> None:
    if portfolio.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )


async def _build_portfolio_analytics(
    session: AsyncSession,
    portfolio_id: UUID,
    timeframe: str,
) -> dict:
    interactor = AnalyticsInteractor(session, Currency.USD)

    holdings = await interactor.get_holdings(portfolio_id)
    performance = await interactor.calculate_performance(portfolio_id)
    allocation_raw = await interactor.get_allocation(portfolio_id)
    performance_history = await interactor.get_performance_history(
        portfolio_id, timeframe
    )
    contribution_history = await interactor.get_contribution_history(portfolio_id)
    sector_breakdown = await interactor.get_sector_breakdown(portfolio_id)

    current_value = sum(float(h["market_value"]) for h in holdings)
    total_invested = sum(float(h["cost_basis"]) for h in holdings)
    total_gain_loss = current_value - total_invested
    total_gain_loss_percent = (
        (total_gain_loss / total_invested * 100) if total_invested > 0 else 0.0
    )

    allocation = [
        {"label": a["name"], "value": float(a["value"])} for a in allocation_raw
    ]

    return {
        "portfolio_id": str(portfolio_id),
        "total_invested": float(total_invested),
        "current_value": float(current_value),
        "total_gain_loss": float(total_gain_loss),
        "total_gain_loss_percent": float(round(total_gain_loss_percent, 2)),
        "twr": performance.get("twr", "0"),
        "mwr": performance.get("mwr", "0"),
        "allocation": allocation,
        "performance_history": performance_history,
        "contribution_history": contribution_history,
        "sector_breakdown": sector_breakdown,
        "timeframe": timeframe,
    }


@router.get("/", response_model=List[dict])
async def list_portfolios(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    interactor = PortfolioInteractor(session)
    return await interactor.list_portfolios(current_user.id)


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    request: CreatePortfolioRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        interactor = PortfolioInteractor(session)
        portfolio_id = await interactor.create_portfolio(request, current_user.id)
        await session.commit()

        portfolio = await interactor.get_portfolio(portfolio_id)
        return portfolio
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analytics", response_model=List[dict])
async def list_portfolio_analytics(
    timeframe: str = "1y",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        portfolio_interactor = PortfolioInteractor(session)
        portfolios = await portfolio_interactor.list_portfolios(current_user.id)
        if not portfolios:
            return []

        analytics: List[dict] = []
        for portfolio in portfolios:
            analytics.append(
                await _build_portfolio_analytics(
                    session, UUID(portfolio["id"]), timeframe
                )
            )
        return analytics
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{portfolio_id}", response_model=dict)
async def get_portfolio(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        interactor = PortfolioInteractor(session)
        portfolio = await interactor.get_portfolio(portfolio_id)
        _check_ownership(portfolio, current_user)
        return portfolio
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{portfolio_id}")
async def update_portfolio(
    portfolio_id: UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        interactor = PortfolioInteractor(session)
        portfolio = await interactor.get_portfolio(portfolio_id)
        _check_ownership(portfolio, current_user)

        await interactor.update_portfolio(portfolio_id, name, description)
        await session.commit()

        return await interactor.get_portfolio(portfolio_id)
    except HTTPException:
        await session.rollback()
        raise
    except ValueError as e:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        interactor = PortfolioInteractor(session)
        portfolio = await interactor.get_portfolio(portfolio_id)
        _check_ownership(portfolio, current_user)

        await interactor.delete_portfolio(portfolio_id)
        await session.commit()
    except HTTPException:
        await session.rollback()
        raise
    except ValueError as e:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{portfolio_id}/analytics")
async def get_portfolio_analytics(
    portfolio_id: UUID,
    timeframe: str = "1y",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):

    try:
        portfolio_interactor = PortfolioInteractor(session)
        portfolio = await portfolio_interactor.get_portfolio(portfolio_id)
        _check_ownership(portfolio, current_user)

        return await _build_portfolio_analytics(session, portfolio_id, timeframe)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{portfolio_id}/holdings")
async def get_holdings(
    portfolio_id: UUID,
    in_currency: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):

    try:
        portfolio_interactor = PortfolioInteractor(session)
        portfolio = await portfolio_interactor.get_portfolio(portfolio_id)
        _check_ownership(portfolio, current_user)

        base_currency = Currency.USD
        currency = Currency(in_currency) if in_currency else base_currency

        interactor = AnalyticsInteractor(session, base_currency)
        holdings = await interactor.get_holdings(portfolio_id, currency)

        data = [
            {
                "ticker": h["ticker"],
                "quantity": h["quantity"],
                "avg_price": (
                    float(h["cost_basis"]) / float(h["quantity"])
                    if float(h["quantity"]) > 0
                    else 0.0
                ),
                "current_price": h["current_price"],
                "total_value": h["market_value"],
                "gain_loss": h["total_return"],
                "gain_loss_percent": h["total_return_percent"],
            }
            for h in holdings
        ]
        total_value = sum(float(h["market_value"]) for h in holdings)

        return {
            "data": data,
            "currency": currency.value,
            "total_value": float(total_value),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{portfolio_id}/performance")
async def get_performance(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):

    try:
        portfolio_interactor = PortfolioInteractor(session)
        portfolio = await portfolio_interactor.get_portfolio(portfolio_id)
        _check_ownership(portfolio, current_user)

        interactor = AnalyticsInteractor(session, Currency.USD)
        performance = await interactor.calculate_performance(portfolio_id)

        return {
            "portfolio_id": str(portfolio_id),
            "returns": float(performance.get("twr", 0)),
            "returns_percent": float(performance.get("twr", 0)),
            "start_date": performance.get("start_date", ""),
            "end_date": performance.get("end_date", ""),
            "data_points": [],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{portfolio_id}/allocation")
async def get_allocation(
    portfolio_id: UUID,
    group_by: str = "asset_class",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):

    try:
        portfolio_interactor = PortfolioInteractor(session)
        portfolio = await portfolio_interactor.get_portfolio(portfolio_id)
        _check_ownership(portfolio, current_user)

        interactor = AnalyticsInteractor(session, Currency.USD)
        allocation = await interactor.get_allocation(portfolio_id, group_by)

        return {
            "portfolio_id": str(portfolio_id),
            "allocations": [
                {
                    "category": item["name"],
                    "value": float(item["value"]),
                    "percent": float(item["weight_percent"]),
                    "holdings": [],
                }
                for item in allocation
            ],
            "group_by": group_by,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
