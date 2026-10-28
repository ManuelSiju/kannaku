"""LLM provider layer. Business logic only talks to LLMProvider, never to an SDK directly.

Any OpenAI-compatible endpoint works (Ollama, llama.cpp llama-server, Meta Model API):
only LLM_BASE_URL / LLM_MODEL / LLM_API_KEY change.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextvars import ContextVar
from typing import Any, TypeVar

from openai import AsyncOpenAI, BadRequestError
from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    calls: int = 0
    ms: float = 0.0


class LLMStepFailed(Exception):
    """The LLM step could not produce a valid answer (timeout, transport error, bad JSON twice)."""


class BudgetExceeded(Exception):
    """More LLM calls were attempted in one ask than LLM_MAX_CALLS_PER_ASK allows."""


class AskBudget:
    """Counts LLM calls for one ask. Activate with `use_budget(budget)`."""

    def __init__(self, max_calls: int) -> None:
        self.max_calls = max_calls
        self.used = 0

    def consume(self) -> None:
        if self.used >= self.max_calls:
            raise BudgetExceeded(f"LLM call budget of {self.max_calls} per ask exhausted")
        self.used += 1


_current_budget: ContextVar[AskBudget | None] = ContextVar("kanakku_ask_budget", default=None)


@contextlib.contextmanager
def use_budget(budget: AskBudget) -> Iterator[AskBudget]:
    token = _current_budget.set(budget)
    try:
        yield budget
    finally:
        _current_budget.reset(token)


def current_budget() -> AskBudget | None:
    return _current_budget.get()


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def chat_json(
        self, system: str, user: str, schema: type[T], images: list[bytes] | None = None
    ) -> tuple[T, LLMUsage]: ...

    @abstractmethod
    async def chat_text(self, system: str, user: str, images: list[bytes] | None = None) -> tuple[str, LLMUsage]: ...


_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def extract_json(text: str) -> str:
    """Strip markdown fences and any prose around the outermost JSON object."""
    text = _FENCE.sub("", text.strip())
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if start != -1 and end > start else text


def _sniff_mime(data: bytes) -> str:
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


class OpenAICompatibleLLM(LLMProvider):
    name = "openai_compatible"

    def __init__(self, settings: Settings | None = None, client: AsyncOpenAI | None = None) -> None:
        self.settings = settings or get_settings()
        self.model = self.settings.llm_model
        self.client = client or AsyncOpenAI(
            base_url=self.settings.llm_base_url,
            api_key=self.settings.llm_api_key or "none",
            timeout=self.settings.llm_timeout_s,
            max_retries=0,
        )
        self._json_mode_supported = True

    def _messages(self, system: str, user: str, images: list[bytes] | None) -> list[dict[str, Any]]:
        content: str | list[dict[str, Any]] = user
        if images and self.settings.llm_vision_enabled:
            parts: list[dict[str, Any]] = [{"type": "text", "text": user}]
            for img in images:
                b64 = base64.b64encode(img).decode()
                parts.append({"type": "image_url", "image_url": {"url": f"data:{_sniff_mime(img)};base64,{b64}"}})
            content = parts
        return [{"role": "system", "content": system}, {"role": "user", "content": content}]

    async def _create(self, kwargs: dict[str, Any]) -> Any:
        return await asyncio.wait_for(
            self.client.chat.completions.create(**kwargs), timeout=self.settings.llm_timeout_s
        )

    async def _call(self, messages: list[dict[str, Any]], json_mode: bool, usage: LLMUsage) -> str:
        budget = current_budget()
        if budget is not None:
            budget.consume()
        kwargs: dict[str, Any] = {"model": self.model, "messages": messages}
        if json_mode and self._json_mode_supported:
            kwargs["response_format"] = {"type": "json_object"}
        loop = asyncio.get_running_loop()
        t0 = loop.time()
        try:
            try:
                resp = await self._create(kwargs)
            except BadRequestError:
                if "response_format" not in kwargs:
                    raise
                # Server does not support JSON mode; the schema in the prompt still applies.
                log.warning("LLM server rejected response_format; continuing without JSON mode")
                self._json_mode_supported = False
                kwargs.pop("response_format")
                resp = await self._create(kwargs)
        except TimeoutError as e:
            raise LLMStepFailed(f"LLM call timed out after {self.settings.llm_timeout_s}s") from e
        except Exception as e:  # transport errors, connection refused, rejected request, ...
            raise LLMStepFailed(f"LLM call failed: {type(e).__name__}: {e}") from e
        finally:
            usage.ms += (loop.time() - t0) * 1000
        usage.calls += 1
        if resp.usage is not None:
            usage.prompt_tokens = (usage.prompt_tokens or 0) + resp.usage.prompt_tokens
            usage.completion_tokens = (usage.completion_tokens or 0) + resp.usage.completion_tokens
        return resp.choices[0].message.content or ""

    async def chat_json(
        self, system: str, user: str, schema: type[T], images: list[bytes] | None = None
    ) -> tuple[T, LLMUsage]:
        schema_text = json.dumps(schema.model_json_schema(), separators=(",", ":"))
        full_system = (
            f"{system}\n\nReply with ONE JSON object only, no prose, matching this JSON schema:\n{schema_text}"
        )
        messages = self._messages(full_system, user, images)
        usage = LLMUsage()
        error = ""
        for attempt in range(2):
            raw = await self._call(messages, json_mode=True, usage=usage)
            try:
                return schema.model_validate_json(extract_json(raw)), usage
            except ValidationError as e:
                error = str(e)
                log.info("LLM JSON invalid (attempt %d): %s", attempt + 1, error)
                messages = messages + [
                    {"role": "assistant", "content": raw},
                    {
                        "role": "user",
                        "content": f"That JSON was invalid:\n{error}\nReply again with corrected JSON only.",
                    },
                ]
        raise LLMStepFailed(f"LLM returned invalid JSON twice: {error}")

    async def chat_text(self, system: str, user: str, images: list[bytes] | None = None) -> tuple[str, LLMUsage]:
        usage = LLMUsage()
        text = await self._call(self._messages(system, user, images), json_mode=False, usage=usage)
        return text, usage


def get_llm(settings: Settings | None = None) -> LLMProvider:
    return OpenAICompatibleLLM(settings)
