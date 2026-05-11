from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status

from application.auth import use_cases
from application.auth.use_cases import LoginUser, LogoutUser, RefreshToken, RegisterUser
from domain.entities.models import User


class FakeUserRepo:
    def __init__(self, *, users_by_email=None, users_by_id=None):
        self.users_by_email = users_by_email or {}
        self.users_by_id = users_by_id or {}
        self.created = []

    async def get_by_email(self, email: str):
        return self.users_by_email.get(email)

    async def create(self, email: str, hashed_password: str):
        user = User(
            id=uuid4(),
            email=email,
            hashed_password=hashed_password,
            is_active=True,
            created_at=datetime(2024, 1, 1, 12, 0),
        )
        self.created.append((email, hashed_password, user))
        self.users_by_email[email] = user
        self.users_by_id[user.id] = user
        return user

    async def get_by_id(self, user_id: UUID):
        return self.users_by_id.get(user_id)


class FakeTokenRepo:
    def __init__(self, *, tokens_by_value=None):
        self.tokens_by_value = tokens_by_value or {}
        self.created = []
        self.revoked = []
        self.revoked_families = []

    async def create(self, user_id, token, family_id, expires_at):
        self.created.append((user_id, token, family_id, expires_at))
        self.tokens_by_value[token] = {
            "user_id": user_id,
            "token": token,
            "family_id": family_id,
            "is_revoked": False,
            "expires_at": expires_at,
        }

    async def get_by_token(self, token: str):
        return self.tokens_by_value.get(token)

    async def revoke(self, token: str):
        self.revoked.append(token)
        if token in self.tokens_by_value:
            self.tokens_by_value[token]["is_revoked"] = True

    async def revoke_family(self, family_id):
        self.revoked_families.append(family_id)


def _patch_tokens(
    monkeypatch, *, refresh_token: UUID, family_id: UUID, access_token: str
):
    values = iter([refresh_token, family_id])
    monkeypatch.setattr(use_cases, "uuid4", lambda: next(values))
    monkeypatch.setattr(
        use_cases,
        "create_access_token",
        lambda user_id, email: (access_token, datetime(2024, 1, 1, 12, 0)),
    )


def _user(email: str = "user@example.com", *, is_active: bool = True) -> User:
    return User(
        id=uuid4(),
        email=email,
        hashed_password="hashed-password",
        is_active=is_active,
        created_at=datetime(2024, 1, 1, 12, 0),
    )


@pytest.mark.asyncio
async def test_register_user_creates_user_and_token(monkeypatch):
    user_repo = FakeUserRepo()
    token_repo = FakeTokenRepo()
    _patch_tokens(
        monkeypatch,
        refresh_token=UUID("11111111-1111-1111-1111-111111111111"),
        family_id=UUID("22222222-2222-2222-2222-222222222222"),
        access_token="access-token",
    )
    monkeypatch.setattr(
        use_cases, "_hash_password", lambda password: f"hashed:{password}"
    )
    monkeypatch.setattr(
        use_cases.settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7, raising=False
    )

    user, access_token, refresh_token = await RegisterUser(
        user_repo, token_repo
    ).execute("user@example.com", "password123")

    assert user.email == "user@example.com"
    assert access_token == "access-token"
    assert refresh_token == "11111111-1111-1111-1111-111111111111"
    assert user_repo.created[0][1] == "hashed:password123"
    assert token_repo.created[0][2] == UUID("22222222-2222-2222-2222-222222222222")
    assert token_repo.created[0][3] > datetime.now()


@pytest.mark.asyncio
async def test_register_user_rejects_duplicate_email():
    existing = _user()
    user_repo = FakeUserRepo(users_by_email={existing.email: existing})
    token_repo = FakeTokenRepo()

    with pytest.raises(HTTPException) as exc:
        await RegisterUser(user_repo, token_repo).execute(existing.email, "password123")

    assert exc.value.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_login_user_returns_tokens_for_valid_credentials(monkeypatch):
    user = _user()
    user_repo = FakeUserRepo(users_by_email={user.email: user})
    token_repo = FakeTokenRepo()
    _patch_tokens(
        monkeypatch,
        refresh_token=UUID("33333333-3333-3333-3333-333333333333"),
        family_id=UUID("44444444-4444-4444-4444-444444444444"),
        access_token="login-access-token",
    )
    monkeypatch.setattr(use_cases, "_verify_password", lambda password, hashed: True)
    monkeypatch.setattr(
        use_cases.settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7, raising=False
    )

    result = await LoginUser(user_repo, token_repo).execute(user.email, "password123")

    assert result[0] == user
    assert result[1] == "login-access-token"
    assert result[2] == "33333333-3333-3333-3333-333333333333"
    assert token_repo.created[0][2] == UUID("44444444-4444-4444-4444-444444444444")


