import logging
from typing import Optional

import valkey.asyncio as valkey

from infrastructure.config import settings

logger = logging.getLogger(__name__)

_client: Optional[valkey.Valkey] = None


def get_valkey_client() -> valkey.Valkey:
    """Return the shared Valkey client, creating it if necessary.

    If ``REDIS_URL`` is not configured a dummy client pointing at
    ``redis://localhost:6379/0`` is returned — the caller is responsible
    for handling connection errors gracefully.
    """
    global _client

    if _client is not None:
        return _client

    url = settings.REDIS_URL
    logger.info("Connecting Valkey client to %s", url)

    _client = valkey.Valkey.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30,
    )
    return _client


async def close_valkey_client() -> None:
    """Gracefully close the shared Valkey connection."""
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        except Exception as exc:
            logger.warning("Error closing Valkey client: %s", exc)
        finally:
            _client = None
            logger.info("Valkey client closed")
