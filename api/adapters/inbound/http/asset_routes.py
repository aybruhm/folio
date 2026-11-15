from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from adapters.inbound.http.dependencies import get_asset_service
from application.assets.asset_service import AssetService

router = APIRouter(prefix="/assets", tags=["assets"])


class BatchHistoryRequest(BaseModel):
    tickers: list[str]
    start_date: date | None = None
    end_date: date | None = None


@router.post("/history/batch")
async def get_price_history_batch(
    body: BatchHistoryRequest,
    service: AssetService = Depends(get_asset_service),
):
    return await service.batch_history(body.tickers, body.start_date, body.end_date)


@router.get("/search")
async def search_assets(
    q: str,
    service: AssetService = Depends(get_asset_service),
):
    try:
        return await service.search(q)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/validate")
async def validate_ticker(
    ticker: str,
    provider: str = "yfinance",
    currency: str = "USD",
    asset_class: str = "",
    service: AssetService = Depends(get_asset_service),
):
    try:
        return await service.validate(ticker, provider, currency, asset_class)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/{ticker}/history")
async def get_price_history(
    ticker: str,
    start_date: date | None = None,
    end_date: date | None = None,
    service: AssetService = Depends(get_asset_service),
):
    try:
        return await service.history(ticker, start_date, end_date)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))
