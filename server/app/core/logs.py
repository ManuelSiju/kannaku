"""Structured JSON logs to run/server.log (rotated 10 MB x 5), each line with the request id. Secrets (the Meta API
key, the LAN access token) are scrubbed from every message before it is written anywhere."""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from app.core.context import request_id

MAX_BYTES = 10 * 1024 * 1024
BACKUPS = 5
_HANDLER_TAG = "_kanakku"


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = getattr(record, "request_id", "") or request_id()
        return True


class RedactFilter(logging.Filter):
    """Replaces every secret (and its Bearer form) in the rendered message with ***."""

    def __init__(self, secrets: Iterable[str]) -> None:
        super().__init__()
        self.secrets = [s for s in secrets if s and len(s) >= 6]

    def scrub(self, text: str) -> str:
        for s in self.secrets:
            text = text.replace(s, "***")
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        if not self.secrets:
            return True
        msg = self.scrub(record.getMessage())
        record.msg, record.args = msg, None
        if record.exc_info and record.exc_info[1] is not None:
            record.exc_text = self.scrub(logging.Formatter().formatException(record.exc_info))
            record.exc_info = None
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", ""),
            "msg": record.getMessage(),
        }
        for key in ("method", "path", "status", "ms", "case_id"):
            if hasattr(record, key):
                out[key] = getattr(record, key)
        if record.exc_text or record.exc_info:
            out["exc"] = record.exc_text or self.formatException(record.exc_info)  # type: ignore[arg-type]
        return json.dumps(out, ensure_ascii=False)


def setup_logging(log_path: Path | None, secrets: Iterable[str] = (), level: int = logging.INFO) -> None:
    """Idempotent: replaces the handlers this function added before."""
    root = logging.getLogger()
    root.setLevel(level)
    for h in [h for h in root.handlers if getattr(h, _HANDLER_TAG, False)]:
        root.removeHandler(h)
        h.close()
    filters: list[logging.Filter] = [RequestIdFilter(), RedactFilter(secrets)]
    handlers: list[logging.Handler] = []
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"))
    handlers.append(console)
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(log_path, maxBytes=MAX_BYTES, backupCount=BACKUPS, encoding="utf-8")
        fh.setFormatter(JsonFormatter())
        handlers.append(fh)
    for h in handlers:
        setattr(h, _HANDLER_TAG, True)
        for f in filters:
            h.addFilter(f)
        root.addHandler(h)
    # uvicorn's own loggers go through the same handlers (and filters)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers, lg.propagate = [], True
