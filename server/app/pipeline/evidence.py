"""Evidence checker. Model text may contain numbers ONLY as {fact_id} placeholders; code substitutes Fact.display.

check_argument(...) -> Kept(rendered, cited) | Dropped(reason). An argument is dropped when:
- it contains a raw digit outside placeholders (the model wrote a number itself),
- a placeholder or cited id is unknown (or, with kind_filter, a placeholder fact has the wrong kind),
- it cites nothing at all (placeholders count as citations; quote ids back non-numeric claims).
- it uses a comparison word (better, worse, higher, lower, more, less, beats, below, above) without citing a cmp_*
  fact whose direction agrees (checked on the rendered text; "... than this plan" flips the direction).

Before checking, two mechanical repairs are made and reported in `fixes` (trace key "auto_placeholder"):
- short id: {sum_assured} -> {term.sum_assured} when exactly one fact id ends with ".sum_assured";
- auto placeholder: a raw number that exactly equals the display of exactly one fact becomes that placeholder.

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


COMPARISON = re.compile(r"\b(better|worse|higher|lower|more|less|beats?|below|above)\b", re.I)
_POSITIVE = {"better", "higher", "more", "beat", "beats", "above"}
_FLIP = re.compile(r"\s*than\s+(?:this|the|your|that)\s+(?:plan|policy|offer|loan|scheme|investment|tip)\b", re.I)


class Kept(BaseModel):
    kept: Literal[True] = True
    rendered: str  # placeholders replaced by Fact.display
    cited: list[str] = []  # cited ids plus placeholder ids
    fixes: list[str] = []  # auto_placeholder / short-id repairs made before checking


class Dropped(BaseModel):
    kept: Literal[False] = False
    reason: str
    fixes: list[str] = []


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


def resolve_placeholders(text: str, fact_ids: Iterable[str]) -> tuple[str, list[str]]:
    """Small models often drop an id's prefix ({sum_assured} for {term.sum_assured}). Rewrite a placeholder to the
    full id only when exactly one fact id ends with ".<name>"; anything else is left for the check to reject."""
    ids = set(fact_ids)
    fixes: list[str] = []

    def fix(m: re.Match[str]) -> str:
        name = m.group(1)
        if name in ids:
            return m.group(0)
        matches = [i for i in ids if i.endswith("." + name)]
        if len(matches) != 1:
            return m.group(0)
        fixes.append(f"short id {{{name}}} -> {{{matches[0]}}}")
        return "{" + matches[0] + "}"

    return PLACEHOLDER.sub(fix, text), fixes


def auto_placeholders(text: str, facts: Facts) -> tuple[str, list[str]]:
    """Replace a raw number that exactly equals the display of exactly ONE known fact by that fact's placeholder.
    Text inside existing placeholders is never touched. Ambiguous or non-matching numbers stay (and get dropped)."""
    by_display: dict[str, list[str]] = {}
    for f in as_fact_map(facts).values():
        if f.status == "known" and _DIGIT.search(f.display):
            by_display.setdefault(f.display, []).append(f.id)
    fixes: list[str] = []
    parts = re.split(r"(\{[A-Za-z][A-Za-z0-9_.]*\})", text)
    for display in sorted(by_display, key=len, reverse=True):
        ids = by_display[display]
        pat = re.compile(r"(?<![\d.,])" + re.escape(display) + r"(?![\d.,])")
        for k, part in enumerate(parts):
            if k % 2 or not pat.search(part):
                continue  # odd parts are existing placeholders
            if len(ids) != 1:
                continue
            parts[k] = pat.sub("{" + ids[0] + "}", part)
            fixes.append(f"auto_placeholder '{display}' -> {{{ids[0]}}}")
        parts = re.split(r"(\{[A-Za-z][A-Za-z0-9_.]*\})", "".join(parts))
    return "".join(parts), fixes


def comparison_problem(rendered: str, cited: Iterable[str], fact_map: Mapping[str, Fact]) -> str | None:
    """Every comparison word needs a cited cmp_* fact saying the same direction."""
    directions = {fact_map[c].value_text for c in cited if c in fact_map and c.rsplit(".", 1)[-1].startswith("cmp_")}
    for m in COMPARISON.finditer(rendered):
        word = m.group(1).lower()
        direction = "higher" if word in _POSITIVE else "lower"
        if _FLIP.match(rendered, m.end()):
            direction = "lower" if direction == "higher" else "higher"
        if direction not in directions:
            return f"comparison '{m.group(1)}' needs a cited cmp_* fact saying '{direction}'"
    return None


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
    *,
    comparisons: bool = True,
) -> Kept | Dropped:
    """kind_filter: if set, every placeholder must be a fact of that kind. comparisons: run the comparison-word
    check (off for questions to the seller)."""
    fact_map, quote_map = as_fact_map(facts), as_quote_map(quotes)
    argument_text, fixes = resolve_placeholders(argument_text, fact_map)
    argument_text, autos = auto_placeholders(argument_text, fact_map)
    fixes += autos
    ph = placeholders(argument_text)
    unknown_ph = [p for p in ph if p not in fact_map]
    if unknown_ph:
        return Dropped(reason=f"unknown placeholder(s): {', '.join(unknown_ph)}", fixes=fixes)
    if kind_filter is not None:
        wrong = [p for p in ph if fact_map[p].kind != kind_filter]
        if wrong:
            return Dropped(reason=f"placeholder {wrong[0]} is not a {kind_filter} fact", fixes=fixes)
    if (raw := raw_number(argument_text)) is not None:
        return Dropped(reason=f"raw number in text ('{raw}'); numbers must be {{fact_id}} placeholders", fixes=fixes)
    cited = list(dict.fromkeys([*cited_ids, *ph]))
    unknown_ids = [c for c in cited if c not in fact_map and c not in quote_map]
    if unknown_ids:
        return Dropped(reason=f"unknown citation id(s): {', '.join(unknown_ids)}", fixes=fixes)
    if not cited:
        return Dropped(reason="no evidence cited", fixes=fixes)
    rendered = render(argument_text, fact_map)
    if comparisons and (problem := comparison_problem(rendered, cited, fact_map)):
        return Dropped(reason=problem, fixes=fixes)
    return Kept(rendered=rendered, cited=cited, fixes=fixes)
