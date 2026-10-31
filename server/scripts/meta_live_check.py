"""One endowment case against the real Meta Model API, only when META_API_KEY is set (environment or .env.local).
Prints the verdict and the number of model calls; otherwise "Meta live check skipped: no key". Run: make meta-check
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    from app.config import Settings

    probe = Settings()
    if not (os.environ.get("META_API_KEY") or probe.meta_api_key.get_secret_value()):
        print("Meta live check skipped: no key")
        return 0
    tmp = tempfile.mkdtemp(prefix="kanakku-meta-check-")
    settings = Settings(llm_provider="meta", db_path=Path(tmp) / "k.db", llm_cache=False)

    from app.db.repo import Repo
    from app.db.seed_demo import seed
    from app.pipeline.events import EventBus
    from app.pipeline.ingest import Upload
    from app.pipeline.run import AskInput, run_pipeline
    from app.providers.llm import get_llm

    repo = Repo(settings.db_path)
    seed(repo)
    pdf = Path(__file__).resolve().parents[1] / "demo_assets" / "kanakavalli_brochure.pdf"
    brochure = Upload(filename=pdf.name, data=pdf.read_bytes(), mime="application/pdf")
    question = "An agent from the company says this plan is guaranteed to give 15 lakh. Should I take it?"
    res = asyncio.run(
        run_pipeline(
            repo.create_case(1),
            AskInput(family_id=1, text=question, files=[brochure]),
            repo=repo, llm=get_llm(settings), stt=None, settings=settings, bus=EventBus(),
        )
    )  # fmt: skip
    print(f"Meta live check: model {settings.llm_model}")
    print(f"  verdict     : {res.verdict.colour}  ({res.short_answer.text if res.short_answer else ''})")
    print(f"  model calls : {res.llm_calls}   degraded: {res.degraded_steps or 'no'}")
    return 0 if res.verdict.colour else 1


if __name__ == "__main__":
    sys.exit(main())
