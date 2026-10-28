"""Smoke-test every model provider once and print PASS / FAIL / SKIP with timings. Never crashes."""

from __future__ import annotations

import asyncio
import math
import struct
import sys
import time
import traceback
import wave
from collections.abc import Awaitable, Callable
from pathlib import Path

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import SERVER_ROOT, get_settings  # noqa: E402
from app.providers.llm import get_llm  # noqa: E402
from app.providers.ocr import ocr_image  # noqa: E402
from app.providers.stt import get_stt  # noqa: E402

ASSETS = SERVER_ROOT / "demo_assets"
WAV = ASSETS / "sample_ml_en.wav"
PNG = ASSETS / "sample_brochure.png"


def ensure_placeholders() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    if not PNG.exists():
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (1200, 400), "white")
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 40)
        except OSError:
            font = ImageFont.load_default()
        draw.text((40, 60), "Sample Plan Brochure (placeholder)", fill="black", font=font)
        draw.text((40, 160), "Annual premium: Rs. 50,000", fill="black", font=font)
        draw.text((40, 240), "Policy term: 15 years", fill="black", font=font)
        img.save(PNG)
        print(f"  created placeholder {PNG.relative_to(SERVER_ROOT)} (replace with a real fictional brochure)")
    if not WAV.exists():
        rate = 16000
        with wave.open(str(WAV), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            frames = b"".join(
                struct.pack("<h", int(3000 * math.sin(2 * math.pi * 440 * i / rate))) for i in range(rate)
            )
            w.writeframes(frames)
        print(f"  created placeholder {WAV.relative_to(SERVER_ROOT)} (1 s tone; record real speech for a real test)")


class Ping(BaseModel):
    answer: str
    number: int


async def check_llm_json() -> str:
    out, usage = await get_llm().chat_json("You are a test.", 'Reply with answer="ok" and number=7.', Ping)
    return f"{out.model_dump()} tokens={usage.prompt_tokens}/{usage.completion_tokens}"


async def check_llm_image() -> str:
    text, _ = await get_llm().chat_text("Describe briefly.", "What text is in this image?", [PNG.read_bytes()])
    return text[:80].replace("\n", " ")


async def check_stt() -> str:
    t = await get_stt().transcribe(WAV.read_bytes(), "audio/wav")
    return f"lang={t.language} text={t.text[:60]!r}"


async def check_ocr() -> str:
    r = await asyncio.to_thread(ocr_image, PNG.read_bytes())
    return f"langs={r.langs} conf={r.mean_confidence} text={r.text[:60]!r}"


async def run(name: str, fn: Callable[[], Awaitable[str]], verbose: bool) -> bool:
    t0 = time.perf_counter()
    try:
        detail = await fn()
        ok = True
    except Exception as e:
        detail = f"{type(e).__name__}: {e}"
        ok = False
        if verbose:
            traceback.print_exc()
    ms = (time.perf_counter() - t0) * 1000
    print(f"  {'PASS' if ok else 'FAIL'}  {name:<12} {ms:8.0f} ms  {detail}")
    return ok


async def main() -> None:
    verbose = "-v" in sys.argv
    s = get_settings()
    print(f"Kanakku model check  (LLM {s.llm_model} @ {s.llm_base_url}, STT {s.stt_provider}/{s.whisper_model})")
    ensure_placeholders()
    results = [await run("llm-json", check_llm_json, verbose)]
    if s.llm_vision_enabled:
        results.append(await run("llm-image", check_llm_image, verbose))
    else:
        print(f"  SKIP  {'llm-image':<12} {'':>11}  LLM_VISION_ENABLED=false")
    results.append(await run("stt", check_stt, verbose))
    results.append(await run("ocr", check_ocr, verbose))
    print(f"{sum(results)}/{len(results)} checks passed")


if __name__ == "__main__":
    asyncio.run(main())
