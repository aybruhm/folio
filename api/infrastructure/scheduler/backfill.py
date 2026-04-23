import asyncio
import logging
from datetime import date, timedelta
from uuid import UUID

from adapters.outbound.market_data.yfinance_adapter import YFinanceAdapter
from adapters.outbound.persistence.price_repository import PriceHistoryRepository
from infrastructure.db.session import async_session

logger = logging.getLogger(__name__)

async def backfill_price_history(ticker: str, asset_id: UUID):
    logger.info(f"Starting price history backfill for {ticker}")
    
    try:
        yfinance = YFinanceAdapter()
        
        end_date = date.today()
        start_date = end_date - timedelta(days=365 * 5)
        
        history = await yfinance.get_price_history(ticker, start_date, end_date)
        
        async with async_session() as session:
            price_repo = PriceHistoryRepository(session)
            
            for price_date, price_close in history:
                try:
                    await price_repo.add(
                        asset_id=asset_id,
                        date_val=price_date,
                        close=price_close,
                        currency=None
                    )
                except Exception as e:
                    logger.debug(f"Error adding price {ticker} on {price_date}: {e}")
            
            await session.commit()
        
        logger.info(f"Price history backfill completed for {ticker}: {len(history)} records")
        return len(history)
    
    except Exception as e:
        logger.error(f"Price history backfill failed for {ticker}: {e}")
        raise
