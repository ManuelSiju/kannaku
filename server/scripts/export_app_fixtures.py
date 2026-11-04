"""Writes app/test/fixtures/*.json: real server responses for the Flutter widget and screenshot tests.

Every case runs through the real pipeline (offline: the LLM is the scripted FakeLLM from tests/fixtures/llm), so the
app is tested against the exact JSON the server sends. Run: make app-fixtures
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_tmp = tempfile.mkdtemp(prefix="kanakku-fixtures-")
os.environ.update(
    LLM_PROVIDER="local",
    KANAKKU_TOKEN="",
    DB_PATH=os.path.join(_tmp, "k.db"),
    LOG_PATH=os.path.join(_tmp, "server.log"),
    BACKUP_DIR=os.path.join(_tmp, "backups"),
    ASKS_PER_MINUTE="1000",
)

from fastapi.testclient import TestClient  # noqa: E402

from app.api import deps  # noqa: E402
from app.db.repo import Repo  # noqa: E402
from app.db.seed_demo import seed  # noqa: E402
from app.main import app  # noqa: E402
from app.pipeline.events import EventBus  # noqa: E402
from tests.fakes import TIMEOUT, FakeLLM, FakeSTT, load_fixture  # noqa: E402

OUT = ROOT.parent / "app" / "test" / "fixtures"
BROCHURE = ROOT / "demo_assets" / "kanakavalli_brochure.pdf"
ENDOWMENT_Q = "An agent from the company says this plan is guaranteed to give 15 lakh. Should I take it?"
LOAN_Q = "A finance company is offering me a loan of 1,00,000 at 12% flat for 24 months. Should I take it?"
TIP_Q = (
    "I got this message: ZEPHYRX LTD - BIG NEWS COMING! Target Rs. 180 in 2 weeks. Upper circuit guaranteed. "
    "Should I put 1 lakh in it?"
)
SCAM_Q = "A man from the bank called. My KYC has expired and he asks me to tell him the OTP."


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    repo = Repo(Path(_tmp) / "fixtures.db")
    seed(repo)
    state: dict = {}
    app.dependency_overrides[deps.get_repo] = lambda: repo
    app.dependency_overrides[deps.get_llm_provider] = lambda: state["llm"]
    app.dependency_overrides[deps.get_stt_provider] = lambda: FakeSTT("")
    app.dependency_overrides[deps.get_bus] = lambda: EventBus()
    degraded = load_fixture("endowment") | {"CouncilOutput": TIMEOUT}
    cases = {
        "endowment_red": ("endowment", ENDOWMENT_Q, True, {}),
        "endowment_full": ("endowment", ENDOWMENT_Q, True, {"earphones": "true"}),
        "loan_red": ("flat_loan", LOAN_Q, False, {}),
        "stock_red": ("stock_tip", TIP_Q, False, {}),
        "scam": (None, SCAM_Q, False, {}),
        "out_of_scope": ("out_of_scope", "Can you tell me a good recipe for sambar?", False, {}),
        "degraded": (degraded, ENDOWMENT_Q, True, {}),
    }
    with TestClient(app) as client:
        for name, (script, text, brochure, extra) in cases.items():
            state["llm"] = FakeLLM(script if isinstance(script, dict) else load_fixture(script) if script else {})
            files = [("files", (BROCHURE.name, BROCHURE.read_bytes(), "application/pdf"))] if brochure else None
            r = client.post("/v1/cases", data={"family_id": "1", "text": text, **extra}, files=files)
            r.raise_for_status()
            result = r.json()
            bundle = client.get(f"/v1/cases/{result['case_id']}").json()
            (OUT / f"{name}.json").write_text(json.dumps({"result": result, "bundle": bundle}, indent=1))
            print(f"{name:15} {str(result['verdict']['colour']):7} privacy={result['privacy_mode']}")
        alerts = client.get("/v1/families/1/alerts").json()
        client.patch(f"/v1/alerts/{alerts[0]['id']}", json={"note": "Please wait for me before you sign. I will call."})
        extras = {
            "health": client.get("/v1/health").json(),
            "profile": client.get("/v1/families/1/profile").json(),
            "items": client.get("/v1/families/1/items").json(),
            "alerts": client.get("/v1/families/1/alerts").json(),
            "notes": client.get("/v1/families/1/notes").json(),
            "documents": client.get("/v1/families/1/documents").json(),
            "proposal": client.post(
                "/v1/families/1/profile/extract", data={"text": "My pension is 45,000 a month."}
            ).json(),
        }
        for name, body in extras.items():
            (OUT / f"{name}.json").write_text(json.dumps(body, indent=1))
            print(f"{name:15} written")
    app.dependency_overrides.clear()


if __name__ == "__main__":
    main()
