from datetime import datetime, timedelta
from uuid import uuid4

import bcrypt
from fastapi import HTTPException, status

from domain.entities.models import User
from domain.ports.outbound.repositories import ITokenRepository, IUserRepository
from infrastructure.config import settings
from infrastructure.security.jwt import create_access_token


def _hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _refresh_token_expires_at() -> datetime:
    return datetime.now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


class RegisterUser:
    def __init__(self, user_repo: IUserRepository, token_repo: ITokenRepository):
        self.user_repo = user_repo
        self.token_repo = token_repo

    async def execute(self, email: str, password: str) -> tuple[User, str, str]:
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        hashed = _hash_password(password)
        user = await self.user_repo.create(email, hashed)

        access_token, _ = create_access_token(user.id, user.email)
        refresh_token = str(uuid4())
        family_id = uuid4()
        await self.token_repo.create(
            user.id, refresh_token, family_id, _refresh_token_expires_at()
        )

        return user, access_token, refresh_token


class LoginUser:
    def __init__(self, user_repo: IUserRepository, token_repo: ITokenRepository):
        self.user_repo = user_repo
        self.token_repo = token_repo

    async def execute(self, email: str, password: str) -> tuple[User, str, str]:
        user = await self.user_repo.get_by_email(email)
        if not user or not _verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        access_token, _ = create_access_token(user.id, user.email)
        refresh_token = str(uuid4())
        family_id = uuid4()
        await self.token_repo.create(
            user.id, refresh_token, family_id, _refresh_token_expires_at()
        )

        return user, access_token, refresh_token


class RefreshToken:
    def __init__(self, user_repo: IUserRepository, token_repo: ITokenRepository):
        self.user_repo = user_repo
        self.token_repo = token_repo

    async def execute(self, refresh_token: str) -> tuple[User, str, str]:
        record = await self.token_repo.get_by_token(refresh_token)

        if not record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        if record["is_revoked"]:
            await self.token_repo.revoke_family(record["family_id"])
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token reuse detected — all sessions revoked",
            )

        if record["expires_at"] < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        await self.token_repo.revoke(refresh_token)

        user = await self.user_repo.get_by_id(record["user_id"])
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        new_access_token, _ = create_access_token(user.id, user.email)
        new_refresh_token = str(uuid4())
        await self.token_repo.create(
            user.id, new_refresh_token, record["family_id"], _refresh_token_expires_at()
        )

        return user, new_access_token, new_refresh_token


class LogoutUser:
    def __init__(self, token_repo: ITokenRepository):
        self.token_repo = token_repo

    async def execute(self, refresh_token: str | None) -> None:
        if refresh_token:
            await self.token_repo.revoke(refresh_token)
