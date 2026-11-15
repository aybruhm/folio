from application.auth.services import AuthService
from application.portfolio.portfolio_service import PortfolioService
from application.trades.trade_service import TradeService
from application.trades.csv_import_service import CsvImportService
from infrastructure.db.postgres.auth_uow import AuthUnitOfWork
from infrastructure.db.postgres.portfolio_uow import PortfolioUnitOfWork
from infrastructure.db.postgres.trade_uow import TradeUnitOfWork
from infrastructure.db.postgres.csv_import_uow import CsvImportUnitOfWork


auth_service = AuthService(AuthUnitOfWork)
portfolio_service = PortfolioService(PortfolioUnitOfWork)
trade_service = TradeService(TradeUnitOfWork)
csv_import_service = CsvImportService(CsvImportUnitOfWork)
