from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from adapters.inbound.http.dependencies import (
    get_benchmark_fx_service,
)
from application.market_data.benchmark_fx_service import BenchmarkFxService

router_benchmarks = APIRouter(prefix="/benchmarks", tags=["benchmarks"])
router_fx = APIRouter(prefix="/fx", tags=["fx"])


@router_benchmarks.get("/")
async def list_benchmarks(
    service: BenchmarkFxService = Depends(get_benchmark_fx_service),
):
    return service.list_benchmarks()


@router_benchmarks.post("/")
async def add_benchmark(
    ticker: str,
    name: str,
    service: BenchmarkFxService = Depends(get_benchmark_fx_service),
):
    return service.add_benchmark(ticker, name)


@router_benchmarks.delete("/{benchmark_id}")
async def delete_benchmark(
    benchmark_id: UUID,
    service: BenchmarkFxService = Depends(get_benchmark_fx_service),
):
    return service.delete_benchmark(benchmark_id)


@router_fx.get("/rates")
async def get_fx_rates(
    currencies: list[str] = None,
    service: BenchmarkFxService = Depends(get_benchmark_fx_service),
):
    try:
        return await service.get_fx_rates(currencies)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
