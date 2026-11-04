"""Real Meta replies, played back without a key (make demo-replay). scripts/record_replay.py records them, keyed by the
same hash as the response cache. A question outside the recording fails its step; nothing is ever made up here."""

from __future__ import annotations

import json
from typing import Any

from app.config import Settings, get_settings
from app.providers.guard import cache_key
from app.providers.llm import LLMProvider, LLMStepFailed, LLMUsage, T, current_budget


class ReplayLLM(LLMProvider):
    name = "replay"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.model = self.settings.meta_model
        self.calls: dict[str, dict[str, Any]] = {}
        for path in sorted(self.settings.replay_dir.glob("*.json")):
            self.calls.update(json.loads(path.read_text())["calls"])
        self.recorded_at = max((c["at"] for c in self.calls.values()), default=None)

    def _find(self, system: str, user: str, schema: str, images: list[bytes] | None) -> dict[str, Any]:
        budget = current_budget()
        call = self.calls.get(cache_key(system, user, schema, self.model, images))
        if call is None:
            raise LLMStepFailed("replay answers the recorded demo questions only")
        if budget is not None:
            budget.consume()
            budget.replay_at = call["at"]
        return call

    async def chat_json(
        self, system: str, user: str, schema: type[T], images: list[bytes] | None = None
    ) -> tuple[T, LLMUsage]:
        call = self._find(system, user, schema.__name__, images)
        return schema.model_validate_json(call["response"]), LLMUsage(calls=1)

    async def chat_text(self, system: str, user: str, images: list[bytes] | None = None) -> tuple[str, LLMUsage]:
        return json.loads(self._find(system, user, "text", images)["response"]), LLMUsage(calls=1)
