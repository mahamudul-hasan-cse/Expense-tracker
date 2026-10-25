"""Uniform error responses.

Every error body has the same shape:
    {"error": {"code": "not_found", "message": "Expense not found",
               "details": [...] | null, "request_id": "..."}}
"""
import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.logging_config import request_id_var

logger = logging.getLogger("app.errors")

_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    503: "service_unavailable",
}


def error_response(status_code: int, message: str, details=None, headers=None) -> JSONResponse:
    code = _CODES.get(status_code) or HTTPStatus(status_code).phrase.lower().replace(" ", "_")
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "request_id": request_id_var.get(),
            }
        },
        headers=headers,
    )


async def _http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else HTTPStatus(exc.status_code).phrase
    return error_response(exc.status_code, message, headers=getattr(exc, "headers", None))


async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {
            # e.g. ["body", "amount"] -> "amount"; keep "query.page" style for non-body params
            "field": ".".join(str(p) for p in err["loc"][1:]) if err["loc"][:1] == ("body",) else ".".join(str(p) for p in err["loc"]),
            "message": err["msg"].removeprefix("Value error, "),
        }
        for err in exc.errors()
    ]
    message = "; ".join(f"{d['field']}: {d['message']}" if d["field"] else d["message"] for d in details)
    return error_response(422, message or "Invalid request", details)


async def _integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
    # Usually a race on a unique constraint that the routers already check for
    logger.warning("integrity error", extra={"path": request.url.path, "error": str(exc.orig)})
    return error_response(409, "This change conflicts with existing data")


async def _rate_limited(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return error_response(429, f"Too many requests. Limit: {exc.detail}. Please try again later.")


async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    # Full traceback goes to the logs only, never to the client
    logger.exception("unhandled error", extra={"path": request.url.path, "method": request.method})
    return error_response(500, "Something went wrong. Please try again.")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_exception)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(IntegrityError, _integrity_error)
    app.add_exception_handler(RateLimitExceeded, _rate_limited)
    app.add_exception_handler(Exception, _unhandled)
