from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from dataclasses import dataclass

from domain.value_objects.money import Currency, TradeType

@dataclass
class CreatePortfolioRequest:
    name: str
    base_currency: Currency
    description: Optional[str] = None

@dataclass
class CreateTradeRequest:
    portfolio_id: UUID
    ticker: str
    trade_type: TradeType
    trade_date: datetime
    quantity: Decimal
    price: Decimal
    trade_currency: Currency
    fees: Decimal = Decimal('0')
    notes: Optional[str] = None

@dataclass
class CreateGoalRequest:
    portfolio_id: UUID
    name: str
    target_net_worth: Decimal
    target_net_worth_currency: Currency
    target_date: date
    monthly_savings: Decimal
    monthly_savings_currency: Currency
    expected_annual_return: Decimal

class IPortfolioUseCase(ABC):
    @abstractmethod
    async def create_portfolio(self, request: CreatePortfolioRequest) -> UUID: ...
    
    @abstractmethod
    async def get_portfolio(self, portfolio_id: UUID) -> dict: ...
    
    @abstractmethod
    async def list_portfolios(self) -> List[dict]: ...
    
    @abstractmethod
    async def update_portfolio(
        self, portfolio_id: UUID, name: Optional[str] = None, description: Optional[str] = None
    ) -> None: ...
    
    @abstractmethod
    async def delete_portfolio(self, portfolio_id: UUID) -> None: ...

class ITradeUseCase(ABC):
    @abstractmethod
    async def create_trade(self, request: CreateTradeRequest) -> UUID: ...
    
    @abstractmethod
    async def get_trade(self, trade_id: UUID) -> dict: ...
    
    @abstractmethod
    async def list_trades(
        self,
        portfolio_id: Optional[UUID] = None,
        ticker: Optional[str] = None,
        trade_type: Optional[TradeType] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[dict], int]: ...
    
    @abstractmethod
    async def update_trade(self, trade_id: UUID, request: CreateTradeRequest) -> None: ...
    
    @abstractmethod
    async def delete_trade(self, trade_id: UUID) -> None: ...

class IAnalyticsUseCase(ABC):
    @abstractmethod
    async def get_holdings(
        self, portfolio_id: UUID, in_currency: Optional[Currency] = None
    ) -> List[dict]: ...
    
    @abstractmethod
    async def calculate_performance(
        self, portfolio_id: UUID, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> dict: ...
    
    @abstractmethod
    async def get_allocation(
        self, portfolio_id: UUID, group_by: str = 'asset_class'
    ) -> List[dict]: ...
    
    @abstractmethod
    async def get_benchmark_comparison(
        self, portfolio_id: UUID, benchmark_tickers: List[str], start_date: Optional[date] = None
    ) -> dict: ...

class IGoalUseCase(ABC):
    @abstractmethod
    async def create_goal(self, request: CreateGoalRequest) -> UUID: ...
    
    @abstractmethod
    async def get_goal(self, goal_id: UUID) -> dict: ...
    
    @abstractmethod
    async def list_goals(self, portfolio_id: UUID) -> List[dict]: ...
    
    @abstractmethod
    async def update_goal(self, goal_id: UUID, request: CreateGoalRequest) -> None: ...
    
    @abstractmethod
    async def delete_goal(self, goal_id: UUID) -> None: ...
    
    @abstractmethod
    async def get_projection(self, goal_id: UUID) -> dict: ...

class ICsvImportUseCase(ABC):
    @abstractmethod
    async def preview_csv(self, file_content: bytes, filename: str) -> dict: ...
    
    @abstractmethod
    async def validate_mapping(
        self, file_content: bytes, filename: str, mapping: dict, date_format: str
    ) -> dict: ...
    
    @abstractmethod
    async def confirm_import(
        self, file_content: bytes, filename: str, mapping: dict, date_format: str,
        portfolio_id: UUID, profile_name: Optional[str] = None
    ) -> dict: ...
