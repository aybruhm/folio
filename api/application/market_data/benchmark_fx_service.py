from collections.abc import Callable
from uuid import UUID

from application.analytics.benchmarks import list_catalog
from domain.value_objects.money import Currency


class BenchmarkFxService:
    def __init__(self, adapter_factory: Callable[[], object]):
        self.adapter_factory = adapter_factory

    def list_benchmarks(self) -> list[dict[str, str]]:
        return list_catalog()

    def add_benchmark(self, ticker: str, name: str) -> dict[str, str]:
        return {"ticker": ticker, "name": name}

    def delete_benchmark(self, benchmark_id: UUID) -> dict[str, str]:
        return {"status": "deleted"}

    async def get_fx_rates(self, currencies: list[str] | None) -> dict[str, str | None]:
        adapter = self.adapter_factory()
        requested = currencies or ["USD", "GBP", "EUR", "JPY"]
        rates = {}
        for currency in requested:
            try:
                rate = await adapter.get_current_rate(
                    Currency("USD"), Currency(currency)
                )
                rates[f"USD{currency}"] = str(rate / 100) if rate else None
            except Exception:
                rates[f"USD{currency}"] = None
        return rates
