"""Speech-to-text providers: Meta Muse Voice Transcribe, with local faster-whisper as fallback and local path."""

from __future__ import annotations

import asyncio
import io
import json
import logging
import mimetypes
import re
import tempfile
import wave
from abc import ABC, abstractmethod
from typing import Any

import httpx
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
    engine: str = "whisper"  # which path ran, for the trace: "meta" or "whisper (fallback: <reason>)"


class STTProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, mime: str) -> Transcript: ...


class FasterWhisperSTT(STTProvider):
    """Local faster-whisper. Language fixed by STT_LANGUAGE (en for now); empty = auto-detect."""

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
            language = self.settings.stt_language or None
            segments, info = self._load().transcribe(f.name, language=language, vad_filter=True)
            segs = [Segment(start=s.start, end=s.end, text=s.text.strip()) for s in segments]
        return Transcript(text=" ".join(s.text for s in segs).strip(), language=info.language, segments=segs)

    async def transcribe(self, audio_bytes: bytes, mime: str) -> Transcript:
        return await asyncio.to_thread(self._transcribe_sync, audio_bytes, mime)


# Words a family says that a general model hears wrongly; Muse Voice Transcribe biases recognition towards them.
STT_KEYWORDS = [
    "Kanakku",
    "Alfii",
    "Sankz",
    "Dani",
    "Vick",
    "lakh",
    "crore",
    "EMI",
    "SIP",
    "OTP",
    "KYC",
    "ULIP",
    "demat",
]


def to_wav(audio: bytes) -> bytes:
    """Any recording as the 16 kHz mono 16-bit WAV the file endpoint takes (the app records m4a)."""
    import av

    pcm = bytearray()
    with av.open(io.BytesIO(audio)) as source:
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        for frame in source.decode(audio=0):
            for out in resampler.resample(frame):
                pcm += out.to_ndarray().tobytes()
        for out in resampler.resample(None):
            pcm += out.to_ndarray().tobytes()
    data = io.BytesIO()
    with wave.open(data, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(bytes(pcm))
    return data.getvalue()


class MetaTranscribeSTT(STTProvider):
    """POST /v1/asr/transcribe. Any failure falls back to `fallback`, and the trace says so."""

    name = "meta"

    def __init__(
        self,
        settings: Settings | None = None,
        fallback: STTProvider | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.fallback = fallback
        self.transport = transport

    async def _ask(self, audio_bytes: bytes) -> Transcript:
        s = self.settings
        request: dict[str, Any] = {
            "mode": "PUSH_TO_TALK",
            "model": s.meta_stt_model,
            "audioEncoding": "WAV",
            "keywords": STT_KEYWORDS,
        }
        if s.stt_language:
            request["languageBias"] = [s.stt_language]
        wav = await asyncio.to_thread(to_wav, audio_bytes)
        async with httpx.AsyncClient(timeout=s.meta_stt_timeout_s, transport=self.transport) as client:
            r = await client.post(
                s.meta_stt_url,
                headers={"Authorization": f"Bearer {s.meta_api_key.get_secret_value()}"},
                files={"request": (None, json.dumps(request), "application/json"), "audio": ("audio.wav", wav)},
            )
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        body = r.json()
        turns = [
            Segment(start=t.get("startMs", 0) / 1000, end=t.get("endMs", 0) / 1000, text=t.get("transcript", ""))
            for t in body.get("turns") or []
        ]
        return Transcript(
            text=body.get("transcript", "").strip(), language=s.stt_language or None, segments=turns, engine="meta"
        )

    async def transcribe(self, audio_bytes: bytes, mime: str) -> Transcript:
        try:
            heard = await self._ask(audio_bytes)
            if heard.text or self.fallback is None:
                return heard
            reason = "empty transcript"
        except Exception as e:
            if self.fallback is None:
                raise
            reason = f"{type(e).__name__}: {e}"[:80]
        log.warning("Muse Voice Transcribe gave nothing (%s); using the fallback", reason)
        out = await self.fallback.transcribe(audio_bytes, mime)
        return out.model_copy(update={"engine": f"whisper (fallback: {reason})"})


def get_stt(settings: Settings | None = None) -> STTProvider:
    settings = settings or get_settings()
    whisper = FasterWhisperSTT(settings)
    if settings.stt_provider == "meta" or (settings.meta and settings.feature_meta_stt):
        return MetaTranscribeSTT(settings, fallback=whisper)
    return whisper
