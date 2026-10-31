"""All runtime settings, read from environment variables / .env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = REPO_ROOT / "server"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    llm_base_url: str = "http://localhost:8080/v1"
    llm_api_key: str = "local"
    llm_model: str = "local-model"
    llm_vision_enabled: bool = False
    llm_vision_model: str = ""  # optional separate model for calls that carry images (e.g. qwen2.5vl:7b)
    llm_temperature: float = 0.2
    llm_vision_timeout_s: float = 60.0  # local vision models are slow; text calls keep llm_timeout_s
    llm_image_max_side: int = (
        1024  # pages are shrunk to this long side before they go to the model (OCR uses full size)
    )
    llm_timeout_s: float = 20.0
    llm_max_calls_per_ask: int = 4

    stt_provider: Literal["faster_whisper", "meta"] = "faster_whisper"
    whisper_model: str = "medium"
    whisper_device: str = "auto"
    # English only while testing; empty = auto-detect (multilingual comes later).
    stt_language: str = "en"

    tts_provider: Literal["device", "none"] = "device"

    ocr_langs: str = "eng"

    db_path: Path = SERVER_ROOT / "kanakku.db"
    meta_api_key: str = ""
    reference_rates_path: Path = SERVER_ROOT / "data" / "reference_rates.json"

    @field_validator("db_path", "reference_rates_path")
    @classmethod
    def _relative_to_repo(cls, v: Path) -> Path:
        # Relative paths in .env are relative to the repo root, not the working directory.
        return v if v.is_absolute() else REPO_ROOT / v


@lru_cache
def get_settings() -> Settings:
    return Settings()
