"""Evidence checker. Model text may contain numbers ONLY as {fact_id} placeholders; code substitutes Fact.display.

check_argument(...) -> Kept(rendered, cited) | Dropped(reason). An argument is dropped when:
- it contains a raw digit outside placeholders (the model wrote a number itself),
- a placeholder or cited id is unknown (or, with kind_filter, a placeholder fact has the wrong kind),
- it cites nothing at all (placeholders count as citations; quote ids back non-numeric claims).

numbers_in / value_matches are kept for the privacy check, which runs on the rendered text.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any, Literal

from pydantic import BaseModel

from app.engines.fact import Fact, FactKind
from app.numbers.indian_number_parser import find_amounts, find_percents

REL_TOL = 0.01

Facts = Mapping[str, Fact] | Iterable[Fact]
Quotes = Mapping[str, str] | Iterable[Any]  # {quote_id: text} or objects with .id and .text


PLACEHOLDER = re.compile(r"\{([A-Za-z][A-Za-z0-9_.]*)\}")
_DIGIT = re.compile(r"\d")


class Kept(BaseModel):
    kept: Literal[True] = True
    rendered: str  # placeholders replaced by Fact.display
    cited: list[str] = []  # cited ids plus placeholder ids


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
    # Rounding to lakh / crore only applies to amounts that size (0.45 lakh must not "match" 0.5 lakh).
    rounded = [round(value / 1e5, 1) * 1e5] if abs(value) >= 1e5 else []
    rounded += [round(value / 1e7, 2) * 1e7] if abs(value) >= 1e7 else []
    return n.value in rounded


def placeholders(text: str) -> list[str]:
    return list(dict.fromkeys(PLACEHOLDER.findall(text)))


def resolve_placeholders(text: str, fact_ids: Iterable[str]) -> str:
    """Small models often drop an id's prefix ({sum_assured} for {term.sum_assured}). Rewrite a placeholder to the
    full id only when exactly one fact id ends with ".<name>"; anything else is left for the check to reject."""
    ids = set(fact_ids)

    def fix(m: re.Match[str]) -> str:
        name = m.group(1)
        if name in ids:
            return m.group(0)
        matches = [i for i in ids if i.endswith("." + name)]
        return "{" + matches[0] + "}" if len(matches) == 1 else m.group(0)

    return PLACEHOLDER.sub(fix, text)


def render(text: str, facts: Facts) -> str:
    fact_map = as_fact_map(facts)
    return PLACEHOLDER.sub(lambda m: fact_map[m.group(1)].display if m.group(1) in fact_map else m.group(0), text)


def raw_number(text: str) -> str | None:
    """The first stretch of text with a digit outside placeholders, or None."""
    m = _DIGIT.search(PLACEHOLDER.sub("", text))
    if m is None:
        return None
    stripped = PLACEHOLDER.sub("", text)
    return stripped[max(0, m.start() - 8) : m.end() + 8].strip()


def check_argument(
    argument_text: str,
    cited_ids: Iterable[str],
    facts: Facts,
    quotes: Quotes | None,
    kind_filter: FactKind | None = None,
) -> Kept | Dropped:
    """kind_filter: if set, every placeholder must be a fact of that kind."""
    fact_map, quote_map = as_fact_map(facts), as_quote_map(quotes)
    argument_text = resolve_placeholders(argument_text, fact_map)
    ph = placeholders(argument_text)
    unknown_ph = [p for p in ph if p not in fact_map]
    if unknown_ph:
        return Dropped(reason=f"unknown placeholder(s): {', '.join(unknown_ph)}")
    if kind_filter is not None:
        wrong = [p for p in ph if fact_map[p].kind != kind_filter]
        if wrong:
            return Dropped(reason=f"placeholder {wrong[0]} is not a {kind_filter} fact")
    if (raw := raw_number(argument_text)) is not None:
        return Dropped(reason=f"raw number in text ('{raw}'); numbers must be {{fact_id}} placeholders")
    cited = list(dict.fromkeys([*cited_ids, *ph]))
    unknown_ids = [c for c in cited if c not in fact_map and c not in quote_map]
    if unknown_ids:
        return Dropped(reason=f"unknown citation id(s): {', '.join(unknown_ids)}")
    if not cited:
        return Dropped(reason="no evidence cited")
    return Kept(rendered=render(argument_text, fact_map), cited=cited)
