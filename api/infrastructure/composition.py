from application.auth.services import AuthService
from infrastructure.db.postgres.auth_uow import AuthUnitOfWork


auth_service = AuthService(AuthUnitOfWork)
