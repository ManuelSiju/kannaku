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


def shrink_image(data: bytes, max_side: int) -> bytes:
    """Downscale so the long side is at most max_side (PNG out). Unreadable data is returned unchanged."""
    try:
        import io

        from PIL import Image

        im = Image.open(io.BytesIO(data))
        if max(im.size) <= max_side:
            return data
        im.thumbnail((max_side, max_side))
        out = io.BytesIO()
        im.convert("RGB").save(out, format="PNG")
        return out.getvalue()
    except Exception:
        return data


def _sniff_mime(data: bytes) -> str:
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


class LLMStats(BaseModel):
    """Counters for reliability reports (per provider instance)."""

    steps: int = 0  # chat_json calls
    attempts: int = 0  # requests sent
    valid_first_try: int = 0
    valid_after_retry: int = 0
    invalid_twice: int = 0
    transport_failures: int = 0


_FORMATS = ("json_schema", "json_object", "none")


class OpenAICompatibleLLM(LLMProvider):
    name = "openai_compatible"

    def __init__(self, settings: Settings | None = None, client: AsyncOpenAI | None = None) -> None:
        self.settings = settings or get_settings()
        self.model = self.settings.llm_model
        self.vision_model = self.settings.llm_vision_model or self.model
        self.client = client or AsyncOpenAI(
            base_url=self.settings.llm_base_url,
            api_key=self.settings.llm_api_key or "none",
            timeout=self.settings.llm_timeout_s,
            max_retries=0,
        )
        self._format = 0  # index into _FORMATS; drops a level when the server rejects one
        self.stats = LLMStats()

    def _messages(self, system: str, user: str, images: list[bytes] | None) -> list[dict[str, Any]]:
        content: str | list[dict[str, Any]] = user
        if images and self.settings.llm_vision_enabled:
            parts: list[dict[str, Any]] = [{"type": "text", "text": user}]
            for img in images:
                b64 = base64.b64encode(shrink_image(img, self.settings.llm_image_max_side)).decode()
                parts.append({"type": "image_url", "image_url": {"url": f"data:{_sniff_mime(img)};base64,{b64}"}})
            content = parts
        return [{"role": "system", "content": system}, {"role": "user", "content": content}]

    def _response_format(self, schema: type[BaseModel] | None) -> dict[str, Any] | None:
        fmt = _FORMATS[self._format]
        if schema is None or fmt == "none":
            return None
        if fmt == "json_schema":
            # Server-side constrained decoding (Ollama `format` / llama-server json_schema) via the OpenAI API.
            return {
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
            }
        return {"type": "json_object"}

    async def _create(self, kwargs: dict[str, Any], timeout: float | None = None) -> Any:
        timeout = timeout or self.settings.llm_timeout_s
        return await asyncio.wait_for(self.client.chat.completions.create(**kwargs, timeout=timeout), timeout=timeout)

    async def _call(
        self, messages: list[dict[str, Any]], schema: type[BaseModel] | None, usage: LLMUsage, *, vision: bool
    ) -> str:
        budget = current_budget()
        if budget is not None:
            budget.consume()
        self.stats.attempts += 1
        kwargs: dict[str, Any] = {
            "model": self.vision_model if vision else self.model,
            "messages": messages,
            "temperature": self.settings.llm_temperature,
        }
        loop = asyncio.get_running_loop()
        t0 = loop.time()
        try:
            while True:
                rf = self._response_format(schema)
                if rf is None:
                    kwargs.pop("response_format", None)
                else:
                    kwargs["response_format"] = rf
                try:
                    resp = await self._create(kwargs, self.settings.llm_vision_timeout_s if vision else None)
                    break
                except BadRequestError as e:
                    if rf is None or self._format >= len(_FORMATS) - 1:
                        raise
                    # The server does not support this structured-output mode; the schema in the prompt still applies.
                    log.warning("LLM server rejected response_format %s (%s); trying %s", _FORMATS[self._format], e,
                                _FORMATS[self._format + 1])  # fmt: skip
                    self._format += 1
        except TimeoutError as e:
            self.stats.transport_failures += 1
            limit = self.settings.llm_vision_timeout_s if vision else self.settings.llm_timeout_s
            raise LLMStepFailed(f"LLM call timed out after {limit:g}s") from e
        except Exception as e:  # transport errors, connection refused, rejected request, ...
            self.stats.transport_failures += 1
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
        self.stats.steps += 1
        schema_text = json.dumps(schema.model_json_schema(), separators=(",", ":"))
        full_system = (
            f"{system}\n\nReply with ONE JSON object only, no prose, matching this JSON schema:\n{schema_text}"
        )
        vision = bool(images) and self.settings.llm_vision_enabled
        messages = self._messages(full_system, user, images)
        usage = LLMUsage()
        error = ""
        for attempt in range(2):
            raw = await self._call(messages, schema, usage, vision=vision)
            try:
                parsed = schema.model_validate_json(extract_json(raw))
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
                continue
            if attempt == 0:
                self.stats.valid_first_try += 1
            else:
                self.stats.valid_after_retry += 1
            return parsed, usage
        self.stats.invalid_twice += 1
        raise LLMStepFailed(f"LLM returned invalid JSON twice: {error}")

    async def chat_text(self, system: str, user: str, images: list[bytes] | None = None) -> tuple[str, LLMUsage]:
        usage = LLMUsage()
        vision = bool(images) and self.settings.llm_vision_enabled
        text = await self._call(self._messages(system, user, images), None, usage, vision=vision)
        return text, usage


def get_llm(settings: Settings | None = None) -> LLMProvider:
    return OpenAICompatibleLLM(settings)
