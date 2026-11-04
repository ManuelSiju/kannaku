"""Guardian alerts: GET /families/{id}/alerts, PATCH /alerts/{id}."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_repo, require_family
from app.db.repo import Repo

router = APIRouter(tags=["alerts"])


class AlertPatch(BaseModel):
    status: Literal["new", "handled"] | None = None
    note: str | None = None  # the guardian's note for Amma


@router.get("/families/{family_id}/notes")
def guardian_notes(family_id: int, repo: Repo = Depends(get_repo)) -> list[dict[str, Any]]:
    """Notes the guardian left for Amma, newest first (her Home screen shows "A note from <guardian>")."""
    require_family(repo, family_id)
    guardian = next((m["name"] for m in repo.members(family_id) if m["role"] == "guardian"), "your family")
    return [
        {
            "alert_id": a["id"],
            "case_id": a["case_id"],
            "from": guardian,
            "note": a["guardian_note"],
            "at": a["noted_at"],
        }
        for a in sorted(repo.list_alerts(family_id), key=lambda a: a.get("noted_at") or "", reverse=True)
        if a.get("guardian_note")
    ]


@router.get("/families/{family_id}/alerts")
def list_alerts(
    family_id: int, status: Literal["new", "handled"] | None = None, repo: Repo = Depends(get_repo)
) -> list[dict[str, Any]]:
    require_family(repo, family_id)
    out = []
    for a in repo.list_alerts(family_id, status):
        bundle = repo.case_bundle(a["case_id"]) or {}
        verdict = bundle.get("verdict") or {}
        out.append(
            a
            | {
                "case_type": bundle.get("case", {}).get("case_type"),
                "colour": verdict.get("colour"),
                "sentence": verdict.get("sentence"),
                "key_facts": [
                    f
                    for f in bundle.get("facts", [])
                    if f["kind"] == "offer" and f["value"] is not None and not f["id"].startswith(("ref.", "cmp_"))
                ][:4],
                "agent_lines": [ln for ln in bundle.get("spoken_lines", []) if ln["speaker"] != "alfii"],
            }
        )
    return out


@router.patch("/alerts/{alert_id}")
def patch_alert(alert_id: int, body: AlertPatch, repo: Repo = Depends(get_repo)) -> dict[str, bool]:
    if not repo.update_alert(alert_id, status=body.status, note=body.note):
        raise HTTPException(404, f"alert {alert_id} not found or nothing to change")
    return {"updated": True}
