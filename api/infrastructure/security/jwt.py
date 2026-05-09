from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import jwt

from infrastructure.config import settings

ALGORITHM = "HS256"


def create_access_token(user_id: UUID, email: str) -> tuple[str, datetime]:
    expires_at = datetime.now() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expires_at,
        "iat": datetime.now(),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    return token, expires_at


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
