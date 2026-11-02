from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from adapters.inbound.http.dependencies import get_current_user
from infrastructure.db.session import get_session
from main import app
from domain.entities.models import User


class FakeSession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


@pytest.fixture
def fake_session():
    return FakeSession()


@pytest.fixture
def fake_user():
    return User(
        id=uuid4(),
        email="user@example.com",
        hashed_password="hashed-password",
        is_active=True,
        created_at=datetime(2024, 1, 1, 12, 0),
    )


@pytest.fixture
def client(fake_session):
    app.dependency_overrides[get_session] = lambda: fake_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def authed_client(fake_session, fake_user):
    app.dependency_overrides[get_session] = lambda: fake_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class FakeValkey:
    """Just enough of Valkey for the benchmark cache: get, set and incr."""

    def __init__(self):
        self.store: dict[str, str] = {}
        self.expiries: dict[str, int | None] = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value
        self.expiries[key] = ex

    async def incr(self, key):
        self.store[key] = str(int(self.store.get(key, "0")) + 1)


@pytest.fixture(autouse=True)
def fake_valkey(monkeypatch):
    """No test reaches a real Valkey; the benchmark cache gets an in-memory one."""
    from adapters.outbound.market_data import benchmark_cache

    fake = FakeValkey()
    monkeypatch.setattr(benchmark_cache, "get_valkey_client", lambda: fake)
    return fake
