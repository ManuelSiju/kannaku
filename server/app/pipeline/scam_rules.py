"""Scam fast-path rules (code, no LLM). Any signal makes the verdict red before the council runs."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

ScamRule = Literal[
    "otp_pin_request", "remote_access", "digital_arrest", "kyc_urgency", "pay_to_receive", "collect_request"
]


class ScamSignal(BaseModel):
    rule: ScamRule
    source: Literal["transcript", "document"]
    matched_text: str
    explanation: str  # plain words, safe to show or say


# Python's \b fails next to Malayalam/Devanagari vowel signs, so word edges are "no ASCII letter" lookarounds.
_L, _R = r"(?<![A-Za-z])", r"(?![A-Za-z])"
_SECRET = r"(?:otp|one[\s-]*time[\s-]*password|pin|cvv|password|passcode|ഒടിപി|ഒ\.ടി\.പി|പിൻ|ओटीपी|पिन|पासवर्ड)"
_ASK = r"(?:share|tell|give|send|read\s*out|say|type|enter|forward|confirm|പറയ\w*|അയക്ക\w*|बताओ|बताइए|बताएं|भेजो|भेजें|दो)"
_NEGATION = re.compile(r"\b(?:never|don'?t|do\s+not|not|no\s+one|nobody|won'?t)\b[^.!?]{0,25}$", re.I)

_RULES: list[tuple[ScamRule, re.Pattern[str], str]] = [
    (
        "otp_pin_request",
        re.compile(
            rf"{_L}{_ASK}{_R}[^.!?]{{0,40}}{_L}{_SECRET}{_R}|{_L}{_SECRET}{_R}[^.!?]{{0,30}}{_L}{_ASK}{_R}", re.I
        ),
        "Someone is asking for your OTP, PIN, CVV or password. No real bank or company ever asks for these.",
    ),
    (
        "remote_access",
        re.compile(
            r"\b(?:any\s*desk|team\s*viewer|quick\s*support|rust\s*desk|airdroid|ultraviewer)\b"
            r"|\bscreen[\s-]*shar\w*",
            re.I,
        ),
        "Someone wants you to install a screen-sharing app. With it they can see and control your phone.",
    ),
    (
        "digital_arrest",
        re.compile(
            r"digital\s*arrest|ഡിജിറ്റൽ\s*അറസ്റ്റ്|डिजिटल\s*अरेस्ट"
            r"|\b(?:cbi|police|customs|narcotics|ncb|ed|enforcement\s+directorate)\b[^.!?]{0,60}"
            r"\b(?:video\s*call|skype|arrest(?:ed)?|warrant)\b",
            re.I,
        ),
        "There is no such thing as a 'digital arrest'. Police never arrest or demand money over a video call.",
    ),
    (
        "kyc_urgency",
        re.compile(
            r"(?<![A-Za-z])(?:kyc|കെവൈസി|केवाईसी)(?![A-Za-z])[^.!?]{0,60}\b(?:expir\w*|block\w*|suspend\w*|deactivat\w*|"
            r"clos\w*|freez\w*|band)\b|\b(?:account|sim|card)\b[^.!?]{0,40}\b(?:block\w*|suspend\w*|"
            r"deactivat\w*)\b[^.!?]{0,40}\bkyc\b",
            re.I,
        ),
        "A message says your KYC is expiring or your account will be blocked. Banks do not do this by call or "
        "link; visit your branch instead.",
    ),
    (
        "pay_to_receive",
        re.compile(
            r"\b(?:pay|send|transfer|deposit)\b[^.!?]{0,60}\b(?:to\s+(?:receive|get|claim|release|unlock)|"
            r"processing\s+fee|registration\s+fee|release\s+fee|tax\s+first)\b"
            r"|\b(?:lottery|prize|refund|cashback|reward|kbc)\b[^.!?]{0,60}\b(?:pay|send|fee)\b",
            re.I,
        ),
        "You are being asked to pay money in order to receive money. That is how this scam works.",
    ),
    (
        "collect_request",
        re.compile(
            r"\bcollect\s+request\b|\b(?:enter|type)\b[^.!?]{0,20}\b(?:upi\s+)?pin\b[^.!?]{0,30}"
            r"\bto\s+(?:receive|get)\b|\b(?:approve|accept)\b[^.!?]{0,30}\b(?:upi\s+)?request\b[^.!?]{0,40}"
            r"\b(?:receive|get|credit\w*)\b",
            re.I,
        ),
        "You never need to approve a request or enter your UPI PIN to receive money. Doing so sends money out.",
    ),
]


def _negated(text: str, start: int) -> bool:
    return bool(_NEGATION.search(text[max(0, start - 40) : start]))


def detect(transcript_text: str | None, doc_text: str | None) -> list[ScamSignal]:
    """One signal per rule per source; order follows the rule list."""
    out: list[ScamSignal] = []
    for source, text in (("transcript", transcript_text or ""), ("document", doc_text or "")):
        for rule, pattern, explanation in _RULES:
            for m in pattern.finditer(text):
                if rule == "otp_pin_request" and _negated(text, m.start()):
                    continue  # "never share your OTP" is advice, not a request
                out.append(ScamSignal(rule=rule, source=source, matched_text=m.group(0), explanation=explanation))
                break
    return out
