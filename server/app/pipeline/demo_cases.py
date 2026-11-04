"""The 5 demo questions, shared by the replay recorder, make demo-replay and its test."""

from __future__ import annotations

from app.config import SERVER_ROOT
from app.pipeline.ingest import Upload

DEMO_CASES: dict[str, tuple[str, str | None]] = {
    "endowment": (
        "An agent from the company says this plan is guaranteed to give 15 lakh. Should I take it?",
        "kanakavalli_brochure.pdf",
    ),
    "flat_loan": (
        "A finance company is offering me a loan of 1,00,000 at 12% flat for 24 months. Should I take it?",
        None,
    ),
    "stock_tip": (
        "I got this message: ZEPHYRX LTD - BIG NEWS COMING! Target Rs. 180 in 2 weeks. Upper circuit guaranteed. "
        "Should I put 1 lakh in it?",
        None,
    ),
    "otp_scam": ("A man from the bank called. My KYC has expired and he asks me to tell him the OTP.", None),
    "out_of_scope": ("How do I make sambar?", None),
}


def upload_for(filename: str) -> Upload:
    data = (SERVER_ROOT / "demo_assets" / filename).read_bytes()
    return Upload(filename=filename, data=data, mime="application/pdf")
