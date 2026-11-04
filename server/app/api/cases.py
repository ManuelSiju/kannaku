"""POST /cases (ask), GET /cases/{id}, GET /cases/{id}/events (SSE), POST /cases/{id}/letter."""

from __future__ import annotations

import asyncio
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.api import uploads as upload_limits
from app.api.deps import get_bus, get_llm_provider, get_repo, get_settings_dep, get_stt_provider, require_family
from app.api.errors import ApiError
from app.config import Settings, get_settings
from app.core.context import request_id
from app.db.repo import Repo
from app.pipeline.events import EventBus
from app.pipeline.ingest import Upload
from app.pipeline.letter import LetterKind, draft_letter
from app.pipeline.run import AskInput, run_pipeline
from app.pipeline.schemas import CaseResult
from app.providers.guard import GuardedLLM, cap_message
from app.providers.llm import LLMProvider
from app.providers.stt import STTProvider

router = APIRouter(tags=["cases"])
_background: set[asyncio.Task[Any]] = set()


def background_tasks() -> set[asyncio.Task[Any]]:
    return set(_background)


async def _upload(f: UploadFile, limit_bytes: int) -> Upload:
    data = await f.read(limit_bytes + 1)  # never read more than the largest allowed file
    if len(data) > limit_bytes:
        raise ApiError(413, "file_too_large", f"{f.filename or 'upload'} is too big.")
    return Upload(filename=f.filename or "upload", data=data, mime=f.content_type or "")


def _replay(repo: Repo, case_id: int) -> Any:
    """The answer to a resent request: the finished result, or 202 while the first one is still running."""
    case = repo.get_case(case_id) or {}
    if case.get("result_json"):
        return JSONResponse(json.loads(case["result_json"]), headers={"Idempotent-Replay": "true"})
    return JSONResponse(
        {"case_id": case_id, "status": "running"}, status_code=202, headers={"Idempotent-Replay": "true"}
    )


@router.post("/cases", response_model=CaseResult, responses={202: {"description": "accepted (wait=false)"}})
async def ask(
    family_id: Annotated[int, Form()] = 1,
    text: Annotated[str | None, Form()] = None,
    earphones: Annotated[bool, Form()] = False,
    user_says_alone: Annotated[bool, Form()] = False,
    case_id: Annotated[int | None, Form()] = None,
    wait: Annotated[bool, Form()] = True,
    audio: Annotated[UploadFile | None, File()] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
    idempotency_key: Annotated[str | None, Header(max_length=128)] = None,
    repo: Repo = Depends(get_repo),
    settings: Settings = Depends(get_settings_dep),
    llm: LLMProvider = Depends(get_llm_provider),
    stt: STTProvider = Depends(get_stt_provider),
    bus: EventBus = Depends(get_bus),
) -> Any:
    """Ask a money question. wait=false returns 202 {case_id} at once; follow /cases/{id}/events, then GET it."""
    """Send an Idempotency-Key header to make a resend safe: the same key returns the first case."""
    require_family(repo, family_id)
    if idempotency_key and (seen := repo.idempotent_case(idempotency_key, family_id)) is not None:
        return _replay(repo, seen)
    if len(files or []) > settings.max_files:
        raise ApiError(413, "too_many_files", f"Send at most {settings.max_files} files at a time.")
    biggest = int(max(settings.max_pdf_mb, settings.max_image_mb, settings.max_audio_mb) * upload_limits.MB)
    uploads = [await _upload(f, biggest) for f in files or []]
    audio_up = await _upload(audio, biggest) if audio is not None else None
    audio_up, uploads = upload_limits.check_all(audio_up, uploads, settings)
    if not (text and text.strip()) and audio_up is None and not uploads:
        raise HTTPException(422, "send text, audio or at least one file")
    if isinstance(llm, GuardedLLM) and llm.guard.exhausted() and llm.fallback is None:
        raise ApiError(429, "daily_limit", cap_message(llm.guard.cap))
    if case_id is not None:
        existing = repo.get_case(case_id)
        if existing is None or existing["family_id"] != family_id:
            raise HTTPException(404, f"case {case_id} not found")
    else:
        case_id = repo.create_case(family_id)
    if idempotency_key and not repo.claim_idempotency(idempotency_key, family_id, case_id):
        return _replay(repo, repo.idempotent_case(idempotency_key, family_id) or case_id)  # lost a race
    inp = AskInput(
        family_id=family_id,
        text=text,
        audio=audio_up,
        files=uploads,
        earphones=earphones,
        user_says_alone=user_says_alone,
        request_id=request_id(),
    )
    if wait:
        return await run_pipeline(case_id, inp, repo=repo, llm=llm, stt=stt, bus=bus)
    task = asyncio.create_task(run_pipeline(case_id, inp, repo=repo, llm=llm, stt=stt, bus=bus))
    _background.add(task)
    task.add_done_callback(_background.discard)
    return JSONResponse({"case_id": case_id, "status": "running"}, status_code=202)


