from infrastructure.market_data.benchmark_cache import BenchmarkCache
from infrastructure.market_data.providers import (
    BENCHMARK_PROVIDERS,
    PROVIDER_CURRENCY,
    PROVIDER_LABELS,
    build_adapter,
    is_configured,
)


class BenchmarkGateway:
    providers = BENCHMARK_PROVIDERS
    provider_currencies = PROVIDER_CURRENCY
    provider_labels = PROVIDER_LABELS

    def __init__(self):
        self.cache = BenchmarkCache()

    def build_adapter(self, provider: str):
        return build_adapter(provider)

    def is_configured(self, adapter) -> bool:
        return is_configured(adapter)
