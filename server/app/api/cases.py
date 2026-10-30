"""POST /cases (ask), GET /cases/{id}, GET /cases/{id}/events (SSE), POST /cases/{id}/letter."""

from __future__ import annotations

import asyncio
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.api.deps import get_bus, get_llm_provider, get_repo, get_stt_provider, require_family
from app.db.repo import Repo
from app.pipeline.events import EventBus
from app.pipeline.ingest import Upload
from app.pipeline.letter import LetterKind, draft_letter
from app.pipeline.run import AskInput, run_pipeline
from app.pipeline.schemas import CaseResult
from app.providers.llm import LLMProvider
from app.providers.stt import STTProvider

router = APIRouter(tags=["cases"])
_background: set[asyncio.Task[Any]] = set()


async def _upload(f: UploadFile) -> Upload:
    return Upload(filename=f.filename or "upload", data=await f.read(), mime=f.content_type or "")


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
    repo: Repo = Depends(get_repo),
    llm: LLMProvider = Depends(get_llm_provider),
    stt: STTProvider = Depends(get_stt_provider),
    bus: EventBus = Depends(get_bus),
) -> Any:
    """Ask a money question. wait=false returns 202 {case_id} at once; follow /cases/{id}/events, then GET it."""
    require_family(repo, family_id)
    uploads = [await _upload(f) for f in files or []]
    audio_up = await _upload(audio) if audio is not None else None
    if not (text and text.strip()) and audio_up is None and not uploads:
        raise HTTPException(422, "send text, audio or at least one file")
    if case_id is not None:
        existing = repo.get_case(case_id)
        if existing is None or existing["family_id"] != family_id:
            raise HTTPException(404, f"case {case_id} not found")
    else:
        case_id = repo.create_case(family_id)
    inp = AskInput(
        family_id=family_id,
        text=text,
        audio=audio_up,
        files=uploads,
        earphones=earphones,
        user_says_alone=user_says_alone,
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