@router.get("/cases/{case_id}")
def get_case(case_id: int, repo: Repo = Depends(get_repo)) -> dict[str, Any]:
    """Full case incl. dropped arguments, blocked lines and trace (for the Under the hood screen)."""
    bundle = repo.case_bundle(case_id)
    if bundle is None:
        raise HTTPException(404, f"case {case_id} not found")
    raw = bundle["case"].pop("result_json", None)
    bundle["result"] = json.loads(raw) if raw else None
    return bundle


@router.get("/cases/{case_id}/trace.json")
def trace_export(case_id: int, repo: Repo = Depends(get_repo)) -> dict[str, Any]:
    """Everything that decided one case, as one file a reviewer can read."""
    bundle = repo.case_bundle(case_id) if get_settings().feature_trace_export else None
    if bundle is None:
        raise HTTPException(404, f"case {case_id} not found")
    steps = bundle["trace"]
    request = next((t["detail"] for t in steps if t["step"] == "request"), {})
    verdict = bundle["verdict"] or {}
    return {
        "case_id": case_id,
        "case_type": bundle["case"]["case_type"],
        "privacy_mode": bundle["case"]["privacy_mode"],
        "provider": request.get("provider"),
        "models": request.get("models"),
        "router": next((t["detail"] for t in steps if t["step"] == "router"), {}),
        "tool_calls": next((t["detail"] for t in steps if t["step"] == "compute"), {}),
        "facts": bundle["facts"],
        "dropped_arguments": [
            {"agent": a["agent"], "text": a["text"], "reason": a["drop_reason"]}
            for a in bundle["arguments"]
            if not a["kept"]
        ],
        "vote": {
            "positions": bundle["positions"],
            "score": verdict.get("score"),
            "disagreement": verdict.get("disagreement"),
            "colour": verdict.get("colour"),
        },
        "overrides": verdict.get("overrides", []),
        "privacy_blocks": [
            {"speaker": ln["speaker"], "text": ln["text"], "reason": ln["blocked_reason"]}
            for ln in bundle["spoken_lines"]
            if not ln["allowed"]
        ],
        "timings_ms": [{"step": t["step"], "ms": t["ms"], "outcome": t["outcome"]} for t in steps],
    }


@router.get("/cases/{case_id}/events")
async def events(case_id: int, repo: Repo = Depends(get_repo), bus: EventBus = Depends(get_bus)) -> StreamingResponse:
    """Server-Sent Events: step_started / step_finished / agent_called / agent_done / done."""
    if repo.get_case(case_id) is None:
        raise HTTPException(404, f"case {case_id} not found")

    async def stream() -> Any:
        if repo.get_case(case_id)["status"] == "done" and not bus.history(case_id):  # type: ignore[index]
            yield f"data: {json.dumps({'type': 'done', 'case_id': case_id})}\n\n"
            return
        async for event in bus.subscribe(case_id):
            yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


class LetterRequest(BaseModel):
    kind: LetterKind = "cancel"
    sender_name: str = ""


@router.post("/cases/{case_id}/letter")
def letter(case_id: int, body: LetterRequest, repo: Repo = Depends(get_repo)) -> dict[str, str]:
    bundle = repo.case_bundle(case_id)
    if bundle is None:
        raise HTTPException(404, f"case {case_id} not found")
    return {"kind": body.kind, "text": draft_letter(bundle, body.kind, body.sender_name)}
