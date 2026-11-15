from collections.abc import Callable
from typing import Protocol

from application.auth.use_cases import (
    LoginUser,
    LogoutUser,
    RefreshToken,
    RegisterUser,
)
from domain.ports.outbound.repositories import ITokenRepository, IUserRepository


class AuthUnitOfWork(Protocol):
    user_repo: IUserRepository
    token_repo: ITokenRepository

    async def __aenter__(self) -> "AuthUnitOfWork": ...

    async def __aexit__(self, exc_type, exc_value, traceback) -> None: ...


class AuthService:
    def __init__(
        self,
        unit_of_work_factory: Callable[[], AuthUnitOfWork],
        register_use_case: type[RegisterUser] = RegisterUser,
        login_use_case: type[LoginUser] = LoginUser,
        refresh_use_case: type[RefreshToken] = RefreshToken,
        logout_use_case: type[LogoutUser] = LogoutUser,
    ):
        self.unit_of_work_factory = unit_of_work_factory
        self.register_use_case = register_use_case
        self.login_use_case = login_use_case
        self.refresh_use_case = refresh_use_case
        self.logout_use_case = logout_use_case

    async def register(self, email: str, password: str):
        async with self.unit_of_work_factory() as unit_of_work:
            return await self.register_use_case(
                unit_of_work.user_repo, unit_of_work.token_repo
            ).execute(email, password)

    async def login(self, email: str, password: str):
        async with self.unit_of_work_factory() as unit_of_work:
            return await self.login_use_case(
                unit_of_work.user_repo, unit_of_work.token_repo
            ).execute(email, password)

    async def refresh(self, refresh_token: str):
        async with self.unit_of_work_factory() as unit_of_work:
            return await self.refresh_use_case(
                unit_of_work.user_repo, unit_of_work.token_repo
            ).execute(refresh_token)

    async def logout(self, refresh_token: str | None) -> None:
        async with self.unit_of_work_factory() as unit_of_work:
            await self.logout_use_case(unit_of_work.token_repo).execute(refresh_token)
