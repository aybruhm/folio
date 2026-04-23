from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from infrastructure.config import settings

from adapters.inbound.http import portfolio_routes, trade_routes, goal_routes, asset_routes, benchmark_fx_routes

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Folio API...")
    yield
    print("Shutting down Folio API...")

app = FastAPI(
    title="Folio API",
    description="Self-hosted investment tracking platform",
    version="1.0.0",
    lifespan=lifespan
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

app.include_router(portfolio_routes.router)
app.include_router(trade_routes.router)
app.include_router(goal_routes.router)
app.include_router(asset_routes.router)
app.include_router(benchmark_fx_routes.router_benchmarks)
app.include_router(benchmark_fx_routes.router_fx)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
