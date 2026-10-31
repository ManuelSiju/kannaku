"""One error format everywhere: {"error": {"code", "message", "request_id"}}. No stack traces reach clients."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.context import request_id

log = logging.getLogger("kanakku.api")

CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "too_large",
    415: "unsupported_type",
    422: "invalid_request",
    429: "too_many_requests",
    500: "internal_error",
    503: "unavailable",
    504: "timeout",
}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.status, self.code, self.message, self.headers = status, code, message, headers


def error_body(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message, "request_id": request_id()}}


def error_response(status: int, code: str, message: str, headers: dict[str, str] | None = None) -> JSONResponse:
    rid = request_id()
    h = {"X-Request-ID": rid} if rid else {}
    return JSONResponse(error_body(code, message), status_code=status, headers=h | (headers or {}))


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(_: Request, e: ApiError) -> JSONResponse:
        return error_response(e.status, e.code, e.message, e.headers)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException) -> JSONResponse:
        message = e.detail if isinstance(e.detail, str) else "request failed"
        return error_response(e.status_code, CODES.get(e.status_code, "error"), message, getattr(e, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def _invalid(_: Request, e: RequestValidationError) -> JSONResponse:
        parts = [
            f"{'.'.join(str(x) for x in err.get('loc', [])[1:]) or 'body'}: {err.get('msg', '')}" for err in e.errors()
        ]
        return error_response(422, "invalid_request", "; ".join(parts)[:500] or "invalid request")

    @app.exception_handler(Exception)
    async def _crash(_: Request, e: Exception) -> JSONResponse:
        log.exception("unhandled error: %s", type(e).__name__)
        return error_response(500, "internal_error", "Something went wrong on the server. Please try again.")


__all__ = ["ApiError", "HTTPException", "error_response", "install"]
