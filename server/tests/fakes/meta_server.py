"""A fake OpenAI-compatible server that behaves like Meta's endpoint, for testing `make up` and the Meta path.

- GET  /v1/models            200 with the model list for the good key (or no key: the local checks), 401 otherwise
- POST /v1/chat/completions  401 for a bad key; 429 once (the first call, with Retry-After) when FAKE_429_ONCE=1;
                             then a JSON answer for the schema asked for (taken from tests/fixtures/llm/<case>.json,
                             the case picked from the question: loan / ZEPHYRX / otherwise the endowment)
- GET  /_stats               how many calls of each kind it answered (for the tests)

Run: python -m tests.fakes.meta_server --port 18999   (key: FAKE_META_KEY, default "good-key-123456")
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

FIXTURES = Path(__file__).parents[1] / "fixtures" / "llm"
GOOD_KEY = os.environ.get("FAKE_META_KEY", "good-key-123456")
MODELS = ["muse-spark-1.3", "qwen2.5:7b-instruct"]

app = FastAPI()
stats: Counter[str] = Counter()
_state = {"429_left": 1 if os.environ.get("FAKE_429_ONCE") == "1" else 0}


def _authorised(req: Request) -> bool:
    """No Authorization header at all = a local Ollama-style client (make up's local checks); a wrong key = 401."""
    auth = req.headers.get("authorization")
    return auth is None or auth == f"Bearer {GOOD_KEY}" or auth in ("Bearer local", "Bearer none")


def _unauthorised() -> JSONResponse:
    return JSONResponse({"error": {"message": "Invalid API key", "type": "invalid_request_error"}}, status_code=401)


@app.get("/v1/models")
async def models(req: Request) -> Any:
    stats["models"] += 1
    if not _authorised(req):
        return _unauthorised()
    return {"object": "list", "data": [{"id": m, "object": "model"} for m in MODELS]}


def _schema_name(body: dict[str, Any]) -> str:
    rf = body.get("response_format") or {}
    if rf.get("type") == "json_schema":
        return rf["json_schema"]["name"]
    system = body["messages"][0]["content"]
    for name in ("CaseDraft", "CouncilOutput", "ExplainerOutput", "RewriteOutput"):
        if f'"title":"{name}"' in system:
            return name
    return "CaseDraft"


def _case(body: dict[str, Any]) -> str:
    text = json.dumps(body["messages"][-1]["content"]).lower()
    if "zephyrx" in text:
        return "stock_tip"
    if "flat" in text and "loan" in text:
        return "flat_loan"
    if "sambar" in text or "recipe" in text:
        return "out_of_scope"
    return "endowment"


@app.post("/v1/chat/completions")
async def chat(req: Request) -> Any:
    stats["chat"] += 1
    if not _authorised(req):
        return _unauthorised()
    if _state["429_left"] > 0:
        _state["429_left"] -= 1
        stats["429"] += 1
        return JSONResponse({"error": {"message": "Rate limit"}}, status_code=429, headers={"Retry-After": "0"})
    body = await req.json()
    schema = _schema_name(body)
    fixture = json.loads((FIXTURES / f"{_case(body)}.json").read_text())
    answer = fixture.get(schema)
    if isinstance(answer, list):
        answer = answer[0]
    if answer is None or answer == "__timeout__":
        answer = {"lines": []} if schema == "RewriteOutput" else {}
    # quote placeholders in fixtures ({quote:page_1}) -> the quote ids the server sent
    user = body["messages"][-1]["content"]
    if isinstance(user, list):
        user = next((p["text"] for p in user if p.get("type") == "text"), "{}")
    try:
        quotes = {q["source"]: q["id"] for q in json.loads(user).get("quotes", [])}
    except Exception:
        quotes = {}
    text = json.dumps(answer)
    for source, qid in quotes.items():
        text = text.replace(f"{{quote:{source}}}", qid)
    stats[f"answer:{schema}"] += 1
    return {
        "id": f"fake-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.get("model", "muse-spark-1.3"),
        "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }


@app.get("/_stats")
async def get_stats() -> dict[str, int]:
    return dict(stats)


if __name__ == "__main__":
    import uvicorn

    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=18999)
    uvicorn.run(app, host="127.0.0.1", port=ap.parse_args().port, log_level="warning")
