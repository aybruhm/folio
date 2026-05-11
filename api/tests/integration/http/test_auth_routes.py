from datetime import datetime
from uuid import uuid4

import pytest

from adapters.inbound.http import auth_routes
from application.auth import use_cases as auth_use_cases
from domain.entities.models import User
from fastapi import HTTPException


class FakeUserRepo:
    def __init__(self, users=None):
        self.users_by_email = users or {}
        self.users_by_id = {u.id: u for u in self.users_by_email.values()}

    async def create(self, email: str, hashed_password: str):
        user = User(
            id=uuid4(),
            email=email,
            hashed_password=hashed_password,
            is_active=True,
            created_at=datetime(2024, 1, 1, 12, 0),
        )
        self.users_by_email[email] = user
        self.users_by_id[user.id] = user
        return user

    async def get_by_email(self, email: str):
        return self.users_by_email.get(email)

    async def get_by_id(self, user_id):
        return self.users_by_id.get(user_id)


class FakeTokenRepo:
    def __init__(self, record=None):
        self.record = record
        self.created = []
        self.revoked = []
        self.revoked_families = []

    async def create(self, user_id, token, family_id, expires_at):
        self.created.append((user_id, token, family_id, expires_at))
        self.record = {
            "user_id": user_id,
            "token": token,
            "family_id": family_id,
            "is_revoked": False,
            "expires_at": expires_at,
        }

    async def get_by_token(self, token):
        return self.record if self.record and self.record["token"] == token else None

    async def revoke(self, token):
        self.revoked.append(token)
        if self.record and self.record["token"] == token:
            self.record["is_revoked"] = True

    async def revoke_family(self, family_id):
        self.revoked_families.append(family_id)


def _patch_auth_repos(monkeypatch, user_repo, token_repo):
    monkeypatch.setattr(auth_routes, "UserRepository", lambda session: user_repo)
    monkeypatch.setattr(
        auth_routes, "RefreshTokenRepository", lambda session: token_repo
    )


@pytest.mark.integration
@pytest.mark.happy_path
def test_register_login_refresh_logout_and_me_paths(client, authed_client, monkeypatch):
    user_repo = FakeUserRepo()
    token_repo = FakeTokenRepo()
    _patch_auth_repos(monkeypatch, user_repo, token_repo)

    register = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "password123"},
    )
    assert register.status_code == 201
    assert register.json()["email"] == "new@example.com"
    assert "access_token" in register.cookies
    assert "refresh_token" in register.cookies

    login_repo = FakeUserRepo(
        {
            "login@example.com": User(
                id=uuid4(),
                email="login@example.com",
                hashed_password=auth_use_cases._hash_password("password123"),
                is_active=True,
                created_at=datetime(2024, 1, 1, 12, 0),
            )
        }
    )
    _patch_auth_repos(monkeypatch, login_repo, FakeTokenRepo())
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    assert login.json()["email"] == "login@example.com"

    refresh_token = login.cookies.get("refresh_token")
    assert refresh_token
    client.cookies.set("refresh_token", refresh_token)
    refresh = client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200
    assert refresh.json() == {"message": "Token refreshed"}

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204

    me = authed_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_login_refresh_and_me_error_paths(client, monkeypatch):
    user_repo = FakeUserRepo(
        {
            "bad@example.com": User(
                id=uuid4(),
                email="bad@example.com",
                hashed_password=auth_use_cases._hash_password("password123"),
                is_active=True,
                created_at=datetime(2024, 1, 1, 12, 0),
            )
        }
    )
    _patch_auth_repos(monkeypatch, user_repo, FakeTokenRepo())

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "bad@example.com", "password": "wrong-password"},
    )
    assert login.status_code == 401

    missing_refresh = client.post("/api/v1/auth/refresh")
    assert missing_refresh.status_code == 401

    unauthenticated = client.get("/api/v1/auth/me")
    assert unauthenticated.status_code == 401


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_register_rejects_short_password(client, monkeypatch):
    _patch_auth_repos(monkeypatch, FakeUserRepo(), FakeTokenRepo())
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "1234567"},
    )
    assert response.status_code == 422
    assert "at least 8 characters" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_refresh_rejects_invalid_cookie_token(client, monkeypatch):
    _patch_auth_repos(monkeypatch, FakeUserRepo(), FakeTokenRepo(record=None))
    client.cookies.set("refresh_token", "not-found")
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.edge_case
def test_logout_without_refresh_cookie_is_still_no_content(client, monkeypatch):
    _patch_auth_repos(monkeypatch, FakeUserRepo(), FakeTokenRepo())
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204


class _RaiseUseCase:
    def __init__(self, *_args, **_kwargs):
        pass

    async def execute(self, *_args, **_kwargs):
        raise RuntimeError("boom")


class _RaiseHTTPUseCase:
    def __init__(self, *_args, **_kwargs):
        pass

    async def execute(self, *_args, **_kwargs):
        raise HTTPException(status_code=409, detail="conflict")


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_register_http_exception_branch_rolls_back_and_rethrows(client, monkeypatch):
    _patch_auth_repos(monkeypatch, FakeUserRepo(), FakeTokenRepo())
    monkeypatch.setattr(auth_routes, "RegisterUser", _RaiseHTTPUseCase)
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "password123"},
    )
    assert response.status_code == 409


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_register_generic_exception_branch_returns_400(client, monkeypatch):
    _patch_auth_repos(monkeypatch, FakeUserRepo(), FakeTokenRepo())
    monkeypatch.setattr(auth_routes, "RegisterUser", _RaiseUseCase)
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "err@example.com", "password": "password123"},
    )
    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_login_generic_exception_branch_returns_400(client, monkeypatch):
    _patch_auth_repos(monkeypatch, FakeUserRepo(), FakeTokenRepo())
    monkeypatch.setattr(auth_routes, "LoginUser", _RaiseUseCase)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "err@example.com", "password": "password123"},
    )
    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_refresh_generic_exception_branch_returns_400(client, monkeypatch):
    _patch_auth_repos(monkeypatch, FakeUserRepo(), FakeTokenRepo())
    monkeypatch.setattr(auth_routes, "RefreshToken", _RaiseUseCase)
    client.cookies.set("refresh_token", "token")
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_logout_exception_branch_still_returns_204(client, monkeypatch):
    _patch_auth_repos(monkeypatch, FakeUserRepo(), FakeTokenRepo())
    monkeypatch.setattr(auth_routes, "LogoutUser", _RaiseUseCase)
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204
