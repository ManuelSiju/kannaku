"""Kanakku FastAPI app."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import ValidationError

from app.api import alerts, cases, errors, families, health, items, middleware
from app.config import VERSION, Settings, get_settings
from app.core.logs import setup_logging
from app.db.backup import backup_daily

log = logging.getLogger("kanakku")
BACKUP_CHECK_S = 3600


def load_settings() -> Settings:
    """Validate the configuration once at start-up; on a mistake print what is wrong (never the values, which may
    hold secrets) and exit."""
    try:
        return get_settings()
    except ValidationError as e:
        lines = [f"  {'.'.join(str(x) for x in err['loc']) or 'settings'}: {err['msg']}" for err in e.errors()]
        print("✘ Bad configuration in .env / .env.local:\n" + "\n".join(lines), file=sys.stderr)
        raise SystemExit(1) from None


async def _backups(s: Settings) -> None:
    while True:
        try:
            if made := await asyncio.to_thread(backup_daily, s.db_path, s.backup_dir, s.backups_kept):
                log.info("database backup written: %s", made.name)
        except Exception as e:  # a failed backup must not stop the server
            log.warning("database backup failed: %s", e)
        await asyncio.sleep(BACKUP_CHECK_S)


async def _drain(grace_s: float) -> None:
    """Graceful shutdown: let in-flight background asks finish (up to grace_s), then cancel the rest."""
    pending = [t for t in cases.background_tasks() if not t.done()]
    if not pending:
        return
    log.info("waiting up to %.0fs for %d running ask(s)", grace_s, len(pending))
    _, still = await asyncio.wait(pending, timeout=grace_s)
    for t in still:
        t.cancel()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    s = load_settings()
    setup_logging(s.log_path, secrets=[s.meta_api_key.get_secret_value(), s.kanakku_token.get_secret_value()])
    from app.api.deps import get_repo

    get_repo()  # opens the shared connection and applies migrations before the first request
    vision = (s.llm_vision_model or s.llm_model) if s.llm_vision_enabled else "off"
    cache = "on" if s.meta and s.llm_cache else "off"
    auth = "on" if s.kanakku_token.get_secret_value() else "off"
    log.info(
        "Kanakku %s | provider %s | LLM %s | vision %s | STT %s | cache %s | auth %s",
        VERSION, s.llm_provider, s.llm_model, vision, s.stt_provider, cache, auth,
    )  # fmt: skip
    backups = asyncio.create_task(_backups(s))
    try:
        yield
    finally:
        await _drain(s.shutdown_grace_s)
        backups.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await backups


def create_app(settings: Settings | None = None) -> FastAPI:
    s = settings or load_settings()
    app = FastAPI(title="Kanakku", version=VERSION, lifespan=lifespan)
    errors.install(app)
    middleware.install(app, s)
    routers = (health.router, cases.router, families.router, items.router, alerts.router)
    for r in routers:
        app.include_router(r, prefix="/v1")
    for r in routers:  # old unversioned paths stay as aliases until the app has switched to /v1
        app.include_router(r, include_in_schema=False)
    return app


app = create_app()
