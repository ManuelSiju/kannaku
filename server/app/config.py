"""All runtime settings, read from environment variables / .env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = REPO_ROOT / "server"
RUN_DIR = REPO_ROOT / "run"
VERSION = "0.2.0"
META_BASE_URL = "https://api.meta.ai/v1"
META_MODEL = "muse-spark-1.3"


Effort = Literal["minimal", "low", "medium", "high"]


class Settings(BaseSettings):
    # .env.local (gitignored, mode 600) holds secrets written by `make up`: META_API_KEY, KANAKKU_TOKEN.
    model_config = SettingsConfigDict(env_file=(REPO_ROOT / ".env", REPO_ROOT / ".env.local"), extra="ignore")

    # "local" = the LLM_* settings below (Ollama / llama-server); "meta" = Meta Model API (set by `make up`);
    # "replay" = recorded real Meta replies from replay_dir, no key needed (make demo-replay).
    llm_provider: Literal["local", "meta", "replay"] = "local"
    llm_base_url: str = "http://localhost:8080/v1"
    llm_api_key: SecretStr = SecretStr("local")
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
    meta_api_key: SecretStr = SecretStr("")
    meta_base_url: str = META_BASE_URL
    meta_model: str = META_MODEL
    meta_stt_url: str = META_BASE_URL + "/asr/transcribe"
    meta_stt_model: str = "muse-voice-transcribe-1.0"
    meta_stt_timeout_s: float = 30.0
    # Muse Spark is a reasoning model: at its default effort the bigger steps run past llm_timeout_s.
    meta_reasoning_effort: Effort = "minimal"
    # Per pipeline step; empty = meta_reasoning_effort. See docs/reports/meta_run.md for why each is set.
    meta_effort_case_builder: Effort | None = None
    meta_effort_council: Effort | None = None
    meta_effort_debate: Effort | None = None
    meta_effort_explainer: Effort | None = None
    # Meta only: response cache and a daily call cap (counter kept in SQLite). LLM_FALLBACK=local answers with the
    # local models once the cap is reached (shown as a "local fallback" badge and in the trace); none = fail fast.
    llm_cache: bool = True
    meta_max_calls_per_day: int = 300
    llm_fallback: Literal["none", "local"] = "none"
    # local model settings kept for the fallback (filled from LLM_* before the Meta values replace them)
    local_base_url: str = ""
    local_model: str = ""
    local_vision_enabled: bool | None = None
    local_vision_model: str = ""

    # Features added after the demo-safe tag; with all four off the answers match that tag.
    feature_members: bool = True
    feature_holdings: bool = True
    feature_trace_export: bool = True
    feature_snapshot: bool = True
    feature_meta_stt: bool = True  # on Meta, speech goes to Muse Voice Transcribe, with Whisper as the fallback

    # LAN access token: every request except /health needs "Authorization: Bearer <token>" when it is set.
    kanakku_token: SecretStr = SecretStr("")
    # request limits
    max_audio_mb: float = 10
    max_image_mb: float = 8
    max_pdf_mb: float = 15
    max_files: int = 5
    request_timeout_s: float = 180
    asks_per_minute: int = 20
    shutdown_grace_s: float = 15
    log_path: Path = RUN_DIR / "server.log"
    backup_dir: Path = RUN_DIR / "backups"
    backups_kept: int = 3
    reference_rates_path: Path = SERVER_ROOT / "data" / "reference_rates.json"
    replay_dir: Path = SERVER_ROOT / "demo_assets" / "replay"

    @field_validator("db_path", "reference_rates_path", "log_path", "backup_dir")
    @classmethod
    def _relative_to_repo(cls, v: Path) -> Path:
        # Relative paths in .env are relative to the repo root, not the working directory.
        return v if v.is_absolute() else REPO_ROOT / v

    @model_validator(mode="after")
    def _provider(self) -> "Settings":
        self.local_base_url = self.local_base_url or self.llm_base_url
        self.local_model = self.local_model or self.llm_model
        if self.local_vision_enabled is None:
            self.local_vision_enabled, self.local_vision_model = self.llm_vision_enabled, self.llm_vision_model
        if self.llm_provider == "meta":
            if not self.meta_api_key.get_secret_value():
                raise ValueError("LLM_PROVIDER=meta needs META_API_KEY (run make up and type the key, or set it)")
            self.llm_base_url, self.llm_model, self.llm_api_key = self.meta_base_url, self.meta_model, self.meta_api_key
            self.llm_vision_enabled, self.llm_vision_model = True, ""
        if self.llm_provider == "replay":  # the recording's keys hold the Meta model and its vision setting
            self.llm_model, self.llm_vision_enabled, self.llm_vision_model = self.meta_model, True, ""
        if self.meta_max_calls_per_day < 1 or self.llm_timeout_s <= 0 or self.llm_max_calls_per_ask < 1:
            raise ValueError("META_MAX_CALLS_PER_DAY, LLM_TIMEOUT_S and LLM_MAX_CALLS_PER_ASK must be positive")
        return self

    @property
    def meta(self) -> bool:
        return self.llm_provider == "meta"

    def reasoning_effort(self, step: str | None) -> str:
        return getattr(self, f"meta_effort_{step}", None) or self.meta_reasoning_effort

    def local_settings(self) -> "Settings":
        """The same settings pointed at the local models (for LLM_FALLBACK=local)."""
        return self.model_copy(
            update={
                "llm_provider": "local",
                "llm_base_url": self.local_base_url,
                "llm_model": self.local_model,
                "llm_api_key": SecretStr("local"),
                "llm_vision_enabled": bool(self.local_vision_enabled),
                "llm_vision_model": self.local_vision_model,
            }
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
