import os

from functools import lru_cache
from pydantic import BaseModel


class EnvironSettings(BaseModel):
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    )

    # API
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")

    # Auth
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    SECURE_COOKIES: bool = os.getenv("API_ENV", "development") == "production"

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
