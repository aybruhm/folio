import asyncio
import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.outbound.market_data.ngnmarket_adapter import NgnMarketAdapter
from adapters.outbound.market_data.tiingo_adapter import TiingoAdapter
from adapters.outbound.market_data.tradingview_adapter import TradingviewAdapter
from adapters.outbound.market_data.yfinance_adapter import YFinanceAdapter
from adapters.outbound.persistence.asset_repository import AssetRepository
from infrastructure.db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["assets"])


def _normalize_provider(provider: str) -> str:
    normalized = (provider or "yfinance").strip().lower()
    return (
        normalized
        if normalized in {"yfinance", "tiingo", "ngnmarket", "tradingview"}
        else "yfinance"
    )


class BatchHistoryRequest(BaseModel):
    tickers: list[str]
    start_date: Optional[date] = None
    end_date: Optional[date] = None


@router.post("/history/batch")
async def get_price_history_batch(
    body: BatchHistoryRequest,
    session: AsyncSession = Depends(get_session),
):
    end = body.end_date or date.today()
    start = body.start_date or (end - timedelta(days=30))

    repo = AssetRepository(session)
    assets = await repo.list_all()
    provider_map = {a.ticker.upper(): a.market_data_provider for a in assets}

    yfinance = YFinanceAdapter()
    tiingo = TiingoAdapter()
    tradingview = TradingviewAdapter()
    ngnmarket = NgnMarketAdapter()

    def _pick_adapter(ticker: str):
        provider = _normalize_provider(provider_map.get(ticker.upper(), "yfinance"))
        if provider == "tradingview":
            return tradingview
        if provider == "tiingo":
            return tiingo
        if provider == "ngnmarket":
            return ngnmarket
        return yfinance

    async def _fetch(ticker: str):
        try:
            adapter = _pick_adapter(ticker)
            history = await adapter.get_price_history(ticker, start, end)
            return {
                "ticker": ticker,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "data": [
                    {"date": d.isoformat(), "close": str(price / 100)}
                    for d, price in history
                ],
            }
        except Exception as e:
            logger.error(
                f"Exception occured when retrieving price history of {ticker}: {str(e)}"
            )
            return {
                "ticker": ticker,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "data": [],
            }

    results = await asyncio.gather(*[_fetch(t) for t in body.tickers])
    return {"results": results}


@router.get("/search")
async def search_assets(q: str, session: AsyncSession = Depends(get_session)):
    try:
        if not q or len(q) < 1:
            raise ValueError("Search query must be at least 1 character")

        repo = AssetRepository(session)
        assets = await repo.search_by_ticker(q, limit=10)

        return [
            {
                "id": str(a.id),
                "ticker": a.ticker,
                "name": a.name,
                "asset_class": a.asset_class.value,
                "currency": a.currency.value,
            }
            for a in assets
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/validate")
async def validate_ticker(
    ticker: str,
    provider: str = "yfinance",
    currency: str = "USD",
    session: AsyncSession = Depends(get_session),
):
    try:
        _ = session
        selected = _normalize_provider(provider)

        if selected == "tiingo":
            adapter = TiingoAdapter()
            metadata = await adapter.get_asset_metadata(ticker, currency)
        elif selected == "ngnmarket":
            adapter = NgnMarketAdapter()
            metadata = await adapter.get_asset_metadata(ticker, currency)
        elif selected == "tradingview":
            adapter = TradingviewAdapter()
            metadata = await adapter.get_asset_metadata(ticker, currency)
            print(f"TradingView metadata for {ticker}: {metadata}")
        else:
            adapter = YFinanceAdapter()
            metadata = await adapter.get_asset_metadata(ticker, currency)

        return {
            "ticker": ticker,
            "provider": selected,
            "supported": metadata is not None,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{ticker}/history")
async def get_price_history(
    ticker: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    session: AsyncSession = Depends(get_session),
):
    try:
        end = end_date or date.today()
        start = start_date or (end - timedelta(days=365))

        repo = AssetRepository(session)
        asset = await repo.get_by_ticker(ticker)
        provider = _normalize_provider(
            asset.market_data_provider if asset else "yfinance"
        )

        if provider == "tradingview":
            adapter = TradingviewAdapter()
        elif provider == "tiingo":
            adapter = TiingoAdapter()
        elif provider == "ngnmarket":
            adapter = NgnMarketAdapter()
        else:
            adapter = YFinanceAdapter()

        history = await adapter.get_price_history(ticker, start, end)

        return {
            "ticker": ticker,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "data": [
                {"date": d.isoformat(), "close": str(price / 100)}
                for d, price in history
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
