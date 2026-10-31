"""Reliability runs against the REAL configured LLM (not fixtures).

  python scripts/reliability.py --runs 5                 # 5 acceptance cases x N runs
  python scripts/reliability.py --framing --runs 3       # 3 framings of the endowment case x N runs
  python scripts/reliability.py --vision --runs 3        # endowment from the brochure PHOTOS with a vision model

Each run uses a fresh seeded database in a temp dir. Writes docs/reliability*.md (+ raw JSON).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import REPO_ROOT, SERVER_ROOT, get_settings  # noqa: E402
from app.db.repo import Repo  # noqa: E402
from app.db.seed_demo import seed  # noqa: E402
from app.pipeline.events import EventBus  # noqa: E402
from app.pipeline.ingest import Upload  # noqa: E402
from app.pipeline.run import AskInput, run_pipeline  # noqa: E402
from app.providers.llm import OpenAICompatibleLLM  # noqa: E402

ASSETS = SERVER_ROOT / "demo_assets"
PDF = Upload(filename="brochure.pdf", data=(ASSETS / "kanakavalli_brochure.pdf").read_bytes(), mime="application/pdf")
PHOTOS = [
    Upload(filename=f"p{i}.png", data=(ASSETS / f"kanakavalli_brochure_p{i}.png").read_bytes(), mime="image/png")
    for i in (1, 2, 3)
]
CASES: dict[str, dict[str, Any]] = {
    "endowment": {
        "text": "An agent from the company says this plan is guaranteed to give 15 lakh. Should I take it?",
        "files": [PDF],
        "expect": {"red"},
    },
    "flat_loan": {
        "text": "A finance company is offering me a loan of 1,00,000 at 12% flat for 24 months. Should I take it?",
        "files": [],
        "expect": {"red", "yellow"},
    },
    "stock_tip": {
        "text": "I got this message: ZEPHYRX LTD - BIG NEWS COMING! Target Rs. 180 in 2 weeks. Upper circuit "
        "guaranteed. Should I put 1 lakh in it?",
        "files": [],
        "expect": {"red"},
    },
    "otp_scam": {
        "text": "A man from the bank called. My KYC has expired and he asks me to tell him the OTP.",
        "files": [],
        "expect": {"red"},
    },
    "out_of_scope": {"text": "Can you tell me a good recipe for sambar?", "files": [], "expect": {None}},
}
FRAMINGS = {
    "neutral": "Is this plan good for me?",
    "seller_positive": (
        "The agent says this is the best guaranteed plan and I must sign today. It is a good plan, right?"
    ),
    "user_negative": "My neighbour says these plans are a waste of money. I should avoid it, no?",
}
STEPS = [
    "ingest",
    "scam_rules",
    "case_builder",
    "verify_terms",
    "compute",
    "router",
    "council",
    "debate",
    "consensus",
    "explainer",
]


async def one_run(text: str, files: list[Upload], llm: OpenAICompatibleLLM) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Repo(Path(tmp) / "k.db")
        seed(repo)
        case_id = repo.create_case(1)
        t0 = time.perf_counter()
        res = await run_pipeline(
            case_id, AskInput(family_id=1, text=text, files=files), repo=repo, llm=llm, stt=None, bus=EventBus()
        )
        total = time.perf_counter() - t0
        b = repo.case_bundle(case_id) or {}
        repo.close()
    final_round = max((p["round"] for p in b.get("positions", [])), default=1)
    return {
        "colour": res.verdict.colour,
        "case_type": res.case_type,
        "agents": res.called_agents,
        "llm_calls": res.llm_calls,
        "degraded_steps": res.degraded_steps,
        "kept": sum(1 for a in b.get("arguments", []) if a["kept"]),
        "dropped": sum(1 for a in b.get("arguments", []) if not a["kept"]),
        "drop_reasons": [a["drop_reason"] for a in b.get("arguments", []) if not a["kept"]],
        "blocked_lines": [ln["blocked_reason"] for ln in b.get("spoken_lines", []) if not ln["allowed"]],
        "stances": {
            p["agent"]: f"{p['stance']} {p['strength']:.1f}"
            for p in b.get("positions", [])
            if p["round"] == final_round
        },
        "terms": [
            {"name": t["name"], "value": t["value"], "verified": t["verified"], "reason": t["reason"]}
            for t in b.get("terms", [])
        ],
        "photo_confirmed": [
            f["id"] for f in b.get("facts", []) if f["id"].startswith("term.") and f["inputs"].get("photo")
        ],
        "spoken": [f"{ln['speaker']}: {ln['text']}" for ln in b.get("spoken_lines", [])],
        "step_ms": {t["step"]: t["ms"] for t in b.get("trace", [])},
        "step_errors": {t["step"]: t["detail"].get("error") for t in b.get("trace", []) if t["detail"].get("error")},
        "total_s": round(total, 1),
    }


def stats_dict(llm: OpenAICompatibleLLM) -> dict[str, int]:
    return llm.stats.model_dump()


async def warm_up(llm: OpenAICompatibleLLM) -> None:
    from pydantic import BaseModel

    class Ok(BaseModel):
        ok: bool

    try:
        await llm.chat_json("Reply with ok=true.", "{}", Ok)
    except Exception as e:  # warm-up only loads the model
        print(f"warm-up failed: {e}")
    llm.stats = type(llm.stats)()


def fmt_ms(values: list[float]) -> str:
    return f"{statistics.median(values) / 1000:.1f}" if values else "–"


def report(
    title: str,
    groups: dict[str, list[dict[str, Any]]],
    llm_stats: dict[str, dict[str, int]],
    expect: dict[str, set[Any]] | None,
    model: str,
) -> str:
    s = get_settings()
    out = [
        f"# {title}",
        "",
        f"Model `{model}` at `{s.llm_base_url}`, temperature {s.llm_temperature}, "
        f"timeout {s.llm_timeout_s:g} s per call, max {s.llm_max_calls_per_ask} calls per ask. "
        f"Run {time.strftime('%Y-%m-%d %H:%M')}.",
        "",
    ]
    out += [
        "| case | runs | valid JSON (1st try / after retry / failed) | args kept / dropped | verdicts | "
        "LLM calls | degraded runs | total s (median) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, runs in groups.items():
        st = llm_stats[name]
        json_cell = (
            f"{st['valid_first_try']}/{st['steps']} · {st['valid_after_retry']} · {st['invalid_twice']}"
            if st["steps"]
            else "no LLM steps"
        )
        colours = " ".join({"red": "🔴", "yellow": "🟡", "green": "🟢", None: "⚪"}[r["colour"]] for r in runs)
        ok = ""
        if expect is not None:
            hits = sum(r["colour"] in expect[name] for r in runs)
            ok = f" ({hits}/{len(runs)} as expected)"
        out.append(
            f"| {name} | {len(runs)} | {json_cell} | "
            f"{sum(r['kept'] for r in runs)} / {sum(r['dropped'] for r in runs)} "
            f"| {colours}{ok} | {', '.join(str(r['llm_calls']) for r in runs)} | "
            f"{sum(bool(r['degraded_steps']) for r in runs)} | {statistics.median(r['total_s'] for r in runs):.1f} |"
        )
    out += [
        "",
        "Latency per step, median seconds:",
        "",
        "| case | " + " | ".join(STEPS) + " |",
        "|---|" + "---|" * len(STEPS),
    ]
    for name, runs in groups.items():
        cells = [fmt_ms([r["step_ms"][st] for r in runs if st in r["step_ms"]]) for st in STEPS]
        out.append(f"| {name} | " + " | ".join(cells) + " |")
    reasons = Counter(x for runs in groups.values() for r in runs for x in r["drop_reasons"])
    if reasons:
        out += ["", "Dropped-argument reasons:", ""] + [f"- {n}× {r}" for r, n in reasons.most_common(12)]
    blocked = Counter(x for runs in groups.values() for r in runs for x in r["blocked_lines"])
    if blocked:
        out += ["", "Spoken lines replaced (blocked):", ""] + [f"- {n}× {r}" for r, n in blocked.most_common(8)]
    errors = Counter(f"{k}: {v}" for runs in groups.values() for r in runs for k, v in r["step_errors"].items())
    if errors:
        out += ["", "Step errors:", ""] + [f"- {n}× {e[:200]}" for e, n in errors.most_common(8)]
    return "\n".join(out) + "\n"


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--cases", default=",".join(CASES))
    ap.add_argument("--framing", action="store_true")
    ap.add_argument("--vision", action="store_true")
    args = ap.parse_args()

    s = get_settings()
    docs = REPO_ROOT / "docs"
    docs.mkdir(exist_ok=True)
    if args.framing:
        jobs = {f: (FRAMINGS[f], [PDF]) for f in FRAMINGS}
        expect, title, stem = None, "Framing test (endowment brochure)", "reliability_framing"
    elif args.vision:
        s = s.model_copy(update={"llm_vision_enabled": True})
        jobs = {"endowment_photos": (CASES["endowment"]["text"], PHOTOS)}
        expect, title, stem = {"endowment_photos": {"red"}}, "Vision test (brochure photos)", "reliability_vision"
    else:
        names = args.cases.split(",")
        jobs = {n: (CASES[n]["text"], CASES[n]["files"]) for n in names}
        expect, title, stem = {n: CASES[n]["expect"] for n in names}, "Reliability run", "reliability"

    llm = OpenAICompatibleLLM(s)
    model = f"{s.llm_model}" + (f" (+ vision {llm.vision_model})" if args.vision else "")
    print(f"warming up {model} ...")
    await warm_up(llm)
    groups: dict[str, list[dict[str, Any]]] = {}
    llm_stats: dict[str, dict[str, int]] = {}
    for name, (text, files) in jobs.items():
        llm.stats = type(llm.stats)()
        groups[name] = []
        for i in range(args.runs):
            r = await one_run(text, files, llm)
            groups[name].append(r)
            print(
                f"{name} run {i + 1}: {r['colour']} calls={r['llm_calls']} kept={r['kept']} dropped={r['dropped']} "
                f"degraded={r['degraded_steps']} {r['total_s']}s stances={r['stances']}"
            )
        llm_stats[name] = stats_dict(llm)
    md = report(title, groups, llm_stats, expect, model)
    if args.framing:
        md += "\nStances per run (final round):\n\n| framing | run | verdict | stances |\n|---|---|---|---|\n"
        for name, runs in groups.items():
            for i, r in enumerate(runs, 1):
                md += f"| {name} | {i} | {r['colour']} | {r['stances']} |\n"
    if args.vision:
        md += "\nTerms per run:\n\n"
        for i, r in enumerate(groups["endowment_photos"], 1):
            terms = ", ".join(
                f"{t['name']}={t['value']:g}{'' if t['verified'] else ' ✗ ' + str(t['reason'])}"
                if t["value"] is not None
                else f"{t['name']} ✗ {t['reason']}"
                for t in r["terms"]
            )
            md += f"- run {i}: {terms or 'no terms'}; confirmed by OCR: {', '.join(r['photo_confirmed']) or 'none'}\n"
    md += "\nSample spoken lines (first run of each case):\n\n"
    for name, runs in groups.items():
        md += f"**{name}**\n\n" + "\n".join(f"> {x}  " for x in runs[0]["spoken"]) + "\n\n"
    (docs / f"{stem}.md").write_text(md)
    (docs / f"{stem}_raw.json").write_text(
        json.dumps({"groups": groups, "llm_stats": llm_stats}, indent=1, default=str)
    )
    print(md)


if __name__ == "__main__":
    asyncio.run(main())
