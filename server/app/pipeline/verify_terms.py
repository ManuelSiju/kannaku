"""Step 3 (code): a term is used in maths only if its number parses, its quote is really in the evidence
(fuzzy >= 90% on whitespace-normalised text), the number is in that quote, and for photos the number also
appears in the OCR text (two independent readings). Everything else becomes an "ask him this" question."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from pydantic import BaseModel

from app.engines.fact import Fact, format_inr
from app.numbers.indian_number_parser import find_amounts, find_percents, parse_amount, parse_percent
from app.pipeline.schemas import TERM_NAMES, ExtractedTerm

FUZZY_MIN = 0.90


class EvidenceText(BaseModel):
    quote_id: str
    source: str
    text: str
    ocr_text: str | None = None  # set for photo pages


class VerifiedTerm(BaseModel):
    name: str
    value_text: str
    value: float | None
    unit: str
    quote_id: str | None
    source: str
    verified: bool
    reason: str | None = None
    photo: bool = False  # confirmed by a second, independent reading (OCR of the photo)
    reading: str = "checked"  # "twice" (vision model + OCR agree) | "once" (photo, OCR only) | "checked" (text/speech)

    @property
    def display(self) -> str:
        if self.value is None:
            return self.value_text
        if self.unit == "fraction":
            return f"{self.value * 100:g}%"
        if self.unit == "INR":
            return format_inr(self.value)
        return f"{self.value:g} {self.unit}"


def term_unit(name: str) -> str:
    if "rate" in name:  # flat_rate, reducing_rate, bonus_rate_low, bonus_rate_high
        return "fraction"
    if name.endswith("months"):
        return "months"
    if name.endswith("years"):
        return "years"
    return "INR"


def _sentence_around(quote: str, text: str) -> str:
    """The quote with the sentence it came from: "9.5% a year" alone does not say flat or reducing."""
    parts = re.split(r"(?<=[.!?])\s+|\n", text)
    near = [p for p in parts if fuzzy_contains(quote, p) >= FUZZY_MIN]
    return " ".join([quote, *near])


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def fuzzy_contains(quote: str, text: str) -> float:
    q, t = _norm(quote), _norm(text)
    if not q:
        return 0.0
    if q in t:
        return 1.0
    blocks = SequenceMatcher(None, q, t, autojunk=False).get_matching_blocks()
    return sum(b.size for b in blocks) / len(q)


def _number_in(value: float, unit: str, text: str) -> bool:
    if unit == "fraction":
        return any(abs(float(p.value) / 100 - value) < 1e-9 for p in find_percents(text))
    return any(abs(float(a.value) - value) <= max(0.005, 1e-6 * abs(value)) for a in find_amounts(text))


def verify_term(term: ExtractedTerm, evidence: list[EvidenceText], *, vision_read: bool = False) -> VerifiedTerm:
    """vision_read: the model looked at the photo itself, so OCR agreeing is a second, independent reading."""
    unit = term_unit(term.name)
    raw = parse_percent(term.value_text) if unit == "fraction" else parse_amount(term.value_text)
    value = None if raw is None else float(raw) / 100 if unit == "fraction" else float(raw)
    base = dict(name=term.name, value_text=term.value_text, value=value, unit=unit, source=term.source)

    def fail(reason: str, quote_id: str | None = None) -> VerifiedTerm:
        return VerifiedTerm(**base, quote_id=quote_id, verified=False, reason=reason)

    if term.name not in TERM_NAMES:
        return fail(f"unknown term name '{term.name}'")
    if value is None:
        return fail("could not read a number")
    ordered = sorted(evidence, key=lambda e: e.source != term.source)  # the claimed source first
    match = next((e for e in ordered if fuzzy_contains(term.evidence_quote, e.text) >= FUZZY_MIN), None)
    if match is None:
        return fail("quote not found in what you showed or said")
    if not _number_in(value, unit, term.evidence_quote):
        return fail("the number is not in the quoted words", match.quote_id)
    if match.ocr_text is not None and not _number_in(value, unit, match.ocr_text):
        return fail("photo reading did not confirm the number", match.quote_id)
    if term.name == "flat_rate":  # the two rates give different EMIs, so the words decide, not the model
        context = _sentence_around(term.evidence_quote, match.text)
        if re.search(r"\breducing\b", context, re.I):
            base["name"] = "reducing_rate"
        elif not re.search(r"\bflat\b", context, re.I):
            return fail("not written as a flat rate", match.quote_id)
    is_photo = match.ocr_text is not None
    reading = ("twice" if vision_read else "once") if is_photo else "checked"
    return VerifiedTerm(
        **base | {"source": match.source},
        quote_id=match.quote_id,
        verified=True,
        photo=is_photo and vision_read,
        reading=reading,
    )


def verify_terms(
    terms: list[ExtractedTerm], evidence: list[EvidenceText], *, vision_read: bool = False
) -> list[VerifiedTerm]:
    return [verify_term(t, evidence, vision_read=vision_read) for t in terms]


def term_fact(t: VerifiedTerm) -> Fact | None:
    """A verified term as an offer fact (id "term.<name>") so agents may cite it."""
    if not t.verified or t.value is None:
        return None
    return Fact(
        id=f"term.{t.name}",
        label=f"From the document: {TERM_NAMES.get(t.name, t.name)}",
        value=t.value,
        unit=t.unit,
        kind="offer",
        formula="read from the document and checked twice",
        inputs={"quote_id": t.quote_id, "source": t.source, "photo": t.photo, "reading": t.reading},
    )
