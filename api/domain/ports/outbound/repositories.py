from abc import ABC, abstractmethod
from datetime import date
from typing import Optional, List
from uuid import UUID

from domain.entities.models import Portfolio, Trade, Asset, Goal, FxRate, Holding
from domain.value_objects.money import Currency, AssetMetadata, TradeType


class IPortfolioRepository(ABC):
    @abstractmethod
    async def add(self, portfolio: Portfolio) -> None: ...

    @abstractmethod
    async def get_by_id(self, portfolio_id: UUID) -> Optional[Portfolio]: ...

    @abstractmethod
    async def list_all(self) -> List[Portfolio]: ...

    @abstractmethod
    async def update(self, portfolio: Portfolio) -> None: ...

    @abstractmethod
    async def delete(self, portfolio_id: UUID) -> None: ...


class ITradeRepository(ABC):
    @abstractmethod
    async def add(self, trade: Trade) -> None: ...

    @abstractmethod
    async def get_by_id(self, trade_id: UUID) -> Optional[Trade]: ...

    @abstractmethod
    async def list_by_portfolio(
        self, portfolio_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[List[Trade], int]: ...

    @abstractmethod
    async def list_by_asset(self, asset_id: UUID) -> List[Trade]: ...

    @abstractmethod
    async def update(self, trade: Trade) -> None: ...

    @abstractmethod
    async def delete(self, trade_id: UUID) -> None: ...


class IAssetRepository(ABC):
    @abstractmethod
    async def add(self, asset: Asset) -> None: ...

    @abstractmethod
    async def get_by_ticker(self, ticker: str) -> Optional[Asset]: ...

    @abstractmethod
    async def get_by_id(self, asset_id: UUID) -> Optional[Asset]: ...

    @abstractmethod
    async def search_by_ticker(self, query: str, limit: int = 10) -> List[Asset]: ...


class IGoalRepository(ABC):
    @abstractmethod
    async def add(self, goal: Goal) -> None: ...

    @abstractmethod
    async def get_by_id(self, goal_id: UUID) -> Optional[Goal]: ...

    @abstractmethod
    async def list_by_portfolio(self, portfolio_id: UUID) -> List[Goal]: ...

    @abstractmethod
    async def update(self, goal: Goal) -> None: ...

    @abstractmethod
    async def delete(self, goal_id: UUID) -> None: ...


class IAssetPricePort(ABC):
    @abstractmethod
    async def get_price_history(
        self, ticker: str, start: date, end: date
    ) -> List[tuple[date, int]]: ...

    @abstractmethod
    async def get_current_price(self, ticker: str) -> tuple[date, int]: ...

    @abstractmethod
    async def get_asset_metadata(self, ticker: str) -> Optional[AssetMetadata]: ...


class IFxRatePort(ABC):
    @abstractmethod
    async def get_fx_rate(
        self, from_currency: Currency, to_currency: Currency, date: date
    ) -> Optional[int]: ...

    @abstractmethod
    async def get_current_rate(
        self, from_currency: Currency, to_currency: Currency
    ) -> Optional[int]: ...


class IPriceHistoryRepository(ABC):
    @abstractmethod
    async def add(
        self, asset_id: UUID, date: date, close: int, currency: Currency
    ) -> None: ...

    @abstractmethod
    async def get_history(
        self, asset_id: UUID, start: date, end: date
    ) -> List[tuple[date, int]]: ...

    @abstractmethod
    async def get_latest(self, asset_id: UUID) -> Optional[tuple[date, int]]: ...


class IFxRateRepository(ABC):
    @abstractmethod
    async def add(
        self, from_currency: Currency, to_currency: Currency, date: date, rate: int
    ) -> None: ...

    @abstractmethod
    async def get_rate(
        self, from_currency: Currency, to_currency: Currency, date: date
    ) -> Optional[int]: ...

    @abstractmethod
    async def get_latest_rate(
        self, from_currency: Currency, to_currency: Currency
    ) -> Optional[int]: ...
