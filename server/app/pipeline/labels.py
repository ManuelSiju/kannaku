"""Human-readable source labels for the app ("Brochure page 1 · read twice")."""

from __future__ import annotations

from datetime import date

from app.engines.fact import Fact

DOC_NOUN = {
    "insurance_offer": "Brochure", "ulip": "Brochure", "loan_offer": "Loan offer", "stock_tip": "Message",
    "shares": "Message", "ipo": "Document", "sip_or_fund_question": "Document",
}  # fmt: skip
_SOURCE_WORDS = {"voice": "You told us by voice", "typed": "You typed it", "document": "From your document"}


def _pretty_date(iso: str | None) -> str:
    try:
        d = date.fromisoformat(iso or "")
    except ValueError:
        return iso or "unknown date"
    return f"{d.day} {d.strftime('%b %Y')}"


def where(source: str, case_type: str) -> str:
    """'page_2' -> 'Brochure page 2'; 'transcript' -> 'What you said'."""
    if source == "transcript":
        return "What you said"
    if source.startswith("page_"):
        return f"{DOC_NOUN.get(case_type, 'Document')} page {source.removeprefix('page_')}"
    return source


def source_label(fact: Fact, case_type: str) -> str:
    inp = fact.inputs
    if fact.id.startswith("term."):
        reading = inp.get("reading") or ("twice" if inp.get("photo") else "checked")
        how = {"twice": "read twice", "once": "read once"}.get(reading, "checked")
        return f"{where(str(inp.get('source', '')), case_type)} · {how}"
    if fact.id.startswith("ref."):
        return f"Assumption · as of {_pretty_date(inp.get('as_of'))}"
    if fact.id.startswith(("profile.", "item.")):
        if fact.status != "known":
            return "Not told yet"
        label = _SOURCE_WORDS.get(str(inp.get("source")), "You told us")
        ref = inp.get("source_ref")
        if inp.get("source") == "document" and ref:
            return f"From your {ref}"
        return label
    if fact.id in ("existing_emi", "regular_commitments"):
        return "Added up from your saved loans and policies"
    if fact.id.startswith("scam."):
        return "Warning sign found"
    return "Worked out by Kanakku"


def unverified_label(source: str, reason: str | None, case_type: str) -> str:
    return f"{where(source, case_type)} · could not check ({reason or 'unverified'})"
