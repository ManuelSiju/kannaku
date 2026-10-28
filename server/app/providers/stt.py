"""Speech-to-text providers. Local faster-whisper now; Meta Muse Voice Transcribe later."""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import re
import tempfile
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from app.config import Settings, get_settings

log = logging.getLogger(__name__)


class Segment(BaseModel):
    start: float
    end: float
    text: str
    speaker: str | None = None  # whisper has no diarization; kept for providers that do


class Transcript(BaseModel):
    text: str
    language: str | None
    segments: list[Segment]


class STTProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, mime: str) -> Transcript: ...


class FasterWhisperSTT(STTProvider):
    """Local faster-whisper. Language auto-detected (Malayalam / English / Hindi all supported)."""

    name = "faster_whisper"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._model: Any = None
        self._force_cpu = False

    def _device(self) -> tuple[str, str]:
        device = "cpu" if self._force_cpu else self.settings.whisper_device
        if device == "auto":
            try:
                import ctranslate2

                device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
            except Exception:
                device = "cpu"
        return device, ("float16" if device == "cuda" else "int8")

    def _load(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel

            device, compute_type = self._device()
            log.info("Loading whisper %s on %s (%s)", self.settings.whisper_model, device, compute_type)
            self._model = WhisperModel(self.settings.whisper_model, device=device, compute_type=compute_type)
        return self._model

    def _transcribe_sync(self, audio_bytes: bytes, mime: str) -> Transcript:
        try:
            return self._run(audio_bytes, mime)
        except RuntimeError as e:
            # A GPU may be visible while CUDA libraries (cuBLAS/cuDNN) are not installed: fall back to CPU.
            if self.settings.whisper_device != "auto" or not re.search(r"cu(blas|dnn|da)", str(e), re.I):
                raise
            log.warning("Whisper on GPU failed (%s); falling back to CPU", e)
            self._force_cpu = True
            self._model = None
            return self._run(audio_bytes, mime)

    def _run(self, audio_bytes: bytes, mime: str) -> Transcript:
        suffix = mimetypes.guess_extension(mime.split(";")[0].strip()) or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix) as f:
            f.write(audio_bytes)
            f.flush()
            segments, info = self._load().transcribe(f.name, vad_filter=True)
            segs = [Segment(start=s.start, end=s.end, text=s.text.strip()) for s in segments]
        return Transcript(text=" ".join(s.text for s in segs).strip(), language=info.language, segments=segs)

    async def transcribe(self, audio_bytes: bytes, mime: str) -> Transcript:
        return await asyncio.to_thread(self._transcribe_sync, audio_bytes, mime)


class MetaTranscribeSTT(STTProvider):
    name = "meta"

    async def transcribe(self, audio_bytes: bytes, mime: str) -> Transcript:
        raise NotImplementedError(
            "Meta Muse Voice Transcribe is not wired yet (endpoint format unconfirmed). "
            "Set STT_PROVIDER=faster_whisper."
        )


def get_stt(settings: Settings | None = None) -> STTProvider:
    settings = settings or get_settings()
    if settings.stt_provider == "meta":
        return MetaTranscribeSTT()
    return FasterWhisperSTT(settings)
