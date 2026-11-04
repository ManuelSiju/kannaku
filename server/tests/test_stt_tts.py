import io
import wave
from types import SimpleNamespace

import httpx

from app.config import SERVER_ROOT, Settings
from app.providers import stt as stt_mod
from app.providers.stt import FasterWhisperSTT, MetaTranscribeSTT, get_stt, to_wav
from app.providers.tts import DeviceTTS, NoopTTS, get_tts
from tests.fakes import FakeSTT


def test_stt_factory(settings):
    assert isinstance(get_stt(settings), FasterWhisperSTT)
    assert isinstance(get_stt(settings.model_copy(update={"stt_provider": "meta"})), MetaTranscribeSTT)


def meta_settings(**kw):
    return Settings(_env_file=None, llm_provider="meta", meta_api_key="k", **kw)


def stt_with(reply, fallback=None):
    seen = {}

    def handler(request):
        seen["request"] = request
        return reply

    return MetaTranscribeSTT(meta_settings(), fallback, httpx.MockTransport(handler)), seen


SPEECH = (SERVER_ROOT / "demo_assets" / "sample_speech.wav").read_bytes()


def test_on_meta_speech_goes_to_muse_voice_transcribe_with_whisper_behind_it():
    stt = get_stt(meta_settings())
    assert isinstance(stt, MetaTranscribeSTT) and isinstance(stt.fallback, FasterWhisperSTT)
    assert isinstance(get_stt(meta_settings(feature_meta_stt=False)), FasterWhisperSTT)


async def test_meta_stt_sends_the_documented_request():
    stt, seen = stt_with(httpx.Response(200, json={"transcript": " Only 7.5 lakh. ", "turns": []}))
    out = await stt.transcribe(SPEECH, "audio/wav")
    assert (out.text, out.engine) == ("Only 7.5 lakh.", "meta")
    sent = seen["request"]
    assert sent.url.path == "/v1/asr/transcribe" and sent.headers["authorization"] == "Bearer k"
    body = sent.read()
    assert b'"audioEncoding": "WAV"' in body and b'"mode": "PUSH_TO_TALK"' in body and b"Kanakku" in body
    assert b'name="audio"' in body and b"RIFF" in body


async def test_meta_stt_failure_falls_back_to_whisper_and_says_so():
    stt, _ = stt_with(httpx.Response(500, json={}), FakeSTT("My salary is 52,000."))
    out = await stt.transcribe(SPEECH, "audio/wav")
    assert out.text == "My salary is 52,000."
    assert out.engine == "whisper (fallback: RuntimeError: HTTP 500)"


async def test_meta_stt_error_never_carries_the_key():
    stt, _ = stt_with(httpx.Response(401, json={}), FakeSTT("x"))
    assert (await stt.transcribe(SPEECH, "audio/wav")).engine == "whisper (fallback: RuntimeError: HTTP 401)"


def test_any_recording_becomes_16_khz_mono_wav():
    wav = wave.open(io.BytesIO(to_wav(SPEECH)))
    assert (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) == (16000, 1, 2)
    assert wav.getnframes() > 16000


async def test_faster_whisper_with_mocked_model(settings):
    class FakeModel:
        def transcribe(self, path, language, vad_filter):
            assert language == "en"
            segs = [
                SimpleNamespace(start=0.0, end=1.2, text=" one and a half lakh "),
                SimpleNamespace(start=1.2, end=2.0, text="premium"),
            ]
            return iter(segs), SimpleNamespace(language="en")

    provider = FasterWhisperSTT(settings)
    provider._model = FakeModel()
    t = await provider.transcribe(b"RIFF....", "audio/wav")
    assert t.language == "en"
    assert t.text == "one and a half lakh premium"
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
