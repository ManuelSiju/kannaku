import asyncio
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.config import Settings
from app.providers.llm import (
    AskBudget,
    BudgetExceeded,
    LLMStepFailed,
    OpenAICompatibleLLM,
    extract_json,
    use_budget,
)


class Answer(BaseModel):
    verdict: str
    score: int


class FakeCompletions:
    def __init__(self, replies, delay=0.0):
        self.replies = list(replies)
        self.calls: list[dict] = []
        self.delay = delay

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.delay:
            await asyncio.sleep(self.delay)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=reply))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
            model=kwargs["model"],
        )


def make_llm(settings, replies, delay=0.0):
    completions = FakeCompletions(replies, delay)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return OpenAICompatibleLLM(settings, client=client), completions


async def test_chat_json_success(settings):
    llm, fake = make_llm(settings, ['```json\n{"verdict": "red", "score": 3}\n```'])
    out, usage = await llm.chat_json("sys", "user", Answer)
    assert out == Answer(verdict="red", score=3)
    assert usage.calls == 1 and usage.prompt_tokens == 10
    rf = fake.calls[0]["response_format"]
    assert rf["type"] == "json_schema" and rf["json_schema"]["name"] == "Answer"
    assert rf["json_schema"]["schema"]["properties"]["score"]["type"] == "integer"
    assert fake.calls[0]["temperature"] == 0.2
    assert llm.stats.valid_first_try == 1
    assert '"verdict"' in fake.calls[0]["messages"][0]["content"]  # schema in system prompt


async def test_meta_asks_for_plain_json_at_low_reasoning_and_records_the_reply_model():
    settings = Settings(_env_file=None, llm_provider="meta", meta_api_key="k")
    llm, fake = make_llm(settings, ['{"verdict": "red", "score": 3}'])
    await llm.chat_json("sys", "user", Answer)
    assert fake.calls[0]["response_format"] == {"type": "json_object"}  # json_schema never ends on Muse Spark
    assert fake.calls[0]["reasoning_effort"] == "minimal"
    assert '"verdict"' in fake.calls[0]["messages"][0]["content"]
    assert llm.stats.models == {"muse-spark-1.3": 1}


async def test_local_models_get_no_reasoning_effort(settings):
    llm, fake = make_llm(settings, ['{"verdict": "red", "score": 3}'])
    await llm.chat_json("sys", "user", Answer)
    assert "reasoning_effort" not in fake.calls[0]


async def test_chat_json_retries_once_with_error(settings):
    llm, fake = make_llm(settings, ['{"verdict": "red"}', '{"verdict": "red", "score": 1}'])
    out, usage = await llm.chat_json("sys", "user", Answer)
    assert out.score == 1 and usage.calls == 2
    retry_msgs = fake.calls[1]["messages"]
    assert "invalid" in retry_msgs[-1]["content"] and "score" in retry_msgs[-1]["content"]


async def test_chat_json_fails_after_two_bad_replies(settings):
    llm, _ = make_llm(settings, ["not json", "still not json"])
    with pytest.raises(LLMStepFailed):
        await llm.chat_json("sys", "user", Answer)


async def test_timeout_becomes_step_failed(settings):
    llm, _ = make_llm(settings, ['{"verdict": "red", "score": 1}'], delay=1.0)
    with pytest.raises(LLMStepFailed, match="timed out"):
        await llm.chat_text("sys", "user")


async def test_transport_error_becomes_step_failed(settings):
    llm, _ = make_llm(settings, [ConnectionError("refused")])
    with pytest.raises(LLMStepFailed, match="refused"):
        await llm.chat_text("sys", "user")


async def test_budget_counts_every_call(settings):
    llm, _ = make_llm(settings, ["a", "b", "c"])
    with use_budget(AskBudget(max_calls=2)) as budget:
        await llm.chat_text("s", "u")
        await llm.chat_text("s", "u")
        with pytest.raises(BudgetExceeded):
            await llm.chat_text("s", "u")
    assert budget.used == 2


async def test_no_budget_outside_ask(settings):
    llm, _ = make_llm(settings, ["a"])
    text, _ = await llm.chat_text("s", "u")
    assert text == "a"


async def test_images_only_sent_when_vision_enabled(settings):
    png = b"\x89PNG\r\n\x1a\nfake"
    llm, fake = make_llm(settings, ["x"])
    await llm.chat_text("s", "u", images=[png])
    assert fake.calls[0]["messages"][1]["content"] == "u"

    vision = settings.model_copy(update={"llm_vision_enabled": True})
    llm, fake = make_llm(vision, ["x"])
    await llm.chat_text("s", "u", images=[png])
    parts = fake.calls[0]["messages"][1]["content"]
    assert parts[0] == {"type": "text", "text": "u"}
    assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_extract_json():
    assert extract_json('Sure! {"a": 1} hope that helps') == '{"a": 1}'
    assert extract_json('```json\n{"a": 1}\n```') == '{"a": 1}'


def _bad_request():
    import httpx
    from openai import BadRequestError

    req = httpx.Request("POST", "http://x/v1/chat/completions")
    return BadRequestError("unsupported response_format", response=httpx.Response(400, request=req), body=None)


async def test_structured_output_falls_back_schema_then_object_then_none(settings):
    llm, fake = make_llm(settings, [_bad_request(), _bad_request(), '{"verdict": "red", "score": 1}'])
    out, _ = await llm.chat_json("sys", "user", Answer)
    assert out.score == 1
    assert [c.get("response_format", {}).get("type") for c in fake.calls] == ["json_schema", "json_object", None]


async def test_retry_counted_in_stats(settings):
    llm, _ = make_llm(settings, ['{"verdict": "red"}', '{"verdict": "red", "score": 1}'])
    await llm.chat_json("sys", "user", Answer)
    assert llm.stats.valid_after_retry == 1 and llm.stats.attempts == 2


async def test_vision_model_used_only_for_image_calls(settings):
    vision = settings.model_copy(update={"llm_vision_enabled": True, "llm_vision_model": "qwen2.5vl:7b"})
    llm, fake = make_llm(vision, ['{"verdict": "red", "score": 1}', '{"verdict": "red", "score": 1}'])
    await llm.chat_json("s", "u", Answer, images=[b"\x89PNGx"])
    await llm.chat_json("s", "u", Answer)
    assert [c["model"] for c in fake.calls] == ["qwen2.5vl:7b", settings.llm_model]
