"""Routing flags decided in code. market_linked is true only when the documents themselves say returns depend on
the market (ULIP, NAV, fund value, units, market-linked); the case builder's flag counts only with a supporting quote
that is really in the evidence and says so."""

from __future__ import annotations

import re

from app.pipeline.schemas import CaseDraft
from app.pipeline.verify_terms import FUZZY_MIN, EvidenceText, fuzzy_contains

MARKET_WORDS = re.compile(r"\b(?:ULIPs?|NAV|fund\s+values?|units?|market[\s-]*linked)\b", re.I)


def market_linked(draft: CaseDraft, evidence: list[EvidenceText]) -> tuple[bool, str]:
    """(flag, why) — why is recorded in the router trace."""
    for e in evidence:
        if e.source != "transcript" and (m := MARKET_WORDS.search(e.text)):
            return True, f"document {e.source} says '{m.group(0)}'"
    quote = (draft.market_linked_quote or "").strip()
    if "market_linked" in draft.flags or draft.case_type == "ulip":
        if quote and MARKET_WORDS.search(quote) and any(fuzzy_contains(quote, e.text) >= FUZZY_MIN for e in evidence):
            return True, f"case builder quote '{quote}'"
        return False, "case builder said market-linked, but no supporting quote in the documents"
    return False, "no market-linked words in the documents"


def routing_flags(draft: CaseDraft, evidence: list[EvidenceText]) -> tuple[list[str], str, str]:
    """(flags without an unsupported market_linked, case type with an unsupported 'ulip' downgraded, why)."""
    ok, why = market_linked(draft, evidence)
    flags = [f for f in draft.flags if f != "market_linked"] + (["market_linked"] if ok else [])
    case_type = "insurance_offer" if draft.case_type == "ulip" and not ok else draft.case_type
    return flags, case_type, why
