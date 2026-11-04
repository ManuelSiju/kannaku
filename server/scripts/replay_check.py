"""Asks the 5 demo questions of a running replay server and prints each verdict with its replay label."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import SERVER_ROOT  # noqa: E402
from app.pipeline.demo_cases import DEMO_CASES  # noqa: E402

EXPECT = {"endowment": "red", "stock_tip": "red", "otp_scam": "red", "out_of_scope": None}


def main() -> int:
    if sys.argv[1] == "--reset-note":
        print("Ask these same questions in the app. Anything else is outside the recording and says so.")
        return 0
    bad = 0
    with httpx.Client(base_url=sys.argv[1], timeout=120) as client:
        for name, (question, filename) in DEMO_CASES.items():
            files = None
            if filename:
                files = [
                    ("files", (filename, (SERVER_ROOT / "demo_assets" / filename).read_bytes(), "application/pdf"))
                ]
            data = {"family_id": "1", "text": question}
            res = client.post("/v1/cases", data=data, files=files).json()
            colour = res["verdict"]["colour"]
            ok = not res["degraded"] and (name not in EXPECT or colour == EXPECT[name])
            bad += not ok
            print(f"{'✔' if ok else '✘'} {name}: {colour} · {res['provider']}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
