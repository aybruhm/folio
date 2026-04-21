from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.infrastructure.config import settings

# Import routers (will be created in Phase 5)
# from api.adapters.inbound.http import routers

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    print("Starting Folio API...")
    yield
    print("Shutting down Folio API...")

app = FastAPI(
    title="Folio API",
    description="Self-hosted investment tracking platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# TODO: Include routers from api.adapters.inbound.http once implemented
# app.include_router(...)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
