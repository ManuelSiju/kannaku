"""Offline stand-ins for the model providers, driven by JSON fixtures in tests/fixtures/llm/."""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from pydantic import BaseModel

from app.providers.llm import LLMProvider, LLMStepFailed, LLMUsage, current_budget
from app.providers.stt import STTProvider, Transcript

FIXTURES = Path(__file__).parent / "fixtures" / "llm"
TIMEOUT = "__timeout__"
_PLACEHOLDER = re.compile(r"\{quote:([a-z_0-9]+)\}")


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / f"{name}.json").read_text())


class FakeLLM(LLMProvider):
    """Answers chat_json from a script keyed by schema class name. A list is consumed in order (the last entry
    repeats). "__timeout__" raises LLMStepFailed like a real timeout. "{quote:page_1}" in a fixture becomes the
    quote id the pipeline sent for that source. Every call consumes the active AskBudget, like the real one."""

    name = "fake"

    def __init__(
        self, script: dict[str, Any] | None = None, *, vision: bool = False, vision_fails: bool = False
    ) -> None:
        self.script = {k: list(v) if isinstance(v, list) else [v] for k, v in (script or {}).items()}
        self.calls: list[str] = []
        self.inputs: list[dict[str, Any]] = []
        self.image_calls = 0
        self.vision_fails = vision_fails
        self.settings = SimpleNamespace(llm_vision_enabled=vision)

    async def chat_json(self, system: str, user: str, schema: type[BaseModel], images: list[bytes] | None = None):
        budget = current_budget()
        if budget is not None:
            budget.consume()
        self.calls.append(schema.__name__)
        if images:
            self.image_calls += 1
            if self.vision_fails:
                raise LLMStepFailed("LLM call timed out after 60s")
        payload = json.loads(user)
        self.inputs.append(payload)
        queue = self.script.get(schema.__name__)
        if not queue:
            raise LLMStepFailed(f"no fixture for {schema.__name__}")
        resp = queue.pop(0) if len(queue) > 1 else queue[0]
        if resp == TIMEOUT:
            raise LLMStepFailed("LLM call timed out after 20s")
        ids = {q["source"]: q["id"] for q in payload.get("quotes", [])}
        text = _PLACEHOLDER.sub(lambda m: ids.get(m.group(1), m.group(0)), json.dumps(resp))
        return schema.model_validate_json(text), LLMUsage(calls=1)

    async def chat_text(self, system: str, user: str, images: list[bytes] | None = None):
        raise LLMStepFailed("chat_text not scripted")


class FakeSTT(STTProvider):
    name = "fake"

    def __init__(self, text: str, language: str = "en") -> None:
        self.text, self.language = text, language

    async def transcribe(self, audio_bytes: bytes, mime: str) -> Transcript:
        return Transcript(text=self.text, language=self.language, segments=[])
