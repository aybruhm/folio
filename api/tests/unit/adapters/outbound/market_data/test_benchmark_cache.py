import pytest

from adapters.outbound.market_data import benchmark_cache
from adapters.outbound.market_data.benchmark_cache import BenchmarkCache
from application.analytics.benchmarks import (
    benchmark_currency,
    benchmark_provider,
    list_catalog,
)


class DownValkey:
    async def get(self, key):
        raise ConnectionError("valkey is down")

    async def set(self, *args, **kwargs):
        raise ConnectionError("valkey is down")

    async def incr(self, key):
        raise ConnectionError("valkey is down")


@pytest.mark.asyncio
@pytest.mark.edge_case
async def test_a_valkey_outage_is_a_miss_not_an_error(monkeypatch):
    monkeypatch.setattr(benchmark_cache, "get_valkey_client", lambda: DownValkey())
    cache = BenchmarkCache()

    key = await cache.key("a", "b")
    assert await cache.get(key) is None
    await cache.set(key, {"x": 1})
    await cache.invalidate()


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_invalidate_orphans_existing_entries(monkeypatch):
    class Memory:
        def __init__(self):
            self.data = {}

        async def get(self, key):
            return self.data.get(key)

        async def set(self, key, value, ex=None):
            self.data[key] = value

        async def incr(self, key):
            self.data[key] = str(int(self.data.get(key, "0")) + 1)

    memory = Memory()
    monkeypatch.setattr(benchmark_cache, "get_valkey_client", lambda: memory)
    cache = BenchmarkCache(ttl_seconds=60)

    key = await cache.key("u", "all")
    await cache.set(key, {"x": 1})
    assert await cache.get(key) == {"x": 1}

    await cache.invalidate()

    assert await cache.key("u", "all") != key
    assert await cache.get(await cache.key("u", "all")) is None
    assert cache.ttl == 60


@pytest.mark.unit
@pytest.mark.happy_path
def test_catalog_providers_and_currencies():
    assert benchmark_provider("^GSPC") == "yfinance"
    assert benchmark_provider("NGX:ASI") == "ngxpulse"
    assert benchmark_provider("anything-else") == "yfinance"
    assert benchmark_currency("NGX:ASI") == "NGN"
    assert benchmark_currency("^GSPC") is None
    assert all("provider" in entry for entry in list_catalog())
