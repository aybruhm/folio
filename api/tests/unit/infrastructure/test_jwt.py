from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from infrastructure.config import settings
from infrastructure.security.jwt import create_access_token, decode_access_token


@pytest.mark.smoke
def test_create_and_decode_access_token_round_trips_claims(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret", raising=False)
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30, raising=False)

    user_id = uuid4()
    token, expires_at = create_access_token(user_id, "user@example.com")
    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["email"] == "user@example.com"
    assert payload["exp"] > payload["iat"]
    assert (
        datetime.fromtimestamp(payload["exp"]) - datetime.fromtimestamp(payload["iat"])
    ) <= timedelta(minutes=30, seconds=1)
    assert expires_at - datetime.now() <= timedelta(minutes=30, seconds=1)
