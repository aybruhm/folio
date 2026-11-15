from application.auth.services import AuthService
from application.portfolio.portfolio_service import PortfolioService
from infrastructure.db.postgres.auth_uow import AuthUnitOfWork
from infrastructure.db.postgres.portfolio_uow import PortfolioUnitOfWork


auth_service = AuthService(AuthUnitOfWork)
portfolio_service = PortfolioService(PortfolioUnitOfWork)
