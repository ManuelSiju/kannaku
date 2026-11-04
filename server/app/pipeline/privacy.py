"""Privacy: in DISCREET mode no spoken line may reveal the family's own money (personal facts).

speech_allowed(...) -> Allowed | Blocked(reason). Blocked lines go to the screen only.
decide_mode(...) -> "full" | "discreet". Default is discreet.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel

from app.pipeline.evidence import Facts, as_fact_map, numbers_in, value_matches

PrivacyMode = Literal["full", "discreet"]
# raw inputs of personal facts that are the family's own money
PERSONAL_INPUTS = {"monthly_income", "monthly_expenses", "savings", "existing_emi", "regular_commitments"}


class Allowed(BaseModel):
    allowed: Literal[True] = True


class Blocked(BaseModel):
    allowed: Literal[False] = False
    reason: str


# Words that point at the family's own money. In discreet mode a spoken line may not use them even without a number
# ("Given your monthly income and high expenses..." tells a listener plenty).
PERSONAL_WORDS = re.compile(
    r"(?<![A-Za-z])(?:income|salary|salaries|savings?|saved|expenses?|expenditure|spending|EMIs?|your\s+loans?|"
    r"your\s+budget|budget|afford\w*|pension)(?![A-Za-z])"
    r"|വരുമാന\w*|ശമ്പള\w*|സമ്പാദ്യ\w*|ചെലവ്\w*|ചിലവ്\w*|ഇഎംഐ|ബജറ്റ്\w*"
    r"|आय|आमदनी|वेतन|तनख़्वाह|तनख्वाह|बचत|ख़र्च\w*|खर्च\w*|ईएमआई|बजट",
    re.I,
)


def speech_allowed(line_text: str, cited_ids: Iterable[str], facts: Facts, mode: PrivacyMode) -> Allowed | Blocked:
    if mode == "full":
        return Allowed()
    if m := PERSONAL_WORDS.search(line_text):
        return Blocked(reason=f"personal word '{m.group(0)}' in discreet mode")
    fact_map = as_fact_map(facts)
    for cid in cited_ids:
        f = fact_map.get(cid)
        if f is not None and f.kind == "personal":
            return Blocked(reason=f"cites personal fact {cid}")
    personal = [f for f in fact_map.values() if f.kind == "personal"]
    for n in numbers_in(line_text):
        for f in personal:
            if value_matches(n, f.value, f.unit):
                return Blocked(reason=f"says '{n.text}', which is the family's own {f.id}")
            # personal facts' raw inputs (income, savings, ...) are personal amounts too
            for k, v in f.inputs.items():
                if k not in PERSONAL_INPUTS:
                    continue  # e.g. new_monthly_cost is the offer's own price, not the family's money
                if isinstance(v, int | float) and not isinstance(v, bool) and value_matches(n, float(v), "INR"):
                    return Blocked(reason=f"says '{n.text}', which is the family's own {k}")
    return Allowed()


def decide_mode(earphones: bool, user_says_alone: bool, second_speaker: bool | None, context_cue: bool) -> PrivacyMode:
    """Full (speak personal amounts) only if the user is private (earphones or says they are alone), no second
    speaker was detected, and nothing in the conversation suggests someone else is present."""
    if (earphones or user_says_alone) and second_speaker is not True and not context_cue:
        return "full"
    return "discreet"
