from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple


class PriceCache:
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds
        self._cache: Dict[str, Tuple[int, datetime]] = {}

    def get(self, ticker: str) -> Optional[int]:
        if ticker not in self._cache:
            return None

        price, timestamp = self._cache[ticker]
        if datetime.utcnow() - timestamp > timedelta(seconds=self.ttl):
            del self._cache[ticker]
            return None

        return price

    def set(self, ticker: str, price: int) -> None:
        self._cache[ticker] = (price, datetime.utcnow())

    def invalidate(self, ticker: str) -> None:
        if ticker in self._cache:
            del self._cache[ticker]

    def clear(self) -> None:
        self._cache.clear()

    def size(self) -> int:
        return len(self._cache)
