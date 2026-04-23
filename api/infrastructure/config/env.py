import os

from pydantic import BaseModel


class EnvironSettings(BaseModel):
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    )
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "")
    SCHEDULER_ENABLED: bool = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"
    SCHEDULER_TIMEZONE: str = os.getenv("SCHEDULER_TIMEZONE", "UTC")
