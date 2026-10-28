"""Kanakku FastAPI app."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    s = get_settings()
    logging.getLogger("kanakku").info(
        "LLM %s @ %s | STT %s | TTS %s", s.llm_model, s.llm_base_url, s.stt_provider, s.tts_provider
    )
    yield


app = FastAPI(title="Kanakku", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
