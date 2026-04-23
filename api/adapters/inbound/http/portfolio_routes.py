from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List, Optional

from domain.value_objects.money import Currency
from domain.ports.inbound.use_cases import CreatePortfolioRequest
from application.portfolio.portfolio_interactor import PortfolioInteractor
from adapters.outbound.persistence.portfolio_repository import PortfolioRepository
from infrastructure.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/portfolios", tags=["portfolios"])

class PortfolioResponse:
    id: str
    name: str
    base_currency: str
    description: Optional[str]
    created_at: str
    updated_at: str

@router.get("/", response_model=List[dict])
async def list_portfolios(session: AsyncSession = Depends(get_session)):
    interactor = PortfolioInteractor(session)
    portfolios = await interactor.list_portfolios()
    return portfolios

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    request: CreatePortfolioRequest,
    session: AsyncSession = Depends(get_session)
):
    try:
        interactor = PortfolioInteractor(session)
        portfolio_id = await interactor.create_portfolio(request)
        await session.commit()
        
        portfolio = await interactor.get_portfolio(portfolio_id)
        return portfolio
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{portfolio_id}", response_model=dict)
async def get_portfolio(
    portfolio_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    try:
        interactor = PortfolioInteractor(session)
        portfolio = await interactor.get_portfolio(portfolio_id)
        return portfolio
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{portfolio_id}")
async def update_portfolio(
    portfolio_id: UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    try:
        interactor = PortfolioInteractor(session)
        await interactor.update_portfolio(portfolio_id, name, description)
        await session.commit()
        
        portfolio = await interactor.get_portfolio(portfolio_id)
        return portfolio
    except ValueError as e:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    try:
        interactor = PortfolioInteractor(session)
        await interactor.delete_portfolio(portfolio_id)
        await session.commit()
    except ValueError as e:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{portfolio_id}/holdings")
async def get_holdings(
    portfolio_id: UUID,
    in_currency: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    from application.analytics.analytics_interactor import AnalyticsInteractor
    from infrastructure.db.session import async_session
    
    try:
        base_currency = Currency.USD
        currency = Currency(in_currency) if in_currency else base_currency
        
        interactor = AnalyticsInteractor(session, base_currency)
        holdings = await interactor.get_holdings(portfolio_id, currency)
        return holdings
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{portfolio_id}/performance")
async def get_performance(
    portfolio_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    from application.analytics.analytics_interactor import AnalyticsInteractor
    
    try:
        interactor = AnalyticsInteractor(session, Currency.USD)
        performance = await interactor.calculate_performance(portfolio_id)
        return performance
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{portfolio_id}/allocation")
async def get_allocation(
    portfolio_id: UUID,
    group_by: str = "asset_class",
    session: AsyncSession = Depends(get_session)
):
    from application.analytics.analytics_interactor import AnalyticsInteractor
    
    try:
        interactor = AnalyticsInteractor(session, Currency.USD)
        allocation = await interactor.get_allocation(portfolio_id, group_by)
        return allocation
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
