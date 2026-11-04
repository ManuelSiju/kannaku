"""The demo cases once each on the real Meta Model API, with the model id each reply gave. Run: make meta-run
Writes docs/reports/meta_run.md. Needs META_API_KEY (environment or .env.local); the key is never printed.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))

ASSETS = SERVER / "demo_assets"
ENDOWMENT_Q = "An agent from the company says this plan is guaranteed to give 15 lakh. Should I take it?"
CASES = [
    ("endowment PDF", ENDOWMENT_Q, ["kanakavalli_brochure.pdf"]),
    (
        "endowment brochure PNG (vision)",
        ENDOWMENT_Q,
        ["kanakavalli_brochure_p1.png", "kanakavalli_brochure_p2.png", "kanakavalli_brochure_p3.png"],
    ),
    (
        "flat loan",
        "A finance company is offering me a loan of 1,00,000 at 12% flat for 24 months. Should I take it?",
        [],
    ),
    (
        "ZEPHYRX tip",
        "I got this message: ZEPHYRX LTD - BIG NEWS COMING! Target Rs. 180 in 2 weeks. Upper circuit guaranteed. "
        "Should I put 1 lakh in it?",
        [],
    ),
    ("OTP scam", "A man from the bank called. My KYC has expired and he asks me to tell him the OTP.", []),
    ("out of scope", "How do I make sambar?", []),
]


NOTES = """
## Settings and what was tried

- **Reasoning effort: `minimal` on every step**, from [effort_matrix.md](effort_matrix.md). `low` and `high` on the
  council or explainer run past the 20 s limit, so steps degrade. Only `minimal` gave 6 of 6 expected verdicts with no
  degraded run.
- **Structured output: `json_object`.** On the same explainer request `json_schema` ran to the token limit.
- **Muse Voice Transcribe: used on Meta**, with keyword biasing for words like lakh, EMI and the council's names, and
  local faster-whisper as the automatic fallback. The trace records which path ran. It can repeat a word or digit.
- **SAM 3.1: not tried.** It is listed by `GET /models`; nothing in Kanakku calls it.
"""


def main() -> int:
    from app.config import REPO_ROOT, Settings

    if not Settings().meta_api_key.get_secret_value():
        print("Meta run skipped: no key")
        return 0
    tmp = tempfile.mkdtemp(prefix="kanakku-meta-run-")
    settings = Settings(llm_provider="meta", db_path=Path(tmp) / "k.db", llm_cache=False)

    from app.db.repo import Repo
    from app.db.seed_demo import seed
    from app.pipeline.events import EventBus
    from app.pipeline.ingest import Upload
    from app.pipeline.run import AskInput, run_pipeline
    from app.providers.llm import OpenAICompatibleLLM, get_llm
    from app.providers.stt import get_stt

    repo = Repo(settings.db_path)
    seed(repo)
    rows, details = [], []
    facts: dict[str, list] = {}
    spoken: dict[str, list[str]] = {}
    for name, question, files in CASES:
        uploads = [
            Upload(
                filename=f, data=(ASSETS / f).read_bytes(), mime="application/pdf" if f.endswith("pdf") else "image/png"
            )
            for f in files
        ]
        llm = get_llm(settings)
        inner = llm if isinstance(llm, OpenAICompatibleLLM) else llm.inner
        started = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        t0 = time.monotonic()
        case_id = repo.create_case(1)
        res = asyncio.run(
            run_pipeline(
                case_id,
                AskInput(family_id=1, text=question, files=uploads),
                repo=repo, llm=llm, stt=None, settings=settings, bus=EventBus(),
            )
        )  # fmt: skip
        secs = time.monotonic() - t0
        models = ", ".join(f"{m} x{n}" for m, n in inner.stats.models.items()) or "none (no model call)"
        degraded = ", ".join(res.degraded_steps) or "no"
        rows.append(
            f"| {name} | {case_id} | {started} | {models} | {res.verdict.colour} | {res.llm_calls} | {secs:.1f} s | "
            f"{degraded} |"
        )
        terms = [
            f"{t['name']}={t['value']} ({'kept' if t['verified'] else t['reason']})" for t in repo.get_terms(case_id)
        ]
        sources = sorted({d.source for d in res.screen_details if d.id.startswith("term.")})
        details.append(f"### {name}\n\n- Answer: {res.short_answer.text if res.short_answer else ''}")
        details.append(f"- Terms: {'; '.join(terms) or 'none'}\n- Term sources shown: {'; '.join(sources) or 'none'}\n")
        facts[name] = [
            {"id": f.id, "value": f.value, "unit": f.unit, "display": f.display} for f in repo.get_facts(case_id)
        ]
        spoken[name] = [line.text for line in res.spoken_lines]
        print(rows[-1], flush=True)
    speech = (ASSETS / "sample_speech.wav").read_bytes()
    t0 = time.monotonic()
    heard = asyncio.run(get_stt(settings).transcribe(speech, "audio/wav"))
    details.append(
        f"### Speech, 25 s of recorded audio\n\n- Path: {heard.engine}, model {settings.meta_stt_model}, "
        f"{time.monotonic() - t0:.1f} s\n- Heard: {heard.text}\n"
    )
    out = REPO_ROOT / "docs" / "reports" / "meta_run.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    head = (
        "# Meta run\n\nThe model id below is the one each Meta reply returned, not the configured value. "
        f"Reasoning effort: {settings.meta_reasoning_effort}. Limit: {settings.llm_timeout_s:g} s per call "
        f"({settings.llm_vision_timeout_s:g} s with images).\n\n"
        "| case | trace (case id) | started (UTC) | model id returned | verdict | model calls | total | degraded |\n"
        "|---|---|---|---|---|---|---|---|\n"
    )
    out.write_text(head + "\n".join(rows) + "\n\n" + "\n".join(details) + NOTES)
    (out.parent / "meta_run_facts.json").write_text(
        json.dumps({"facts": facts, "spoken": spoken}, indent=1, ensure_ascii=False)
    )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
