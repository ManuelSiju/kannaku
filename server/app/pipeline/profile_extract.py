"""Onboarding / "My details": propose profile values and items from what the family said, typed or showed.
Deterministic (no LLM). Nothing is saved here; the app reads each value back and the family confirms it."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

from app.engines.fact import format_inr
from app.numbers.indian_number_parser import find_amounts

Field = Literal["monthly_income", "monthly_expenses", "savings"]
KEYWORDS: dict[str, tuple[str, ...]] = {
    "monthly_income": ("income", "salary", "earn", "pension", "get paid", "wage"),
    "monthly_expenses": ("expense", "spend", "household", "costs", "kharcha"),
    "savings": ("saving", "saved", "bank balance", "in the bank", "fixed deposit", "fd "),
}
LOAN_WORDS = ("emi", "loan")
POLICY_WORDS = ("policy", "premium", "insurance", "lic")
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
    return [s.strip() for s in re.split(r"(?<=[.!?\n])\s+|;\s*", text) if s.strip()]


def extract_profile(
    text: str,
    source: Literal["typed", "voice", "document"],
    *,
    field: Field | None = None,
    source_ref: str | None = None,
) -> Proposal:
    """`field`: the onboarding question being answered; then the first amount is that field."""
    prop = Proposal(heard=text)
    for sent in _sentences(text):
        amounts = find_amounts(sent)
        if not amounts:
            continue
        low = sent.lower()
        uncertain = len(amounts) > 1
        value = float(amounts[0].value)
        if field is not None:
            target: str | None = field
        elif any(w in low for w in LOAN_WORDS):
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
        elif any(w in low for w in POLICY_WORDS):
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
