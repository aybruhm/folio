from datetime import datetime
from uuid import uuid4

import pytest
from jose import JWTError

from adapters.inbound.http import dependencies
from domain.entities.models import User


class FakeUserRepository:
    def __init__(self, user=None):
        self.user = user

    async def get_by_id(self, user_id):
        return self.user


def _patch_dependency_repo(monkeypatch, user=None):
    monkeypatch.setattr(dependencies, "UserRepository", lambda session: FakeUserRepository(user))


@pytest.mark.integration
@pytest.mark.grumpy_path
@pytest.mark.parametrize(
    "decoded_payload,error_cls",
    [
        (None, JWTError),
        ({}, None),
        ({"sub": "not-a-uuid"}, None),
    ],
)
def test_get_current_user_rejects_bad_token_payload(client, monkeypatch, decoded_payload, error_cls):
    if error_cls is not None:
        monkeypatch.setattr(
            dependencies,
            "decode_access_token",
            lambda token: (_ for _ in ()).throw(error_cls("bad token")),
        )
    else:
        monkeypatch.setattr(dependencies, "decode_access_token", lambda token: decoded_payload)
    _patch_dependency_repo(monkeypatch, user=None)
    client.cookies.set("access_token", "token")

    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_get_current_user_rejects_missing_or_inactive_user(client, monkeypatch):
    active_payload = {"sub": str(uuid4())}
    monkeypatch.setattr(dependencies, "decode_access_token", lambda token: active_payload)
    _patch_dependency_repo(monkeypatch, user=None)
    client.cookies.set("access_token", "token")

    missing = client.get("/api/v1/auth/me")
    assert missing.status_code == 401

    inactive = User(
        id=uuid4(),
        email="inactive@example.com",
        hashed_password="hashed",
        is_active=False,
        created_at=datetime(2024, 1, 1, 12, 0),
    )
    _patch_dependency_repo(monkeypatch, user=inactive)
    inactive_resp = client.get("/api/v1/auth/me")
    assert inactive_resp.status_code == 401


@pytest.mark.integration
@pytest.mark.happy_path
def test_get_current_user_returns_active_user(client, monkeypatch):
    user = User(
        id=uuid4(),
        email="active@example.com",
        hashed_password="hashed",
        is_active=True,
        created_at=datetime(2024, 1, 1, 12, 0),
    )
    monkeypatch.setattr(dependencies, "decode_access_token", lambda token: {"sub": str(user.id)})
    _patch_dependency_repo(monkeypatch, user=user)
    client.cookies.set("access_token", "token")

    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "active@example.com"
