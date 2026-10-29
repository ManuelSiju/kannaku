"""Parse Indian-style money amounts and percentages from free text.

Handles ₹ / Rs. / INR prefixes, Indian and international digit grouping, and the units
k / thousand / lakh / crore in English, plus Malayalam (ആയിരം, ലക്ഷം, കോടി) and Hindi (हज़ार, लाख, करोड़).
Percentages are parsed separately (parse_percent / find_percents) and are never returned as amounts.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel

_MULTIPLIERS: list[tuple[str, int]] = [
    # (regex, multiplier) — longest words first
    (r"crores?|cr\b\.?|കോടി\w*|करोड़?", 10_000_000),
    (r"lakhs?|lacs?|lkh|ലക്ഷ\w*|लाख", 100_000),
    (r"thousands?|k(?![a-z])|ആയിര\w*|हज़ार|हजार", 1_000),
]
_UNIT_RE = "|".join(f"(?P<u{i}>{pat})" for i, (pat, _) in enumerate(_MULTIPLIERS))

_NUMBER = r"\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+"
_CURRENCY = r"₹|rs\.?|inr|rupees?"

_AMOUNT_RE = re.compile(
    rf"(?P<cur>(?:{_CURRENCY})\s*)?(?<![\d.,])(?P<num>{_NUMBER})(?![\d])"
    rf"(?:\s*(?:{_UNIT_RE}))?(?P<pct>\s*(?:%|per\s*cent|percent))?",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(rf"(?<![\d.,])(?P<num>{_NUMBER})\s*(?:%|per\s*cent|percent)", re.IGNORECASE)


class AmountMatch(BaseModel):
    value: Decimal
    text: str
    start: int
    end: int


def _to_decimal(num: str) -> Decimal | None:
    try:
        return Decimal(num.replace(",", ""))
    except InvalidOperation:
        return None


def _clean(d: Decimal) -> Decimal:
    return d.quantize(Decimal(1)) if d == d.to_integral_value() else d.normalize()


def find_amounts(text: str) -> list[AmountMatch]:
    """Every money-like number in the text (percentages excluded), with its rupee value."""
    out: list[AmountMatch] = []
    for m in _AMOUNT_RE.finditer(text):
        if m.group("pct"):
            continue
        value = _to_decimal(m.group("num"))
        if value is None:
            continue
        for i, (_, mult) in enumerate(_MULTIPLIERS):
            if m.group(f"u{i}"):
                value *= mult
                break
        out.append(AmountMatch(value=_clean(value), text=m.group(0).strip(), start=m.start(), end=m.end()))
    return out


def parse_amount(text: str) -> Decimal | None:
    """The first amount in the text, in rupees, or None."""
    found = find_amounts(text)
    return found[0].value if found else None


def find_percents(text: str) -> list[AmountMatch]:
    out = []
    for m in _PERCENT_RE.finditer(text):
        value = _to_decimal(m.group("num"))
        if value is not None:
            out.append(AmountMatch(value=_clean(value), text=m.group(0).strip(), start=m.start(), end=m.end()))
    return out


def parse_percent(text: str) -> Decimal | None:
    """The first percentage in the text as a percent number ("12%" -> 12), or None."""
    found = find_percents(text)
    return found[0].value if found else None
