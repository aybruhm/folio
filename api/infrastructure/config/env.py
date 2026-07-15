import os
from functools import lru_cache

from pydantic import BaseModel


def _asyncpg_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


class EnvironSettings(BaseModel):
    # Platform
    DATABASE_URL: str = _asyncpg_url(
        os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
        )
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # API
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")

    # Auth
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    ENABLE_REGISTRATION: bool = (
        os.getenv("ENABLE_REGISTRATION", "true").lower() != "false"
    )
    SECURE_COOKIES: bool = os.getenv("API_ENV", "development") == "production"
    # Optional: set to e.g. ".domain.com" when frontend and API are on
    # different subdomains, so cookies are scoped across both and browsers
    # treat them as first-party (not blocked by tracking protection).
    # Leave empty for same-origin or reverse-proxy setups.
    COOKIE_DOMAIN: str = os.getenv("COOKIE_DOMAIN", "")

    # Market cache data
    YFINANCE_CACHE_TTL: int = int(os.getenv("YFINANCE_CACHE_TTL", "3600"))  # 1 hour
    YFINANCE_PRICE_HISTORY_CACHE_TTL: int = int(
        os.getenv("YFINANCE_PRICE_HISTORY_CACHE_TTL", "86400")
    )  # 1 day
    MARKET_DATA_CACHE_TTL: int = int(
        os.getenv("MARKET_DATA_CACHE_TTL", "10800")
    )  # 3 hours — cached in Valkey
    MARKET_DATA_WARM_JOB_TTL: int = int(os.getenv("MARKET_DATA_WARM_JOB_TTL", "43200")) # 12 hours

    # Market data
    TIINGO_API_KEY: str = os.getenv("TIINGO_API_KEY", "")
    NGNMARKET_API_BASE_URL: str = os.getenv(
        "NGNMARKET_API_BASE_URL", "https://api.ngnmarket.com/v1"
    )
    NGNMARKET_API_KEY: str = os.getenv("NGNMARKET_API_KEY", "")
    RAPID_API_BASE_URL: str = os.getenv(
        "RAPID_API_BASE_URL", "https://tradingview-data1.p.rapidapi.com/"
    )
    RAPID_API_KEY: str = os.getenv("RAPID_API_KEY", "")
    NGXPULSE_API_BASE_URL: str = os.getenv(
        "NGXPULSE_API_BASE_URL", "https://www.ngxpulse.ng"
    )
    NGXPULSE_API_KEY: str = os.getenv("NGXPULSE_API_KEY", "")

    # Scheduler
    SCHEDULER_ENABLED: bool = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"
    SCHEDULER_TIMEZONE: str = os.getenv("SCHEDULER_TIMEZONE", "UTC")
    PRICE_REFRESH_SCHEDULE: str = "0 18 * * *"  # 18:00 UTC daily
    FX_REFRESH_SCHEDULE: str = "0 18:30 * * *"  # 18:30 UTC daily


@lru_cache
def get_environ_settings() -> EnvironSettings:
    return EnvironSettings()