@pytest.mark.asyncio
async def test_login_user_rejects_invalid_credentials(monkeypatch):
    user = _user()
    user_repo = FakeUserRepo(users_by_email={user.email: user})
    token_repo = FakeTokenRepo()
    monkeypatch.setattr(use_cases, "_verify_password", lambda password, hashed: False)

    with pytest.raises(HTTPException) as exc:
        await LoginUser(user_repo, token_repo).execute(user.email, "wrong-password")

    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_refresh_token_rotates_session(monkeypatch):
    user = _user()
    token_value = "refresh-token"
    family_id = UUID("55555555-5555-5555-5555-555555555555")
    user_repo = FakeUserRepo(users_by_id={user.id: user})
    token_repo = FakeTokenRepo(
        tokens_by_value={
            token_value: {
                "user_id": user.id,
                "token": token_value,
                "family_id": family_id,
                "is_revoked": False,
                "expires_at": datetime.now() + timedelta(days=1),
            }
        }
    )
    _patch_tokens(
        monkeypatch,
        refresh_token=UUID("66666666-6666-6666-6666-666666666666"),
        family_id=UUID("77777777-7777-7777-7777-777777777777"),
        access_token="rotated-access-token",
    )

    result = await RefreshToken(user_repo, token_repo).execute(token_value)

    assert result[0] == user
    assert result[1] == "rotated-access-token"
    assert result[2] == "66666666-6666-6666-6666-666666666666"
    assert token_repo.revoked == [token_value]
    assert token_repo.created[0][2] == family_id


@pytest.mark.asyncio
async def test_refresh_token_rejects_missing_record():
    user_repo = FakeUserRepo()
    token_repo = FakeTokenRepo()

    with pytest.raises(HTTPException) as exc:
        await RefreshToken(user_repo, token_repo).execute("missing")

    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_refresh_token_revokes_family_on_reuse():
    user = _user()
    family_id = UUID("88888888-8888-8888-8888-888888888888")
    user_repo = FakeUserRepo(users_by_id={user.id: user})
    token_repo = FakeTokenRepo(
        tokens_by_value={
            "reused": {
                "user_id": user.id,
                "token": "reused",
                "family_id": family_id,
                "is_revoked": True,
                "expires_at": datetime.now() + timedelta(days=1),
            }
        }
    )

    with pytest.raises(HTTPException) as exc:
        await RefreshToken(user_repo, token_repo).execute("reused")

    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert token_repo.revoked_families == [family_id]


@pytest.mark.asyncio
async def test_refresh_token_rejects_expired_token():
    user = _user()
    user_repo = FakeUserRepo(users_by_id={user.id: user})
    token_repo = FakeTokenRepo(
        tokens_by_value={
            "expired": {
                "user_id": user.id,
                "token": "expired",
                "family_id": UUID("99999999-9999-9999-9999-999999999999"),
                "is_revoked": False,
                "expires_at": datetime.now() - timedelta(seconds=1),
            }
        }
    )

    with pytest.raises(HTTPException) as exc:
        await RefreshToken(user_repo, token_repo).execute("expired")

    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_refresh_token_rejects_inactive_user():
    user = _user(is_active=False)
    family_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    user_repo = FakeUserRepo(users_by_id={user.id: user})
    token_repo = FakeTokenRepo(
        tokens_by_value={
            "inactive": {
                "user_id": user.id,
                "token": "inactive",
                "family_id": family_id,
                "is_revoked": False,
                "expires_at": datetime.now() + timedelta(days=1),
            }
        }
    )

    with pytest.raises(HTTPException) as exc:
        await RefreshToken(user_repo, token_repo).execute("inactive")

    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert token_repo.revoked == ["inactive"]


@pytest.mark.asyncio
async def test_logout_user_revokes_token_when_present():
    token_repo = FakeTokenRepo()

    await LogoutUser(token_repo).execute("logout-token")

    assert token_repo.revoked == ["logout-token"]


@pytest.mark.asyncio
async def test_logout_user_ignores_missing_token():
    token_repo = FakeTokenRepo()

    await LogoutUser(token_repo).execute(None)

    assert token_repo.revoked == []


def test_hash_password_and_verify_password_round_trip():
    hashed = use_cases._hash_password("password123")

    assert hashed != "password123"
    assert use_cases._verify_password("password123", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = use_cases._hash_password("password123")

    assert use_cases._verify_password("wrong-password", hashed) is False
