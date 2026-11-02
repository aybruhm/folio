from abc import ABC, abstractmethod
from datetime import date, datetime
from uuid import UUID

from domain.entities.models import Asset, Goal, Portfolio, Trade, User
from domain.value_objects.money import AssetMetadata, Currency, TradeType


class IUserRepository(ABC):
    @abstractmethod
    async def create(self, email: str, hashed_password: str) -> User: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None: ...


class ITokenRepository(ABC):
    @abstractmethod
    async def create(
        self, user_id: UUID, token: str, family_id: UUID, expires_at: datetime
    ) -> None: ...

    @abstractmethod
    async def get_by_token(self, token: str) -> dict | None: ...

    @abstractmethod
    async def revoke(self, token: str) -> None: ...

    @abstractmethod
    async def revoke_family(self, family_id: UUID) -> None: ...


class IPortfolioRepository(ABC):
    @abstractmethod
    async def add(self, portfolio: Portfolio) -> None: ...

    @abstractmethod
    async def get_by_id(self, portfolio_id: UUID) -> Portfolio | None: ...

    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, include_archived: bool = False
    ) -> list[Portfolio]: ...

    @abstractmethod
    async def update(self, portfolio: Portfolio) -> None: ...

    @abstractmethod
    async def delete(self, portfolio_id: UUID) -> None: ...


class ITradeRepository(ABC):
    @abstractmethod
    async def add(self, trade: Trade) -> None: ...

    @abstractmethod
    async def get_by_id(self, trade_id: UUID) -> Trade | None: ...

    @abstractmethod
    async def list_by_portfolio(
        self,
        portfolio_id: UUID,
        ticker: str | None = None,
        trade_type: TradeType | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Trade], int]: ...

    @abstractmethod
    async def list_by_asset(self, asset_id: UUID) -> list[Trade]: ...

    @abstractmethod
    async def update(self, trade: Trade) -> None: ...

    @abstractmethod
    async def delete(self, trade_id: UUID) -> None: ...

    @abstractmethod
    async def delete_batch(self, trade_ids: list[UUID]) -> int: ...


class IAssetRepository(ABC):
    @abstractmethod
    async def add(self, asset: Asset) -> None: ...

    @abstractmethod
    async def get_by_ticker(self, ticker: str) -> Asset | None: ...

    @abstractmethod
    async def get_by_id(self, asset_id: UUID) -> Asset | None: ...

    @abstractmethod
    async def update_classification(
        self,
        asset_id: UUID,
        asset_class: str,
        currency: str,
        market_data_provider: str = "yfinance",
    ) -> None: ...

    @abstractmethod
    async def search_by_ticker(self, query: str, limit: int = 10) -> list[Asset]: ...

    @abstractmethod
    async def list_all(self) -> list[Asset]: ...


class IGoalRepository(ABC):
    @abstractmethod
    async def add(self, goal: Goal) -> None: ...

    @abstractmethod
    async def get_by_id(self, goal_id: UUID) -> Goal | None: ...

    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list[Goal]: ...

    @abstractmethod
    async def update(self, goal: Goal) -> None: ...

    @abstractmethod
    async def delete(self, goal_id: UUID) -> None: ...


class IAssetPricePort(ABC):
    @abstractmethod
    async def get_price_history(
        self, ticker: str, start: date, end: date
    ) -> list[tuple[date, int]]: ...

    @abstractmethod
    async def get_current_price(self, ticker: str) -> tuple[date, int]: ...

    @abstractmethod
    async def get_asset_metadata(self, ticker: str) -> AssetMetadata | None: ...


class IFxRatePort(ABC):
    @abstractmethod
    async def get_fx_rate(
        self, from_currency: Currency, to_currency: Currency, on_date: date
    ) -> int | None: ...

    @abstractmethod
    async def get_current_rate(
        self, from_currency: Currency, to_currency: Currency
    ) -> int | None: ...


class IPriceHistoryRepository(ABC):
    @abstractmethod
    async def add(
        self, asset_id: UUID, date: date, close: int, currency: Currency
    ) -> None: ...

    @abstractmethod
    async def get_history(
        self, asset_id: UUID, start: date, end: date
    ) -> list[tuple[date, int]]: ...

    @abstractmethod
    async def get_latest(self, asset_id: UUID) -> tuple[date, int] | None: ...


class IFxRateRepository(ABC):
    @abstractmethod
    async def add(
        self, from_currency: Currency, to_currency: Currency, date: date, rate: int
    ) -> None: ...

    @abstractmethod
    async def get_rate(
        self, from_currency: Currency, to_currency: Currency, date: date
    ) -> int | None: ...

    @abstractmethod
    async def get_latest_rate(
        self, from_currency: Currency, to_currency: Currency
    ) -> int | None: ...
