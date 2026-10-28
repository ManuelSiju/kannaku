from types import SimpleNamespace

import pytest

from app.providers import stt as stt_mod
from app.providers.stt import FasterWhisperSTT, MetaTranscribeSTT, get_stt
from app.providers.tts import DeviceTTS, NoopTTS, get_tts


def test_stt_factory(settings):
    assert isinstance(get_stt(settings), FasterWhisperSTT)
    assert isinstance(get_stt(settings.model_copy(update={"stt_provider": "meta"})), MetaTranscribeSTT)


async def test_meta_stt_stub_raises_clearly():
    with pytest.raises(NotImplementedError, match="STT_PROVIDER=faster_whisper"):
        await MetaTranscribeSTT().transcribe(b"", "audio/wav")


async def test_faster_whisper_with_mocked_model(settings):
    class FakeModel:
        def transcribe(self, path, vad_filter):
            segs = [
                SimpleNamespace(start=0.0, end=1.2, text=" ഒന്നര ലക്ഷം "),
                SimpleNamespace(start=1.2, end=2.0, text="premium"),
            ]
            return iter(segs), SimpleNamespace(language="ml")

    provider = FasterWhisperSTT(settings)
    provider._model = FakeModel()
    t = await provider.transcribe(b"RIFF....", "audio/wav")
    assert t.language == "ml"
    assert t.text == "ഒന്നര ലക്ഷം premium"
    assert t.segments[0].speaker is None
    assert stt_mod.Transcript.model_validate(t.model_dump()) == t


async def test_tts(settings):
    assert isinstance(get_tts(settings), DeviceTTS)
    assert isinstance(get_tts(settings.model_copy(update={"tts_provider": "none"})), NoopTTS)
    assert await DeviceTTS().synthesize("hello") is None


async def test_faster_whisper_falls_back_to_cpu_when_cuda_libs_missing(settings, monkeypatch):
    provider = FasterWhisperSTT(settings)
    calls = []

    def fake_run(audio, mime):
        calls.append(provider._force_cpu)
        if not provider._force_cpu:
            raise RuntimeError("Library libcublas.so.12 is not found or cannot be loaded")
        return stt_mod.Transcript(text="ok", language="en", segments=[])

    monkeypatch.setattr(provider, "_run", fake_run)
    t = await provider.transcribe(b"", "audio/wav")
    assert t.text == "ok" and calls == [False, True]
    assert provider._device() == ("cpu", "int8")
