"""
Application configuration via pydantic-settings
"""

from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    database_url: str = "postgresql+asyncpg://folio:folio_dev_password@localhost:5432/folio"
    
    # API
    secret_key: str = "dev-secret-key-change-in-production"
    allowed_origins: str = "http://localhost:3000"
    
    # Market data
    yfinance_cache_ttl: int = 3600  # 1 hour
    yfinance_price_history_cache_ttl: int = 86400  # 1 day
    
    # Scheduler
    scheduler_enabled: bool = True
    price_refresh_schedule: str = "0 18 * * *"  # 18:00 UTC daily
    fx_refresh_schedule: str = "0 18:30 * * *"  # 18:30 UTC daily
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

settings = get_settings()
