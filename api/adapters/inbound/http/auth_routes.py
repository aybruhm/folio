from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.inbound.http.dependencies import get_current_user
from adapters.outbound.persistence.token_repository import RefreshTokenRepository
from adapters.outbound.persistence.user_repository import UserRepository
from application.auth.use_cases import LoginUser, LogoutUser, RefreshToken, RegisterUser
from domain.entities.models import User
from infrastructure.config import settings
from infrastructure.db.session import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterBody(BaseModel):
    email: EmailStr
    password: str


class LoginBody(BaseModel):
    email: EmailStr
    password: str


def _set_auth_cookies(
    response: Response, access_token: str, refresh_token: str
) -> None:
    # In production (secure=True) we use SameSite=None so cookies flow
    # cross-origin (e.g. Railway with separate frontend/API domains).
    # For same-origin setups this is identical to Lax and has no downside.
    samesite: str = "none" if settings.SECURE_COOKIES else "lax"
    domain: str | None = settings.COOKIE_DOMAIN or None

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite=samesite,
        secure=settings.SECURE_COOKIES,
        domain=domain,
        path="/",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite=samesite,
        secure=settings.SECURE_COOKIES,
        domain=domain,
        path="/",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )


def _clear_auth_cookies(response: Response) -> None:
    domain: str | None = settings.COOKIE_DOMAIN or None
    response.delete_cookie(key="access_token", path="/", domain=domain)
    response.delete_cookie(key="refresh_token", path="/", domain=domain)


def _user_response(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "created_at": user.created_at.isoformat(),
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterBody,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    if len(body.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Password must be at least 8 characters",
        )
    try:
        use_case = RegisterUser(
            UserRepository(session), RefreshTokenRepository(session)
        )
        user, access_token, refresh_token = await use_case.execute(
            body.email, body.password
        )
        await session.commit()
        _set_auth_cookies(response, access_token, refresh_token)
        return _user_response(user)
    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login")
async def login(
    body: LoginBody,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    try:
        use_case = LoginUser(UserRepository(session), RefreshTokenRepository(session))
        user, access_token, refresh_token = await use_case.execute(
            body.email, body.password
        )
        await session.commit()
        _set_auth_cookies(response, access_token, refresh_token)
        return _user_response(user)
    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/refresh")
async def refresh(
    response: Response,
    session: AsyncSession = Depends(get_session),
    refresh_token: str | None = Cookie(default=None),
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
        )
    try:
        use_case = RefreshToken(
            UserRepository(session), RefreshTokenRepository(session)
        )
        _, new_access_token, new_refresh_token = await use_case.execute(refresh_token)
        await session.commit()
        _set_auth_cookies(response, new_access_token, new_refresh_token)
        return {"message": "Token refreshed"}
    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    session: AsyncSession = Depends(get_session),
    refresh_token: str | None = Cookie(default=None),
):
    try:
        use_case = LogoutUser(RefreshTokenRepository(session))
        await use_case.execute(refresh_token)
        await session.commit()
    except Exception:
        await session.rollback()
    finally:
        _clear_auth_cookies(response)


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat(),
    }
