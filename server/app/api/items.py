"""GET/POST/DELETE /families/{id}/items."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_repo, require_family
from app.db.repo import FamilyItem, ItemKind, Repo
from app.mcp_server import tools

router = APIRouter(tags=["items"])


class SaveItemIn(BaseModel):
    item: FamilyItem
    confirmed: bool


@router.get("/families/{family_id}/items")
def list_items(family_id: int, kind: ItemKind | None = None, repo: Repo = Depends(get_repo)) -> dict[str, Any]:
    require_family(repo, family_id)
    return tools.family_list_items(family_id, kind, repo)


@router.post("/families/{family_id}/items")
def save_item(family_id: int, body: SaveItemIn, repo: Repo = Depends(get_repo)) -> dict[str, Any]:
    require_family(repo, family_id)
    out = tools.family_save_item(family_id, body.item.model_dump(), body.confirmed, repo)
    if not out["saved"]:
        raise HTTPException(422, out["reason"])
    return out


@router.delete("/families/{family_id}/items/{item_id}")
def delete_item(family_id: int, item_id: int, repo: Repo = Depends(get_repo)) -> dict[str, bool]:
    require_family(repo, family_id)
    if not repo.delete_item(family_id, item_id):
        raise HTTPException(404, f"item {item_id} not found")
    return {"deleted": True}
