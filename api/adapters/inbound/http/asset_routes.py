from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import date

from api.adapters.outbound.persistence.asset_repository import AssetRepository
from api.adapters.outbound.persistence.price_repository import PriceHistoryRepository
from api.adapters.outbound.market_data.yfinance_adapter import YFinanceAdapter
from api.infrastructure.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])

@router.get("/search")
async def search_assets(
    q: str,
    session: AsyncSession = Depends(get_session)
):
    try:
        if not q or len(q) < 1:
            raise ValueError("Search query must be at least 1 character")
        
        repo = AssetRepository(session)
        assets = await repo.search_by_ticker(q, limit=10)
        
        return [
            {
                'id': str(a.id),
                'ticker': a.ticker,
                'name': a.name,
                'asset_class': a.asset_class.value,
                'currency': a.currency.value,
            }
            for a in assets
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{ticker}/history")
async def get_price_history(
    ticker: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    session: AsyncSession = Depends(get_session)
):
    try:
        from datetime import date as date_class, timedelta
        
        end = end_date or date_class.today()
        start = start_date or (end - timedelta(days=365))
        
        yfinance = YFinanceAdapter()
        history = await yfinance.get_price_history(ticker, start, end)
        
        return {
            'ticker': ticker,
            'start_date': start.isoformat(),
            'end_date': end.isoformat(),
            'data': [
                {'date': d.isoformat(), 'close': str(price)}
                for d, price in history
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
