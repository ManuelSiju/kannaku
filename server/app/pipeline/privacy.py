"""Privacy: in DISCREET mode no spoken line may reveal the family's own money (personal facts).

speech_allowed(...) -> Allowed | Blocked(reason). Blocked lines go to the screen only.
decide_mode(...) -> "full" | "discreet". Default is discreet.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel

from app.pipeline.evidence import Facts, as_fact_map, numbers_in, value_matches

PrivacyMode = Literal["full", "discreet"]
DEFAULT_MODE: PrivacyMode = "discreet"


class Allowed(BaseModel):
    allowed: Literal[True] = True


class Blocked(BaseModel):
    allowed: Literal[False] = False
    reason: str


def speech_allowed(line_text: str, cited_ids: Iterable[str], facts: Facts, mode: PrivacyMode) -> Allowed | Blocked:
    if mode == "full":
        return Allowed()
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
                if isinstance(v, int | float) and not isinstance(v, bool) and value_matches(n, float(v), "INR"):
                    return Blocked(reason=f"says '{n.text}', which is the family's own {k}")
    return Allowed()


def decide_mode(earphones: bool, user_says_alone: bool, second_speaker: bool | None, context_cue: bool) -> PrivacyMode:
    """Full (speak personal amounts) only if the user is private (earphones or says they are alone), no second
    speaker was detected, and nothing in the conversation suggests someone else is present."""
    if (earphones or user_says_alone) and second_speaker is not True and not context_cue:
        return "full"
    return "discreet"
