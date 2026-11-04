"""Family profile: GET/POST /families/{id}/profile, POST .../profile/extract (proposals, NOT saved),
POST .../profile/confirm (saves only confirmed values)."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.api.deps import get_repo, get_stt_provider, require_family
from app.config import get_settings
from app.db.repo import PROFILE_FIELDS, FamilyItem, Repo
from app.mcp_server import tools
from app.pipeline.ingest import Upload, ingest
from app.pipeline.profile_extract import Field, Proposal, extract_profile
from app.providers.stt import STTProvider

router = APIRouter(tags=["families"])


class ProfileValueIn(BaseModel):
    field: Field
    value: float
    source: Literal["typed", "voice", "document"]
    source_ref: str | None = None
    confirmed: bool
    in_household: bool | None = None  # None: yes for the primary member, no for anyone else


class ItemIn(FamilyItem):
    in_household: bool | None = None  # type: ignore[assignment]


class ConfirmIn(BaseModel):
    values: list[ProfileValueIn] = []
    items: list[ItemIn] = []
    member_id: int | None = None  # default: the primary member


def _primary(repo: Repo, family_id: int) -> int:
    require_family(repo, family_id)
    member = repo.primary_member_id(family_id)
    if member is None:
        raise HTTPException(409, "family has no primary member")
    return member


def _member(repo: Repo, family_id: int, member_id: int | None) -> tuple[int, bool]:
    """Whose values these are, and whether that is the primary member. Without members, always the primary."""
    primary = _primary(repo, family_id)
    if member_id is None or member_id == primary or not get_settings().feature_members:
        return primary, True
    if not repo.member_in_family(family_id, member_id):
        raise HTTPException(422, "that person is not in this family")
    return member_id, False


@router.get("/families/{family_id}/profile")
def get_profile(family_id: int, repo: Repo = Depends(get_repo)) -> dict[str, Any]:
    require_family(repo, family_id)
    out = tools.family_get_profile(family_id, repo)
    out["members"] = repo.members(family_id)
    out["language"] = repo.get_family(family_id)["language"]  # type: ignore[index]
    return out


@router.post("/families/{family_id}/profile")
def set_profile(family_id: int, body: ProfileValueIn, repo: Repo = Depends(get_repo)) -> dict[str, Any]:
    if not body.confirmed:
        raise HTTPException(422, "only confirmed values are saved")
    repo.set_profile_value(
        _primary(repo, family_id), body.field, body.value, body.source, source_ref=body.source_ref, confirmed=True
    )
    return tools.family_get_profile(family_id, repo)


@router.get("/families/{family_id}/documents")
def documents(family_id: int, repo: Repo = Depends(get_repo)) -> dict[str, Any]:
    """Papers this family showed, newest first, with the category each was given."""
    require_family(repo, family_id)
    return {"documents": tools.family_list_documents(family_id, repo)["documents"]}


@router.post("/families/{family_id}/profile/extract", response_model=Proposal)
async def extract(
    family_id: int,
    text: Annotated[str | None, Form()] = None,
    field: Annotated[Field | None, Form()] = None,
    member_id: Annotated[int | None, Form()] = None,
    audio: Annotated[UploadFile | None, File()] = None,
    file: Annotated[UploadFile | None, File()] = None,
    repo: Repo = Depends(get_repo),
    stt: STTProvider = Depends(get_stt_provider),
) -> Proposal:
    """Propose values with their sources. NOTHING is saved; send the confirmed ones to /profile/confirm."""
    require_family(repo, family_id)
    member, primary = _member(repo, family_id, member_id)
    prop = await _propose(text, field, audio, file, stt)
    return prop.model_copy(update={"member_id": member, "ask_household": not primary})


async def _propose(
    text: str | None, field: Field | None, audio: UploadFile | None, file: UploadFile | None, stt: STTProvider
) -> Proposal:
    if audio is not None:
        ing = await ingest(
            text=None,
            audio=Upload(
                filename=audio.filename or "audio", data=await audio.read(), mime=audio.content_type or "audio/wav"
            ),
            files=[],
            stt=stt,
        )
        return extract_profile(ing.transcript, "voice", field=field, source_ref="voice answer")
    if file is not None:
        up = Upload(filename=file.filename or "file", data=await file.read(), mime=file.content_type or "")
        ing = await ingest(text=None, audio=None, files=[up], stt=None)
        return extract_profile(ing.doc_text, "document", field=field, source_ref=up.filename)
    if text:
        return await asyncio.to_thread(extract_profile, text, "typed", field=field)
    raise HTTPException(422, "send text, audio or a file")


@router.post("/families/{family_id}/profile/confirm")
def confirm(family_id: int, body: ConfirmIn, repo: Repo = Depends(get_repo)) -> dict[str, Any]:
    member, primary = _member(repo, family_id, body.member_id)
    saved, skipped = [], []
    for v in body.values:
        if v.confirmed and v.field in PROFILE_FIELDS:
            counted = primary if v.in_household is None or primary else v.in_household
            repo.set_profile_value(
                member, v.field, v.value, v.source, source_ref=v.source_ref, confirmed=True, in_household=counted
            )
            saved.append(v.field)
        else:
            skipped.append(v.field)
    for it in body.items:
        if it.confirmed:
            counted = primary if it.in_household is None or primary else it.in_household
            owner = member if get_settings().feature_members else None
            item = FamilyItem(**{**it.model_dump(), "in_household": counted, "member_id": owner})
            saved.append(f"item:{repo.save_item(family_id, item, confirmed=True)}")
        else:
            skipped.append(f"item:{it.name}")
    return {"saved": saved, "skipped": skipped, "profile": tools.family_get_profile(family_id, repo)}
