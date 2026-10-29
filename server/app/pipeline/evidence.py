"""Evidence checker: every number in an agent's argument must come from a cited fact or a cited quote.

check_argument(...) -> Kept | Dropped(reason). Matching rules for a number in the text:
- against a cited fact: within 1% of the fact value, or equal after rounding to the displayed unit
  (percent to an integer or 1 decimal; lakh to 1 decimal; crore to 2 decimals). Percent numbers are
  compared with fraction facts x 100. A number may also match one of the cited fact's inputs (e.g. "15 years").
- against a cited quote: the same number appears in the quote.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel

from app.engines.fact import Fact, FactKind
from app.numbers.indian_number_parser import find_amounts, find_percents

REL_TOL = 0.01

Facts = Mapping[str, Fact] | Iterable[Fact]
Quotes = Mapping[str, str] | Iterable[Any]  # {quote_id: text} or objects with .id and .text


class Kept(BaseModel):
    kept: Literal[True] = True
    numbers: list[str] = []  # numbers found and matched


class Dropped(BaseModel):
    kept: Literal[False] = False
    reason: str


class TextNumber(BaseModel):
    value: float
    is_percent: bool
    text: str


def as_fact_map(facts: Facts) -> dict[str, Fact]:
    return dict(facts) if isinstance(facts, Mapping) else {f.id: f for f in facts}


def as_quote_map(quotes: Quotes | None) -> dict[str, str]:
    if quotes is None:
        return {}
    if isinstance(quotes, Mapping):
        return {str(k): v for k, v in quotes.items()}
    return {str(q.id): q.text for q in quotes}


def numbers_in(text: str) -> list[TextNumber]:
    pcts = find_percents(text)
    out = [TextNumber(value=float(p.value), is_percent=True, text=p.text) for p in pcts]
    out += [TextNumber(value=float(a.value), is_percent=False, text=a.text) for a in find_amounts(text)]
    return out


def _close(a: float, b: float) -> bool:
    return a == b if b == 0 else abs(a - b) <= REL_TOL * abs(b)


def value_matches(n: TextNumber, value: float | None, unit: str) -> bool:
    if value is None:
        return False
    if n.is_percent:
        if unit != "fraction":
            return False
        pct = value * 100
        return _close(n.value, pct) or n.value in (round(pct), round(pct, 1))
    if unit == "fraction":
        return False
    if _close(n.value, value):
        return True
    # rounded to the displayed unit: "13.4 lakh", "1.25 crore"
    return n.value in (round(value / 1e5, 1) * 1e5, round(value / 1e7, 2) * 1e7)


def fact_supports(n: TextNumber, fact: Fact) -> bool:
    if value_matches(n, fact.value, fact.unit):
        return True
    for v in fact.inputs.values():
        if isinstance(v, bool) or not isinstance(v, int | float | Decimal):
            continue
        if n.is_percent and _close(n.value, float(v) * 100):  # e.g. rate input 0.07 -> "7%"
            return True
        if not n.is_percent and _close(n.value, float(v)):
            return True
    return False


def quote_supports(n: TextNumber, quote: str) -> bool:
    return any(_close(n.value, q.value) and n.is_percent == q.is_percent for q in numbers_in(quote))


def check_argument(
    argument_text: str,
    cited_ids: Iterable[str],
    facts: Facts,
    quotes: Quotes | None,
    kind_filter: FactKind | None = None,
) -> Kept | Dropped:
    """kind_filter: if set, only cited facts of that kind count as support."""
    fact_map, quote_map = as_fact_map(facts), as_quote_map(quotes)
    cited = list(dict.fromkeys(cited_ids))
    unknown_ids = [c for c in cited if c not in fact_map and c not in quote_map]
    if unknown_ids:
        return Dropped(reason=f"unknown citation id(s): {', '.join(unknown_ids)}")
    if not cited:
        return Dropped(reason="no evidence cited")
    cited_facts = [fact_map[c] for c in cited if c in fact_map]
    if kind_filter is not None:
        cited_facts = [f for f in cited_facts if f.kind == kind_filter]
    cited_quotes = [quote_map[c] for c in cited if c in quote_map]

    matched: list[str] = []
    for n in numbers_in(argument_text):
        if any(fact_supports(n, f) for f in cited_facts) or any(quote_supports(n, q) for q in cited_quotes):
            matched.append(n.text)
            continue
        uncited = [f.id for f in fact_map.values() if f.id not in cited and fact_supports(n, f)]
        hint = f" (matches uncited fact {uncited[0]})" if uncited else ""
        return Dropped(reason=f"number '{n.text}' not supported by cited evidence{hint}")
    return Kept(numbers=matched)
