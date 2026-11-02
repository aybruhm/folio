import json
import logging

from infrastructure.cache.valkey_client import get_valkey_client
from infrastructure.config import settings

logger = logging.getLogger(__name__)

_PREFIX = "folio:benchmark"
_VERSION_KEY = f"{_PREFIX}:version"


class BenchmarkCache:
    """Valkey cache for finished benchmark comparisons.

    Entries live for ``BENCHMARK_CACHE_TTL`` (35 minutes). Every key carries a
    version number; bumping it with :meth:`invalidate` orphans all entries at
    once, which is how a trade or portfolio change drops stale results. A
    Valkey outage is a cache miss, never an error.
    """

    def __init__(self, ttl_seconds: int | None = None) -> None:
        self._ttl = (
            ttl_seconds if ttl_seconds is not None else settings.BENCHMARK_CACHE_TTL
        )

    @property
    def ttl(self) -> int:
        return self._ttl

    async def _version(self) -> str:
        try:
            return await get_valkey_client().get(_VERSION_KEY) or "0"
        except Exception as exc:
            logger.warning("Valkey benchmark version read failed: %s", exc)
            return "0"

    async def key(self, *parts: str) -> str:
        return ":".join([_PREFIX, await self._version(), *parts])

    async def get(self, key: str) -> dict | None:
        try:
            raw = await get_valkey_client().get(key)
            return json.loads(raw) if raw else None
        except Exception as exc:
            logger.warning("Valkey benchmark get failed: %s", exc)
            return None

    async def set(self, key: str, value: dict) -> None:
        try:
            await get_valkey_client().set(key, json.dumps(value), ex=self._ttl)
        except Exception as exc:
            logger.warning("Valkey benchmark set failed: %s", exc)

    async def invalidate(self) -> None:
        try:
            await get_valkey_client().incr(_VERSION_KEY)
        except Exception as exc:
            logger.warning("Valkey benchmark invalidate failed: %s", exc)
