"""Draft a polite cancellation or complaint letter from a saved case (template; no LLM, no personal ids)."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

LetterKind = Literal["cancel", "complaint"]


def draft_letter(bundle: dict[str, Any], kind: LetterKind, sender_name: str = "") -> str:
    case = bundle["case"]
    verdict = bundle.get("verdict") or {}
    what = (case.get("case_type") or "offer").replace("_", " ")
    offer = [f for f in bundle.get("facts", []) if f["kind"] == "offer" and f["value"] is not None]
    # What Kanakku worked out first, then what the document said; reference-rate assumptions are left out.
    computed = [f for f in offer if not f["id"].startswith(("term.", "ref."))]
    stated = [f for f in offer if f["id"].startswith("term.")]
    reasons = [f"- {f['label']}: {_fmt(f)}" for f in (computed + stated)[:4]]
    body = "\n".join(reasons) or "- The terms were not explained clearly to me."
    if kind == "cancel":
        ask = (
            f"I do not wish to go ahead with this {what}. If anything has already been started in my name, "
            "please cancel it within the free-look period and refund any amount paid."
        )
        subject = f"Request to cancel: {what}"
    else:
        ask = (
            f"I am writing to complain about how this {what} was offered to me. Important terms were not "
            "explained, and I was pressured to decide quickly."
        )
        subject = f"Complaint about: {what}"
    return (
        f"Date: {date.today().isoformat()}\n\nTo the Grievance Officer,\n\nSubject: {subject}\n\n{ask}\n\n"
        f"What I found when I checked:\n{body}\n\n"
        + (f"{verdict.get('sentence')}\n\n" if verdict.get("sentence") else "")
        + "Please reply in writing.\n\nYours sincerely,\n"
        + (sender_name or "________________")
        + "\n"
    )


def _fmt(f: dict[str, Any]) -> str:
    from app.engines.fact import Fact

    return Fact.model_validate(f).display
