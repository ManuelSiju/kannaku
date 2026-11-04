"""GET /health (liveness + which providers are configured, no secrets) and GET /ready (DB and LLM reachable)."""

from __future__ import annotations

import importlib.util
from typing import Any

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import VERSION, get_settings
from app.providers import ocr

router = APIRouter()


async def llm_status() -> dict[str, Any]:
    s = get_settings()
    out: dict[str, Any] = {
        "provider": s.llm_provider,
        "base_url": s.llm_base_url,
        "model": s.llm_model,
        "vision": s.llm_vision_enabled,
    }
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(
                f"{s.llm_base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {s.llm_api_key.get_secret_value()}"},
            )
        out["reachable"] = r.status_code < 400 or (r.status_code < 500 and not s.meta)
        if s.meta and r.status_code in (401, 403):
            out["error"] = "key rejected"
        if r.status_code == 200 and "data" in r.json():
            # The server is up; also say whether the configured model is actually there.
            ids = {m.get("id") for m in r.json()["data"]}
            out["model_available"] = s.llm_model in ids
            if not out["model_available"]:
                out["error"] = "model not pulled: make llm-pull"
    except httpx.HTTPError as e:
        out["reachable"] = False
        out["error"] = f"{type(e).__name__}: " + ("no internet?" if s.meta else "start it with make llm-up")
    return out


def stt_status() -> dict[str, Any]:
    s = get_settings()
    if s.stt_provider == "meta":
        return {"provider": "meta", "reachable": False, "error": "not implemented yet"}
    out = {
        "provider": "faster_whisper",
        "model": s.whisper_model,
        "reachable": importlib.util.find_spec("faster_whisper") is not None,
    }
    if s.meta:
        out["note"] = "local faster-whisper: the Meta speech endpoint is not confirmed yet"
    return out


def provider_summary() -> dict[str, Any]:
    """What the app shows on Settings / Under the hood, and what make up prints. Never contains a secret."""
    from app.api.deps import get_llm_provider
    from app.providers.guard import GuardedLLM

    s = get_settings()
    llm = get_llm_provider()
    guard = llm.guard.status() if isinstance(llm, GuardedLLM) else None
    return {
        "name": s.llm_provider,
        "model": s.llm_model,
        "vision_model": (s.llm_vision_model or s.llm_model) if s.llm_vision_enabled else None,
        "stt": "faster-whisper (local)" if s.stt_provider == "faster_whisper" else s.stt_provider,
        "cache": bool(s.meta and s.llm_cache),
        "spend_guard": guard,
        "fallback": s.llm_fallback if s.meta else "none",
        "auth": bool(s.kanakku_token.get_secret_value()),
        "features": {"trace_export": s.feature_trace_export},
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
    return {"status": "ok", "version": VERSION, "provider": provider_summary(), "providers": providers}


@router.get("/ready")
async def ready() -> JSONResponse:
    from app.api.deps import get_repo

    checks: dict[str, Any] = {}
    try:
        checks["db"] = {"ok": get_repo().ping()}
    except Exception as e:
        checks["db"] = {"ok": False, "error": type(e).__name__}
    llm = await llm_status()
    checks["llm"] = {"ok": bool(llm.get("reachable")), **({"error": llm["error"]} if "error" in llm else {})}
    ok = all(c["ok"] for c in checks.values())
    return JSONResponse({"ready": ok, "version": VERSION, "checks": checks}, status_code=200 if ok else 503)
