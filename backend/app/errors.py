"""ErrorHandler + common error codes (U1). Structured error body: {error:{code,message,details}}."""
from enum import Enum

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    TOO_MANY_ATTEMPTS = "TOO_MANY_ATTEMPTS"
    INTERNAL = "INTERNAL"


# ErrorCode -> HTTP status mapping (business-rules.md §8).
_STATUS = {
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.TOO_MANY_ATTEMPTS: 429,
    ErrorCode.INTERNAL: 500,
}


class AppError(Exception):
    """Domain/application error carrying a structured code. Raised by any unit; mapped by ErrorHandler."""

    def __init__(self, code: ErrorCode, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)

    @property
    def status_code(self) -> int:
        return _STATUS.get(self.code, 500)


def _body(code: ErrorCode, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code.value, "message": message, "details": details}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content=_body(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=_body(ErrorCode.VALIDATION_ERROR, "요청 검증에 실패했습니다.", {"errors": exc.errors()}),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        return JSONResponse(status_code=500, content=_body(ErrorCode.INTERNAL, "서버 내부 오류가 발생했습니다."))
