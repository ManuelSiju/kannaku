"""Records the demo cases on the real Meta API for make demo-replay. Writes demo_assets/replay/meta_recording.json.
Run after any prompt change: a changed prompt no longer matches its recording. Needs META_API_KEY; it is never written.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.db.repo import Repo  # noqa: E402
from app.db.seed_demo import seed  # noqa: E402
from app.pipeline.demo_cases import DEMO_CASES, upload_for  # noqa: E402
from app.pipeline.events import EventBus  # noqa: E402
from app.pipeline.run import AskInput, run_pipeline  # noqa: E402
from app.providers.guard import cache_key  # noqa: E402
from app.providers.llm import LLMProvider, OpenAICompatibleLLM  # noqa: E402

TRIES = 3


class Recording(LLMProvider):
    name = "recording"

    def __init__(self, inner: OpenAICompatibleLLM) -> None:
        self.inner, self.calls = inner, {}

    def _keep(self, key: str, response: str, model_hint: str) -> None:
        at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        self.calls[key] = {"at": at, "model": model_hint, "response": response}

    async def chat_json(self, system, user, schema, images=None):
        out, usage = await self.inner.chat_json(system, user, schema, images)
        key = cache_key(system, user, schema.__name__, self.inner.model, images)
        self._keep(key, out.model_dump_json(), self.inner.model)
        return out, usage

    async def chat_text(self, system, user, images=None):
        text, usage = await self.inner.chat_text(system, user, images)
        self._keep(cache_key(system, user, "text", self.inner.model, images), json.dumps(text), self.inner.model)
        return text, usage


async def main() -> int:
    settings = Settings(llm_provider="meta", db_path=Path(tempfile.mkdtemp()) / "k.db", llm_cache=False)
    kept: dict[str, dict] = {}
    for name, (question, filename) in DEMO_CASES.items():
        for attempt in range(TRIES):  # a run with a failed step is not a demo recording
            repo = Repo(Path(tempfile.mkdtemp()) / "k.db")
            seed(repo)
            llm = Recording(OpenAICompatibleLLM(settings))
            files = [upload_for(filename)] if filename else []
            res = await run_pipeline(
                repo.create_case(1),
                AskInput(family_id=1, text=question, files=files),
                repo=repo, llm=llm, stt=None, settings=settings, bus=EventBus(),
            )  # fmt: skip
            print(name, f"try {attempt + 1}:", res.verdict.colour, res.degraded_steps or "clean", flush=True)
            if not res.degraded_steps:
                kept.update(llm.calls)
                break
        else:
            print(f"{name}: no clean run")
            return 1
    out = settings.replay_dir / "meta_recording.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"calls": kept}, indent=0, ensure_ascii=False))
    print(f"wrote {len(kept)} calls to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
