from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.market_data.benchmark_cache import BenchmarkCache
from application.auth.services import AuthService
from application.portfolio.portfolio_service import PortfolioService
from application.trades.trade_service import TradeService
from infrastructure.composition import auth_service, portfolio_service, trade_service
from infrastructure.db.postgres.users.dao import UserRepository
from domain.entities.models import User
from infrastructure.db.postgres.engine import get_session
from infrastructure.security.jwt import decode_access_token


def get_auth_service() -> AuthService:
    return auth_service


def get_portfolio_service() -> PortfolioService:
    return portfolio_service


def get_trade_service() -> TradeService:
    return trade_service


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    user = await UserRepository(session).get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    return user


async def invalidate_benchmark_cache():
    """Drop cached benchmark comparisons once a route that changes trades or
    portfolios has run, so the next comparison reflects the change."""
    try:
        yield
    finally:
        await BenchmarkCache().invalidate()
