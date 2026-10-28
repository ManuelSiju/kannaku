"""Text-to-speech providers. For now the app speaks on-device (flutter_tts); the server returns text."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.config import Settings, get_settings


class TTSProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def synthesize(self, text: str, voice: str | None = None) -> bytes | None:
        """Return audio bytes, or None when the client is expected to speak the text itself."""


class DeviceTTS(TTSProvider):
    name = "device"

    async def synthesize(self, text: str, voice: str | None = None) -> bytes | None:
        return None


class NoopTTS(TTSProvider):
    name = "none"

    async def synthesize(self, text: str, voice: str | None = None) -> bytes | None:
        return None


def get_tts(settings: Settings | None = None) -> TTSProvider:
    settings = settings or get_settings()
    return DeviceTTS() if settings.tts_provider == "device" else NoopTTS()
