from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    INVALID_CURRENCY = "INVALID_CURRENCY"
    INSUFFICIENT_HOLDINGS = "INSUFFICIENT_HOLDINGS"
    INVALID_DATE_RANGE = "INVALID_DATE_RANGE"
    CSV_IMPORT_ERROR = "CSV_IMPORT_ERROR"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"


class ErrorDetail(BaseModel):
    code: ErrorCode
    message: str
    field: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class AppException(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        field: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        status_code: int = 400,
    ):
        self.code = code
        self.message = message
        self.field = field
        self.details = details
        self.status_code = status_code
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "field": self.field,
                "details": self.details or {},
            }
        }


class ValidationError(AppException):
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            field=field,
            details=details,
            status_code=422,
        )


class NotFoundError(AppException):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=f"{resource} with ID {resource_id} not found",
            status_code=404,
        )


class ConflictError(AppException):
    def __init__(self, message: str):
        super().__init__(code=ErrorCode.CONFLICT, message=message, status_code=409)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(code=ErrorCode.UNAUTHORIZED, message=message, status_code=401)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Access denied"):
        super().__init__(code=ErrorCode.FORBIDDEN, message=message, status_code=403)


class ExternalAPIError(AppException):
    def __init__(self, service: str, message: str):
        super().__init__(
            code=ErrorCode.EXTERNAL_API_ERROR,
            message=f"{service} API error: {message}",
            details={"service": service},
            status_code=503,
        )


class CsvImportError(AppException):
    def __init__(
        self,
        message: str,
        row_number: Optional[int] = None,
        field: Optional[str] = None,
    ):
        details = {}
        if row_number:
            details["row"] = row_number
        if field:
            details["field"] = field

        super().__init__(
            code=ErrorCode.CSV_IMPORT_ERROR,
            message=message,
            field=field,
            details=details if details else None,
            status_code=400,
        )
