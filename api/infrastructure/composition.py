from application.auth.services import AuthService
from application.portfolio.portfolio_service import PortfolioService
from application.trades.trade_service import TradeService
from application.trades.csv_import_service import CsvImportService
from application.goals.goal_service import GoalService
from application.analytics.portfolio_analytics_service import PortfolioAnalyticsService
from infrastructure.db.postgres.auth_uow import AuthUnitOfWork
from infrastructure.db.postgres.portfolio_uow import PortfolioUnitOfWork
from infrastructure.db.postgres.trade_uow import TradeUnitOfWork
from infrastructure.db.postgres.csv_import_uow import CsvImportUnitOfWork
from infrastructure.db.postgres.goal_uow import GoalUnitOfWork
from infrastructure.db.postgres.portfolio_analytics_uow import (
    PortfolioAnalyticsUnitOfWork,
)
from infrastructure.market_data.benchmark_gateway import BenchmarkGateway


auth_service = AuthService(AuthUnitOfWork)
portfolio_service = PortfolioService(PortfolioUnitOfWork)
trade_service = TradeService(TradeUnitOfWork)
csv_import_service = CsvImportService(CsvImportUnitOfWork)
goal_service = GoalService(GoalUnitOfWork)
portfolio_analytics_service = PortfolioAnalyticsService(
    PortfolioAnalyticsUnitOfWork, BenchmarkGateway()
)
