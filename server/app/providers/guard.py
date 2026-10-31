"""Spend guard for the Meta Model API: a response cache and a daily call cap, both kept in SQLite.

- Cache key: sha256 of (system prompt, user prompt, schema name, model, images). A hit costs no call.
- Cap: META_MAX_CALLS_PER_DAY requests per local day (every request sent counts, retries too). At 80 % a warning is
  logged once a day; at the cap an ask fails fast with SpendCapReached, unless LLM_FALLBACK=local, in which case the
  local models answer and the ask is marked (budget.fallback_used -> "local fallback" badge and trace). Never silent.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any

from app.config import Settings
from app.db.migrate import migrate
from app.providers.llm import LLMProvider, LLMStepFailed, LLMUsage, T, current_budget

log = logging.getLogger(__name__)
WARN_AT = 0.8


class SpendCapReached(LLMStepFailed):
    """Today's Meta Model API call cap is used up."""


def cap_message(cap: int) -> str:
    return (
        f"Today's limit of {cap} Meta model calls is used up. It resets at midnight; "
        "to keep going now, restart with: make up PROVIDER=local"
    )


class SpendGuard:
    def __init__(self, db_path: str | Path, cap: int) -> None:
        self.cap = cap
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        migrate(self.conn)
        self._warned_day = ""

    @staticmethod
    def today() -> str:
        return dt.date.today().isoformat()

    def calls_today(self) -> int:
        row = self.conn.execute("SELECT calls FROM llm_calls_daily WHERE day = ?", (self.today(),)).fetchone()
        return int(row[0]) if row else 0

    def exhausted(self) -> bool:
        return self.calls_today() >= self.cap

    def add(self, n: int) -> int:
        if n <= 0:
            return self.calls_today()
        with self._lock:
            self.conn.execute(
                "INSERT INTO llm_calls_daily (day, calls) VALUES (?, ?) "
                "ON CONFLICT(day) DO UPDATE SET calls = calls + excluded.calls",
                (self.today(), n),
            )
            self.conn.commit()
        used = self.calls_today()
        if used >= WARN_AT * self.cap and self._warned_day != self.today():
            self._warned_day = self.today()
            log.warning(
                "Meta model calls today: %d of %d (%.0f%% of the daily cap)", used, self.cap, 100 * used / self.cap
            )
        return used

    def status(self) -> dict[str, Any]:
        used = self.calls_today()
        return {
            "cap": self.cap,
            "calls_today": used,
            "warning": used >= WARN_AT * self.cap,
            "exhausted": used >= self.cap,
        }

    # ---------------------------------------------------------------- cache
    def cache_get(self, key: str) -> str | None:
        row = self.conn.execute("SELECT response FROM llm_cache WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def cache_put(self, key: str, model: str, response: str) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO llm_cache (key, model, response) VALUES (?, ?, ?)", (key, model, response)
            )
            self.conn.commit()


def cache_key(system: str, user: str, schema: str, model: str, images: list[bytes] | None) -> str:
    h = hashlib.sha256()
    for part in (system, user, schema, model):
        h.update(part.encode())
        h.update(b"\0")
    for img in images or []:
        h.update(hashlib.sha256(img).digest())
    return h.hexdigest()


class GuardedLLM(LLMProvider):
    """Wraps the Meta provider. `fallback` is the local provider when LLM_FALLBACK=local, else None."""

    name = "meta_guarded"

    def __init__(
        self, inner: LLMProvider, settings: Settings, guard: SpendGuard, fallback: LLMProvider | None = None
    ) -> None:
        self.inner, self.settings, self.guard, self.fallback = inner, settings, guard, fallback
        self.model = settings.llm_model
        self.stats = getattr(inner, "stats", None)

    def _attempts(self) -> int:
        stats = getattr(self.inner, "stats", None)
        return int(getattr(stats, "attempts", 0))

    def _over_cap(self) -> LLMProvider | None:
        """None -> use Meta; else the provider to use instead. Raises when there is no fallback."""
        if not self.guard.exhausted():
            return None
        if self.fallback is None:
            raise SpendCapReached(cap_message(self.guard.cap))
        budget = current_budget()
        if budget is not None:
            budget.fallback_used = True
        log.warning("Meta daily cap reached: answering with the local models (LLM_FALLBACK=local)")
        return self.fallback

    async def _counted(self, coro: Any) -> Any:
        before = self._attempts()
        try:
            return await coro
        finally:
            self.guard.add(self._attempts() - before)

    async def chat_json(
        self, system: str, user: str, schema: type[T], images: list[bytes] | None = None
    ) -> tuple[T, LLMUsage]:
        key = cache_key(system, user, schema.__name__, self.model, images) if self.settings.llm_cache else ""
        if key and (hit := self.guard.cache_get(key)) is not None:
            budget = current_budget()
            if budget is not None:
                budget.cache_hits += 1
            return schema.model_validate_json(hit), LLMUsage(calls=0)
        if (other := self._over_cap()) is not None:
            return await other.chat_json(system, user, schema, images)
        out, usage = await self._counted(self.inner.chat_json(system, user, schema, images))
        if key:
            self.guard.cache_put(key, self.model, out.model_dump_json())
        return out, usage

    async def chat_text(self, system: str, user: str, images: list[bytes] | None = None) -> tuple[str, LLMUsage]:
        key = cache_key(system, user, "text", self.model, images) if self.settings.llm_cache else ""
        if key and (hit := self.guard.cache_get(key)) is not None:
            return json.loads(hit), LLMUsage(calls=0)
        if (other := self._over_cap()) is not None:
            return await other.chat_text(system, user, images)
        text, usage = await self._counted(self.inner.chat_text(system, user, images))
        if key:
            self.guard.cache_put(key, self.model, json.dumps(text))
        return text, usage
