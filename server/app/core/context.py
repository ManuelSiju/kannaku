"""Per-request context (request id), readable from anywhere, including log records."""

from __future__ import annotations

from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("kanakku_request_id", default="")


def request_id() -> str:
    return request_id_var.get()
