"""GET /health: which providers are configured and whether each is reachable."""

from __future__ import annotations

import importlib.util
from typing import Any

import httpx
from fastapi import APIRouter

from app.config import get_settings
from app.providers import ocr

router = APIRouter()


async def llm_status() -> dict[str, Any]:
    s = get_settings()
    out: dict[str, Any] = {
        "provider": "openai_compatible",
        "base_url": s.llm_base_url,
        "model": s.llm_model,
        "vision": s.llm_vision_enabled,
    }
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(
                f"{s.llm_base_url.rstrip('/')}/models", headers={"Authorization": f"Bearer {s.llm_api_key}"}
            )
        out["reachable"] = r.status_code < 500
        if r.status_code == 200 and "data" in r.json():
            # The server is up; also say whether the configured model is actually there.
            ids = {m.get("id") for m in r.json()["data"]}
            out["model_available"] = s.llm_model in ids
            if not out["model_available"]:
                out["error"] = "model not pulled: make llm-pull"
    except httpx.HTTPError as e:
        out["reachable"] = False
        out["error"] = f"{type(e).__name__}: start it with make llm-up"
    return out


def stt_status() -> dict[str, Any]:
    s = get_settings()
    if s.stt_provider == "meta":
        return {"provider": "meta", "reachable": False, "error": "not implemented yet"}
    return {
        "provider": "faster_whisper",
        "model": s.whisper_model,
        "reachable": importlib.util.find_spec("faster_whisper") is not None,
    }


def ocr_status() -> dict[str, Any]:
    s = get_settings()
    try:
        return {"provider": "tesseract", "reachable": True, "langs": ocr.resolve_langs(s.ocr_langs)}
    except ocr.OcrUnavailable as e:
        return {"provider": "tesseract", "reachable": False, "error": str(e)}


def tts_status() -> dict[str, Any]:
    return {"provider": get_settings().tts_provider, "reachable": True}


@router.get("/health")
async def health() -> dict[str, Any]:
    providers = {"llm": await llm_status(), "stt": stt_status(), "ocr": ocr_status(), "tts": tts_status()}
    return {"status": "ok", "providers": providers}
