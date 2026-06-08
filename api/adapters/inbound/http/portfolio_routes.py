import asyncio
from collections.abc import Coroutine
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


async def _fetch_fx_rate(from_ccy: str, to_ccy: str) -> int:
    """Return the ×100 FX rate for *from_ccy* → *to_ccy* using yfinance."""
    if from_ccy == to_ccy:
        return 100
    import yfinance as yf

    ticker = f"{from_ccy}{to_ccy}=X"
    try:
        t = yf.Ticker(ticker)
        data = t.history(period="1d")
        if data.empty:
            return 0
        return round(float(data["Close"].iloc[-1]) * 100)
    except Exception:
        return 0


def _check_ownership(portfolio: dict, current_user: User) -> None:
    if portfolio.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )


async def _build_portfolio_analytics(
    session: AsyncSession,
    portfolio_id: UUID,
    timeframe: str,
    base_currency: Currency = Currency.USD,
) -> dict:
    interactor = AnalyticsInteractor(session, base_currency)

    holdings = await interactor.get_holdings(portfolio_id, base_currency)
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

    holdings_with_weight = [
        {
            **h,
            "weight_percent": (
                round((float(h["market_value"]) / current_value) * 100, 2)
                if current_value > 0
                else 0.0
            ),
        }
        for h in holdings
    ]

    top_holdings_by_weight = sorted(
        holdings_with_weight,
        key=lambda h: float(h.get("weight_percent", 0)),
        reverse=True,
    )[:10]

    return {
        "portfolio_id": str(portfolio_id),
        "total_invested": float(total_invested),
        "current_value": float(current_value),
        "total_gain_loss": float(total_gain_loss),
        "holdings": holdings_with_weight,
        "total_gain_loss_percent": float(round(total_gain_loss_percent, 2)),
        "twr": performance.get("twr", "0"),
        "mwr": performance.get("mwr", "0"),
        "allocation": allocation,
        "top_holdings": [
            {
                "ticker": h.get("ticker"),
                "value": float(h.get("market_value", 0)),
                "percent": float(h.get("weight_percent", 0)),
            }
            for h in top_holdings_by_weight
        ],
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
    in_currency: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        portfolio_interactor = PortfolioInteractor(session)
        portfolios = await portfolio_interactor.list_portfolios(current_user.id)
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
                    rate = await _fetch_fx_rate(portfolio_ccy.value, display_ccy.value)
                    if rate and rate != 100:
                        item["total_invested"] = round(
                            float(item["total_invested"]) * rate / 100, 2
                        )
                        item["current_value"] = round(
                            float(item["current_value"]) * rate / 100, 2
                        )
                        item["total_gain_loss"] = round(
                            float(item["total_gain_loss"]) * rate / 100, 2
                        )
                        # Convert holdings values
                        for h in item.get("holdings", []):
                            h["current_price"] = round(
                                float(h["current_price"]) * rate / 100, 2
                            )
                            h["market_value"] = round(
                                float(h["market_value"]) * rate / 100, 2
                            )
                            h["cost_basis"] = round(
                                float(h["cost_basis"]) * rate / 100, 2
                            )
                            h["total_return"] = round(
                                float(h["total_return"]) * rate / 100, 2
                            )
                        # Convert performance/contribution history
                        for pt in item.get("performance_history", []):
                            pt["value"] = round(float(pt["value"]) * rate / 100, 2)
                        for pt in item.get("contribution_history", []):
                            pt["value"] = round(float(pt["value"]) * rate / 100, 2)
                        # Convert allocation and top_holdings
                        for a in item.get("allocation", []):
                            a["value"] = round(float(a["value"]) * rate / 100, 2)
                        for th in item.get("top_holdings", []):
                            th["value"] = round(float(th["value"]) * rate / 100, 2)
                        for sb in item.get("sector_breakdown", []):
                            sb["value"] = round(float(sb["value"]) * rate / 100, 2)
        return list(analytics)
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

        base_ccy = Currency(portfolio.get("base_currency", "USD"))
        return await _build_portfolio_analytics(
            session, portfolio_id, timeframe, base_ccy
        )
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

        base_currency_str = portfolio.get("base_currency", "USD")
        base_currency = Currency(base_currency_str)
        currency = Currency(in_currency) if in_currency else base_currency

        interactor = AnalyticsInteractor(session, base_currency)
        holdings = await interactor.get_holdings(portfolio_id, currency)

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
