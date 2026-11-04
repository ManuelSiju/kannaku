"""Reasoning effort per step on the real Meta API. Run from server/: ../.venv/bin/python -m tests.calibration.effort
Writes docs/reports/effort_matrix.md."""

from __future__ import annotations

import asyncio
import statistics
import sys
import tempfile
import time
from pathlib import Path

from app.config import REPO_ROOT, Settings
from app.db.repo import Repo
from app.db.seed_demo import seed
from app.pipeline.demo_cases import DEMO_CASES, upload_for
from app.pipeline.events import EventBus
from app.pipeline.run import AskInput, run_pipeline
from app.providers.llm import OpenAICompatibleLLM

RUNS = 2
EXPECT = {"endowment": {"red"}, "flat_loan": {"red", "yellow"}, "stock_tip": {"red"}}
CONFIGS = {
    "council minimal, explainer minimal": {},
    "council low": {"meta_effort_council": "low"},
    "council high": {"meta_effort_council": "high"},
    "explainer low": {"meta_effort_explainer": "low"},
    "explainer high": {"meta_effort_explainer": "high"},
}


async def one(name: str, overrides: dict, limit: asyncio.Semaphore) -> dict:
    async with limit:
        with tempfile.TemporaryDirectory() as tmp:
            s = Settings(llm_provider="meta", llm_cache=False, db_path=Path(tmp) / "k.db", **overrides)
            repo = Repo(s.db_path)
            seed(repo)
            question, filename = DEMO_CASES[name]
            files = [upload_for(filename)] if filename else []
            case, t0 = repo.create_case(1), time.perf_counter()
            res = await run_pipeline(
                case,
                AskInput(family_id=1, text=question, files=files),
                repo=repo, llm=OpenAICompatibleLLM(s), stt=None, settings=s, bus=EventBus(),
            )  # fmt: skip
            args = (repo.case_bundle(case) or {}).get("arguments", [])
            repo.close()
    return {
        "match": res.verdict.colour in EXPECT[name],
        "kept": sum(1 for a in args if a["kept"]),
        "dropped": sum(1 for a in args if not a["kept"]),
        "seconds": time.perf_counter() - t0,
        "calls": res.llm_calls,
        "degraded": bool(res.degraded_steps),
    }


async def main() -> int:
    limit = asyncio.Semaphore(3)
    lines = [
        "# Reasoning effort per step\n",
        f"`muse-spark-1.3`, 20 s per call, {RUNS} runs of the 3 cases that use the council.\n",
        "| setting | verdict as expected | kept / dropped | degraded runs | median time | calls |",
        "|---|---|---|---|---|---|",
    ]
    for label, overrides in CONFIGS.items():
        jobs = [one(n, overrides, limit) for n in EXPECT for _ in range(RUNS)]
        runs = await asyncio.gather(*jobs)
        n = len(runs)
        lines.append(
            f"| {label} | {sum(r['match'] for r in runs)}/{n} | {sum(r['kept'] for r in runs)} / "
            f"{sum(r['dropped'] for r in runs)} | {sum(r['degraded'] for r in runs)}/{n} | "
            f"{statistics.median(r['seconds'] for r in runs):.1f} s | {statistics.median(r['calls'] for r in runs):.0f} |"
        )
        print(lines[-1], flush=True)
    (REPO_ROOT / "docs" / "reports" / "effort_matrix.md").write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
