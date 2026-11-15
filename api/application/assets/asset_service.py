import asyncio
from collections.abc import Callable
from datetime import date, timedelta

from domain.services.market_data import normalize_provider
from domain.value_objects.money import Currency


class AssetService:
    def __init__(self, unit_of_work_factory: Callable, gateway):
        self.unit_of_work_factory = unit_of_work_factory
        self.gateway = gateway

    async def search(self, query: str) -> list[dict]:
        if not query:
            raise ValueError("Search query must be at least 1 character")
        async with self.unit_of_work_factory() as unit_of_work:
            assets = await unit_of_work.repository.search_by_ticker(query, limit=10)
        return [
            {
                "id": str(asset.id),
                "ticker": asset.ticker,
                "name": asset.name,
                "asset_class": asset.asset_class.value,
                "currency": asset.currency.value,
            }
            for asset in assets
        ]

    async def validate(
        self, ticker: str, provider: str, currency: str, asset_class: str
    ) -> dict:
        selected = normalize_provider(provider)
        adapter = self.gateway.adapter(selected)
        if selected in {"ngnmarket", "ngxpulse"}:
            metadata = await adapter.get_asset_metadata(ticker, currency, asset_class)
        else:
            metadata = await adapter.get_asset_metadata(ticker, currency)
        return {
            "ticker": ticker,
            "provider": selected,
            "supported": metadata is not None,
        }

    async def history(
        self, ticker: str, start: date | None, end: date | None
    ) -> dict:
        end = end or date.today()
        start = start or (end - timedelta(days=365))
        async with self.unit_of_work_factory() as unit_of_work:
            asset = await unit_of_work.repository.get_by_ticker(ticker)
        provider = normalize_provider(
            asset.market_data_provider if asset else "yfinance"
        )
        history = await self.gateway.adapter(provider).get_price_history(
            ticker, start, end
        )
        return {
            "ticker": ticker,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "data": [
                {"date": day.isoformat(), "close": str(price / 100)}
                for day, price in history
            ],
        }

    async def batch_history(
        self, tickers: list[str], start: date | None, end: date | None
    ) -> dict:
        end = end or date.today()
        start = start or (end - timedelta(days=30))
        async with self.unit_of_work_factory() as unit_of_work:
            assets = await unit_of_work.repository.list_all()
        providers = {a.ticker.upper(): a.market_data_provider for a in assets}
        currencies = {a.ticker.upper(): a.currency for a in assets}

        async def fetch(ticker: str) -> dict:
            try:
                history = await self.gateway.adapter(
                    normalize_provider(providers.get(ticker.upper(), "yfinance"))
                ).get_price_history(ticker, start, end)
                currency = currencies.get(ticker.upper(), Currency.USD)
                fx_rates = (
                    await self.gateway.fx_history(currency.value, start, end)
                    if currency != Currency.USD
                    else {}
                )

                def convert(day, price):
                    rate = fx_rates.get(day)
                    if not rate and fx_rates:
                        nearest = min(fx_rates, key=lambda key: abs((key - day).days))
                        rate = fx_rates[nearest]
                    if not rate:
                        return str(price / 100)
                    converted = (
                        (price * 100) // (-rate)
                        if rate < 0
                        else (price * rate) // 100
                    )
                    return str(converted / 100)

                return {
                    "ticker": ticker,
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "data": [
                        {"date": day.isoformat(), "close": convert(day, price)}
                        for day, price in history
                    ],
                }
            except Exception:
                return {
                    "ticker": ticker,
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "data": [],
                }

        return {"results": await asyncio.gather(*(fetch(ticker) for ticker in tickers))}
