import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.infrastructure.errors import AppException, ErrorCode

logger = logging.getLogger(__name__)


class ErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except AppException as e:
            logger.warning(
                f"App error: {e.code.value}",
                extra={
                    "code": e.code.value,
                    "message": e.message,
                    "path": request.url.path,
                    "method": request.method
                }
            )
            return JSONResponse(
                status_code=e.status_code,
                content=e.to_dict()
            )
        except ValueError as e:
            logger.warning(f"Validation error: {str(e)}", extra={"path": request.url.path})
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": ErrorCode.VALIDATION_ERROR.value,
                        "message": str(e),
                        "field": None,
                        "details": {}
                    }
                }
            )
        except Exception as e:
            logger.error(
                f"Unexpected error: {str(e)}",
                exc_info=True,
                extra={"path": request.url.path, "method": request.method}
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": ErrorCode.INTERNAL_ERROR.value,
                        "message": "An unexpected error occurred",
                        "field": None,
                        "details": {}
                    }
                }
            )
