"""Onboarding / "My details": propose profile values and items from what the family said, typed or showed.
Deterministic (no LLM). Nothing is saved here; the app reads each value back and the family confirms it."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

from app.db.repo import strip_ids
from app.engines.fact import format_inr
from app.numbers.indian_number_parser import AmountMatch, find_amounts

Field = Literal["monthly_income", "monthly_expenses", "savings"]
KEYWORDS: dict[str, tuple[str, ...]] = {
    "monthly_income": ("income", "salary", "earn", "pension", "get paid", "wage"),
    "monthly_expenses": ("expense", "spend", "household", "costs", "kharcha"),
    "savings": ("saving", "saved", "bank balance", "in the bank", "fixed deposit", "fd "),
}
PREMIUM = re.compile(r"\bpremiums?\b", re.I)  # always a policy, even in "loan against policy premium"
LOAN_WORDS = re.compile(r"\b(?:emis?|loans?)\b", re.I)
POLICY_WORDS = re.compile(r"\b(?:polic(?:y|ies)|insurance|lic)\b", re.I)
_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
DATES = re.compile(
    rf"\b\d{{1,2}}[/.-]\d{{1,2}}[/.-]\d{{2,4}}\b|\b\d{{4}}-\d{{2}}-\d{{2}}\b"
    rf"|\b\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTH}(?:\s+\d{{4}})?\b|\b{_MONTH}\s+\d{{1,2}},?\s+\d{{4}}\b"
    rf"|\b{_MONTH}\s+\d{{4}}\b|\b(?:in|since|from|year)\s+(?:19|20)\d{{2}}\b",
    re.I,
)
YEARLY = re.compile(r"\b(?:a|per|every|each)\s+year\b|\byearly\b|\bannual", re.I)
PLAIN = {
    "monthly_income": "income each month",
    "monthly_expenses": "household spending each month",
    "savings": "savings",
}


class ProposedValue(BaseModel):
    field: Field
    value: float
    unit: str = "INR"
    source: Literal["typed", "voice", "document"]
    source_ref: str | None = None
    quote: str
    uncertain: bool
    readback: str


class ProposedItem(BaseModel):
    kind: Literal["policy", "loan", "deposit", "chit", "other"]
    name: str
    amount: float
    frequency: Literal["monthly", "yearly", "once"]
    source: Literal["typed", "voice", "document"]
    source_ref: str | None = None
    quote: str
    uncertain: bool
    readback: str


class Proposal(BaseModel):
    values: list[ProposedValue] = []
    items: list[ProposedItem] = []
    heard: str


def _sentences(text: str) -> list[str]:
    # A line ends a sentence, and so does a full stop, unless it is the one in "Rs. 36,400".
    return [s.strip() for s in re.split(r"(?<=[.!?])(?<![Rr][Ss]\.)\s+|\s*\n\s*|;\s*", text) if s.strip()]


def _amounts(sent: str) -> list[AmountMatch]:
    """The amounts in a sentence, leaving out the numbers of a date."""
    dates = [m.span() for m in DATES.finditer(sent)]
    return [a for a in find_amounts(sent) if not any(s < a.end and a.start < e for s, e in dates)]


def extract_profile(
    text: str,
    source: Literal["typed", "voice", "document"],
    *,
    field: Field | None = None,
    source_ref: str | None = None,
) -> Proposal:
    """`field`: the onboarding question being answered; then the first amount is that field."""
    prop = Proposal(heard="" if source == "document" else text)  # a paper's full text never goes back to the app
    for raw in _sentences(text):
        amounts = _amounts(raw)
        if not amounts:
            continue
        sent = strip_ids(raw) or ""
        low = sent.lower()
        uncertain = len(amounts) > 1
        value = float(next((a for a in amounts if a.currency), amounts[0]).value)
        premium = bool(PREMIUM.search(sent))
        if field is not None:
            target: str | None = field
        elif LOAN_WORDS.search(sent) and not premium:
            prop.items.append(
                ProposedItem(
                    kind="loan",
                    name="Loan EMI",
                    amount=value,
                    frequency="monthly",
                    source=source,
                    source_ref=source_ref,
                    quote=sent,
                    uncertain=uncertain,
                    readback=f"I heard a loan EMI of {format_inr(value)} a month. Is that right?",
                )
            )
            continue
        elif premium or POLICY_WORDS.search(sent):
            freq = "yearly" if YEARLY.search(sent) else "monthly"
            per = "a year" if freq == "yearly" else "a month"
            prop.items.append(
                ProposedItem(
                    kind="policy",
                    name="Insurance policy",
                    amount=value,
                    frequency=freq,
                    source=source,
                    source_ref=source_ref,
                    quote=sent,
                    uncertain=uncertain,
                    readback=f"I heard a policy premium of {format_inr(value)} {per}. Is that right?",
                )
            )
            continue
        else:
            target = next((f for f, words in KEYWORDS.items() if any(w in low for w in words)), None)
        if target is None:
            continue
        per = "" if target == "savings" else " a month"
        prop.values.append(
            ProposedValue(
                field=target,
                value=value,
                source=source,
                source_ref=source_ref,
                quote=sent,
                uncertain=uncertain or (field is None and target is None),
                readback=f"I heard {format_inr(value)}{per} for your {PLAIN[target]}. Is that right?",
            )
        )  # type: ignore[arg-type]
        if field is not None:
            break
    return prop
