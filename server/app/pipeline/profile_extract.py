"""Onboarding / "My details": propose profile values and items from what the family said, typed or showed.
Deterministic (no LLM). Nothing is saved here; the app reads each value back and the family confirms it."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

from app.config import get_settings
from app.db.repo import strip_ids
from app.engines.fact import format_inr
from app.numbers.indian_number_parser import AmountMatch, find_amounts, parse_amount

Field = Literal["monthly_income", "monthly_expenses", "savings"]
Source = Literal["typed", "voice", "document"]
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
_NUMBER = r"\d[\d,]*(?:\.\d+)?"
_AMOUNT = rf"{_NUMBER}(?:\s*(?:lakhs?|lacs?|crores?|k)\b)?"
_RUPEES = r"(?:rs\.?|₹)\s*"
MF_HOLDING = re.compile(
    rf"^mutual fund holding (?P<scheme>.+?) value {_RUPEES}(?P<value>{_AMOUNT}) for (?P<units>{_NUMBER}) units", re.I
)
STOCK_HOLDING = re.compile(
    rf"^stock holding (?P<symbol>[A-Z][A-Z0-9&-]+) value {_RUPEES}(?P<value>{_AMOUNT}) for (?P<qty>\d[\d,]*) shares",
    re.I,
)
SIP = re.compile(rf"^sip {_RUPEES}(?P<amount>{_AMOUNT}) a month into (?P<scheme>.+)", re.I)
EQUITY_WORDS = re.compile(r"\b(?:index|equity|flexi|large|mid|small|elss)\b", re.I)
DEBT_WORDS = re.compile(r"\b(?:debt|liquid|gilt|bond|short term|money market)\b", re.I)
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
    kind: Literal["policy", "loan", "deposit", "chit", "other", "mf_holding", "stock_holding", "sip"]
    name: str
    amount: float
    frequency: Literal["monthly", "yearly", "once"]
    source: Literal["typed", "voice", "document"]
    source_ref: str | None = None
    quote: str
    uncertain: bool
    readback: str
    units: float | None = None
    symbol: str | None = None
    scheme: str | None = None
    category: Literal["equity", "debt", "other"] | None = None


class Proposal(BaseModel):
    values: list[ProposedValue] = []
    items: list[ProposedItem] = []
    heard: str
    member_id: int | None = None  # whose it will be saved as
    ask_household: bool = False  # not the primary member: ask "Count this in the family budget?"


def _sentences(text: str) -> list[str]:
    # A line ends a sentence, and so does a full stop, unless it is the one in "Rs. 36,400".
    return [s.strip() for s in re.split(r"(?<=[.!?])(?<![Rr][Ss]\.)\s+|\s*\n\s*|;\s*", text) if s.strip()]


def _amounts(sent: str) -> list[AmountMatch]:
    """The amounts in a sentence, leaving out the numbers of a date."""
    dates = [m.span() for m in DATES.finditer(sent)]
    return [a for a in find_amounts(sent) if not any(s < a.end and a.start < e for s, e in dates)]


def _category(scheme: str) -> Literal["equity", "debt", "other"]:
    return "equity" if EQUITY_WORDS.search(scheme) else "debt" if DEBT_WORDS.search(scheme) else "other"


def _number(text: str) -> float:
    return float(parse_amount(text) or 0)


def _holding(sent: str, source: Source, source_ref: str | None) -> ProposedItem | None:
    """A statement line in the fixed wording of MF_HOLDING, STOCK_HOLDING or SIP."""
    common = {"source": source, "source_ref": source_ref, "quote": sent, "uncertain": False}
    if m := MF_HOLDING.match(sent):
        scheme, value, units = m["scheme"].strip(), _number(m["value"]), _number(m["units"])
        return ProposedItem(
            kind="mf_holding",
            name=scheme,
            amount=value,
            frequency="once",
            units=units,
            scheme=scheme,
            category=_category(scheme),
            readback=f"I read {scheme}: {format_inr(value)} for {units:g} units. Is that right?",
            **common,
        )
    if m := STOCK_HOLDING.match(sent):
        symbol, value, qty = m["symbol"].upper(), _number(m["value"]), _number(m["qty"])
        return ProposedItem(
            kind="stock_holding",
            name=symbol,
            amount=value,
            frequency="once",
            units=qty,
            symbol=symbol,
            readback=f"I read {qty:g} shares of {symbol}, worth {format_inr(value)}. Is that right?",
            **common,
        )
    if m := SIP.match(sent):
        scheme, value = m["scheme"].strip().rstrip("."), _number(m["amount"])
        return ProposedItem(
            kind="sip",
            name=f"SIP into {scheme}",
            amount=value,
            frequency="monthly",
            scheme=scheme,
            category=_category(scheme),
            readback=f"I read a SIP of {format_inr(value)} a month into {scheme}. Is that right?",
            **common,
        )
    return None


def extract_profile(
    text: str,
    source: Literal["typed", "voice", "document"],
    *,
    field: Field | None = None,
    source_ref: str | None = None,
) -> Proposal:
    """`field`: the onboarding question being answered; then the first amount is that field."""
    prop = Proposal(heard="" if source == "document" else text)  # a paper's full text never goes back to the app
    holdings = get_settings().feature_holdings and field is None
    for raw in _sentences(text):
        amounts = _amounts(raw)
        if not amounts:
            continue
        sent = strip_ids(raw) or ""
        if holdings and (item := _holding(sent, source, source_ref)):
            prop.items.append(item)
            continue
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
