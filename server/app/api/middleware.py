"""Request id, LAN access token, body-size cap, per-device rate limit on asks, request timeout and an access log
line. Order inside one middleware so every rejection uses the standard error format and carries the request id."""

from __future__ import annotations

import asyncio
import hmac
import logging
import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from starlette.responses import Response

from app.api.errors import error_response
from app.config import Settings
from app.core.context import request_id_var

log = logging.getLogger("kanakku.access")
OPEN_PATHS = {"/health", "/v1/health", "/ready", "/v1/ready", "/docs", "/openapi.json", "/docs/oauth2-redirect"}
ASK_PATHS = {"/cases", "/v1/cases"}
STREAM_SUFFIX = "/events"  # SSE: no request timeout


class RateLimiter:
    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        q = self.hits[key]
        while q and now - q[0] >= 60:
            q.popleft()
        if len(q) >= self.per_minute:
            return False
        q.append(now)
        return True


def max_body_bytes(s: Settings) -> int:
    return int((s.max_audio_mb + s.max_files * max(s.max_pdf_mb, s.max_image_mb) + 1) * 1024 * 1024)


def install(app: FastAPI, settings: Settings) -> None:
    token = settings.kanakku_token.get_secret_value()
    limiter = RateLimiter(settings.asks_per_minute)
    app.state.rate_limiter = limiter

    @app.middleware("http")
    async def _guard(request: Request, call_next):  # type: ignore[no-untyped-def]
        rid = request.headers.get("x-request-id", "")[:64] or uuid.uuid4().hex[:16]
        ctx = request_id_var.set(rid)
        t0 = time.perf_counter()
        path = request.url.path
        try:
            try:
                response = await _handle(request, call_next, path)
            except Exception as e:  # never a stack trace to the client
                log.exception("unhandled error: %s", type(e).__name__)
                response = error_response(
                    500, "internal_error", "Something went wrong on the server. Please try again."
                )
            response.headers["X-Request-ID"] = rid
            ms = round((time.perf_counter() - t0) * 1000, 1)
            extra = {"method": request.method, "path": path, "status": response.status_code, "ms": ms}
            log.info("%s %s -> %s", request.method, path, response.status_code, extra=extra)
            return response
        finally:
            request_id_var.reset(ctx)

    async def _handle(request: Request, call_next, path: str) -> Response:  # type: ignore[no-untyped-def]
        if token and path not in OPEN_PATHS:
            auth = request.headers.get("authorization", "")
            given = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
            if not given or not hmac.compare_digest(given.encode(), token.encode()):
                msg = "Missing or wrong access token. Copy it from the make up output into Settings."
                return error_response(401, "unauthorized", msg, {"WWW-Authenticate": "Bearer"})
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > max_body_bytes(settings):
            return error_response(413, "request_too_large", "The upload is too big.")
        if request.method == "POST" and path in ASK_PATHS:
            device = request.headers.get("x-device-id") or (request.client.host if request.client else "unknown")
            if not limiter.allow(device):
                msg = f"Too many questions at once (limit {settings.asks_per_minute} a minute). Please wait a moment."
                return error_response(429, "too_many_requests", msg, {"Retry-After": "30"})
        if path.endswith(STREAM_SUFFIX):
            return await call_next(request)
        try:
            return await asyncio.wait_for(call_next(request), timeout=settings.request_timeout_s)
        except TimeoutError:
            return error_response(504, "timeout", "This took too long. Please try again.")
