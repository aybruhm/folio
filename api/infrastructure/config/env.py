import os

from functools import lru_cache
from pydantic import BaseModel


class EnvironSettings(BaseModel):
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    )

    # API
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # Market data
    YFINANCE_CACHE_TTL: int = 3600  # 1 hour
    YFINANCE_PRICE_HISTORY_CACHE_TTL: int = 86400  # 1 day

    # Scheduler
    SCHEDULER_ENABLED: bool = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"
    SCHEDULER_TIMEZONE: str = os.getenv("SCHEDULER_TIMEZONE", "UTC")
    PRICE_REFRESH_SCHEDULE: str = "0 18 * * *"  # 18:00 UTC daily
    FX_REFRESH_SCHEDULE: str = "0 18:30 * * *"  # 18:30 UTC daily


@lru_cache
def get_environ_settings() -> EnvironSettings:
    return EnvironSettings()
