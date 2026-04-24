from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.outbound.market_data.yfinance_adapter import YFinanceAdapter
from domain.value_objects.money import Currency
from infrastructure.db.session import get_session

router_benchmarks = APIRouter(prefix="/benchmarks", tags=["benchmarks"])
router_fx = APIRouter(prefix="/fx", tags=["fx"])


@router_benchmarks.get("/")
async def list_benchmarks(session: AsyncSession = Depends(get_session)):
    benchmarks = [
        {"ticker": "^GSPC", "name": "S&P 500"},
        {"ticker": "IWDA.L", "name": "MSCI World"},
        {"ticker": "^NDX", "name": "Nasdaq-100"},
    ]
    return benchmarks


@router_benchmarks.post("/")
async def add_benchmark(
    ticker: str, name: str, session: AsyncSession = Depends(get_session)
):
    return {"ticker": ticker, "name": name}


@router_benchmarks.delete("/{benchmark_id}")
async def delete_benchmark(
    benchmark_id: UUID, session: AsyncSession = Depends(get_session)
):
    return {"status": "deleted"}


@router_fx.get("/rates")
async def get_fx_rates(
    currencies: List[str] = None, session: AsyncSession = Depends(get_session)
):
    try:
        if not currencies:
            currencies = ["USD", "GBP", "EUR", "JPY"]

        yfinance = YFinanceAdapter()
        rates = {}

        for ccy in currencies:
            try:
                rate = await yfinance.get_current_rate(Currency("USD"), Currency(ccy))
                rates[f"USD{ccy}"] = str(rate / 100) if rate else None
            except:
                rates[f"USD{ccy}"] = None

        return rates
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
