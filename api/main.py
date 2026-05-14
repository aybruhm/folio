from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapters.inbound.http import (
    asset_routes,
    auth_routes,
    benchmark_fx_routes,
    goal_routes,
    portfolio_routes,
    trade_routes,
)
from infrastructure.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Folio API...")
    try:
        yield
    finally:
        from adapters.outbound.market_data.ngnmarket_adapter import NgnMarketAdapter

        await NgnMarketAdapter.close_shared_session()
        print("Shutting down Folio API...")


app = FastAPI(
    title="Folio API",
    description="Self-hosted investment tracking platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(auth_routes.router)
v1_router.include_router(portfolio_routes.router)
v1_router.include_router(trade_routes.router)
v1_router.include_router(goal_routes.router)
v1_router.include_router(asset_routes.router)
v1_router.include_router(benchmark_fx_routes.router_benchmarks)
v1_router.include_router(benchmark_fx_routes.router_fx)

app.include_router(v1_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
