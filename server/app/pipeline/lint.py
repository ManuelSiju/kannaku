"""Speaking-style linter for every spoken line (code). A line that breaks a rule is regenerated once, then replaced by
a fallback. Rules: at most 2 sentences, at most 20 words per sentence, at most 1 number per sentence, no jargon,
no word repeated twice in a row, no vague verdict without a reason in the same line."""

from __future__ import annotations

import re

from app.pipeline.evidence import PLACEHOLDER, numbers_in

MAX_SENTENCES = 2
MAX_WORDS = 20
MAX_NUMBERS = 1
JARGON = re.compile(r"\b(IRR|XIRR|CAGR|FOIR|NAV|illustrat\w*|annuit\w*|amorti[sz]\w*|basis points?)\b", re.I)
VAGUE = re.compile(r"\b(this is risky|it'?s risky|risky|not worth it|bad idea|not good|be careful)\b", re.I)
REASON = re.compile(r"\b(because|since|as|so|which|while|but|than|only|if|when)\b", re.I)
REPEAT = re.compile(r"\b(\w+)\s+\1\b", re.I)
RULES = ("too_many_sentences", "sentence_too_long", "too_many_numbers", "jargon", "repeated_word", "vague")


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?।])\s+", text.strip())
    return [p for p in parts if p.strip()]


def lint(spoken: str, raw: str | None = None) -> list[str]:
    """Rule names the line breaks (empty = fine). `spoken` is the filled-in line; `raw` the model's text."""
    out: list[str] = []
    sents = sentences(spoken)
    if len(sents) > MAX_SENTENCES:
        out.append("too_many_sentences")
    if any(len(s.split()) > MAX_WORDS for s in sents):
        out.append("sentence_too_long")
    if any(len(numbers_in(s)) > MAX_NUMBERS for s in sents):
        out.append("too_many_numbers")
    if JARGON.search(spoken):
        out.append("jargon")
    if REPEAT.search(spoken):
        out.append("repeated_word")
    has_fact = bool(raw and PLACEHOLDER.search(raw)) or bool(numbers_in(spoken))
    if VAGUE.search(spoken) and not has_fact and not REASON.search(spoken):
        out.append("vague")
    return out
