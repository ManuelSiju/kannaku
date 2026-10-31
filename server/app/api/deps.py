"""Shared dependencies. Tests override these with app.dependency_overrides."""

from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException

from app.config import Settings, get_settings
from app.db.repo import Repo
from app.mcp_server.tools import default_repo
from app.pipeline.events import BUS, EventBus
from app.providers.llm import LLMProvider, get_llm
from app.providers.stt import STTProvider, get_stt


def get_repo() -> Repo:
    return default_repo()


@lru_cache
def _llm() -> LLMProvider:
    return get_llm()


def get_llm_provider() -> LLMProvider:
    return _llm()


@lru_cache
def _stt() -> STTProvider:
    return get_stt()


def get_stt_provider() -> STTProvider:
    return _stt()


def get_settings_dep() -> Settings:
    return get_settings()


def get_bus() -> EventBus:
    return BUS


def require_family(repo: Repo, family_id: int) -> None:
    if repo.get_family(family_id) is None:
        raise HTTPException(404, f"family {family_id} not found")
