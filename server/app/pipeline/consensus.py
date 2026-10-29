"""Weighted vote of the called specialists, then safety overrides (code beats the vote).

stance s in {+1 for, 0 unsure, -1 against}; strength c in [0, 1]; weight w > 0 by case type, renormalised
over the called agents.
  S = sum(w*s*c) / sum(w for s != 0)          (0 if everyone is unsure)
  verdict: S > 0.2 green; S < -0.2 red; else yellow
  D = weighted std dev of s, weights w*c, over non-unsure agents (0 if fewer than 2 voters)
  debate_needed = D > 0.4
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Literal

from pydantic import BaseModel, Field

from app.engines.fact import Fact
from app.pipeline.evidence import as_fact_map

Colour = Literal["red", "yellow", "green"]
Stance = Literal["for", "against", "unsure"]
STANCE_VALUE: dict[str, int] = {"for": 1, "unsure": 0, "against": -1}

GREEN_ABOVE = 0.2
RED_BELOW = -0.2
DEBATE_ABOVE = 0.4

WEIGHTS: dict[str, dict[str, float]] = {
    "insurance_offer": {"dani": 0.4, "sankz": 0.4, "vick": 0.2},
    "loan_offer": {"sankz": 1.0},
    "stock_tip": {"vick": 0.6, "sankz": 0.4},
    "investment_question": {"sankz": 0.5, "dani": 0.5},
    "general": {"sankz": 0.5, "dani": 0.5},
}
WEIGHT_GROUP = {
    "ulip": "insurance_offer",
    "market_linked_insurance": "insurance_offer",
    "shares": "stock_tip",
    "ipo": "stock_tip",
    "sip_or_fund_question": "investment_question",
    "general_money": "general",
}
DEFAULT_WEIGHT = 0.2  # an agent called outside its usual case type still counts, a little


class Position(BaseModel):
    agent: str
    stance: Stance
    strength: float = Field(ge=0, le=1)

    @property
    def s(self) -> int:
        return STANCE_VALUE[self.stance]


class OverrideInputs(BaseModel):
    """Safety facts the overrides look at. Shares are fractions (0.45 = 45%). None = unknown = no override."""

    scam: bool = False
    buffer_months_after: float | None = None
    emi_share: float | None = None
    surplus_after: float | None = None
    guaranteed_claim_unbacked: bool = False  # seller said "guaranteed", the document does not guarantee it
    unverified_required_terms: list[str] = []


class Override(BaseModel):
    rule: str
    effect: Literal["red", "max_yellow", "min_yellow"]
    detail: str


class ConsensusResult(BaseModel):
    verdict: Colour
    vote_verdict: Colour  # before overrides
    score: float
    disagreement: float
    debate_needed: bool
    weights: dict[str, float]
    overrides: list[Override]


def weights_for(case_type: str, agents: Iterable[str]) -> dict[str, float]:
    table = WEIGHTS.get(WEIGHT_GROUP.get(case_type, case_type), WEIGHTS["general"])
    raw = {a: table.get(a, DEFAULT_WEIGHT) for a in agents}
    total = sum(raw.values())
    return {a: w / total for a, w in raw.items()} if total else {}


def vote(positions: list[Position], weights: Mapping[str, float]) -> tuple[float, float]:
    """(S, D)."""
    voters = [p for p in positions if p.s != 0]
    denom = sum(weights[p.agent] for p in voters)
    score = sum(weights[p.agent] * p.s * p.strength for p in voters) / denom if denom else 0.0
    wc = [(weights[p.agent] * p.strength, p.s) for p in voters]
    total = sum(w for w, _ in wc)
    if len(voters) < 2 or total == 0:
        return score, 0.0
    mean = sum(w * s for w, s in wc) / total
    disagreement = math.sqrt(sum(w * (s - mean) ** 2 for w, s in wc) / total)
    return score, disagreement


def verdict_from_score(score: float) -> Colour:
    if score > GREEN_ABOVE:
        return "green"
    if score < RED_BELOW:
        return "red"
    return "yellow"


def overrides_for(o: OverrideInputs) -> list[Override]:
    out: list[Override] = []
    if o.scam:
        out.append(Override(rule="scam_signal", effect="red", detail="scam signal detected"))
    if o.buffer_months_after is not None:
        if o.buffer_months_after < 1:
            out.append(
                Override(
                    rule="buffer_under_1_month",
                    effect="red",
                    detail=f"savings cover {o.buffer_months_after:.1f} months",
                )
            )
        elif o.buffer_months_after < 3:
            out.append(
                Override(
                    rule="buffer_under_3_months",
                    effect="max_yellow",
                    detail=f"savings cover {o.buffer_months_after:.1f} months",
                )
            )
    if o.emi_share is not None:
        if o.emi_share > 0.60:
            out.append(Override(rule="emi_share_over_60", effect="red", detail=f"EMIs take {o.emi_share:.0%}"))
        elif o.emi_share > 0.40:
            out.append(Override(rule="emi_share_over_40", effect="max_yellow", detail=f"EMIs take {o.emi_share:.0%}"))
    if o.surplus_after is not None and o.surplus_after < 0:
        out.append(Override(rule="negative_surplus", effect="red", detail=f"monthly shortfall {o.surplus_after:.0f}"))
    if o.guaranteed_claim_unbacked:
        out.append(
            Override(rule="unbacked_guarantee", effect="min_yellow", detail="seller said guaranteed; document does not")
        )
    if o.unverified_required_terms:
        out.append(
            Override(
                rule="unverified_terms",
                effect="max_yellow",
                detail="unverified: " + ", ".join(o.unverified_required_terms),
            )
        )
    return out


def apply_overrides(colour: Colour, overrides: list[Override]) -> Colour:
    if any(o.effect == "red" for o in overrides):
        return "red"
    # "at most yellow" and "at least yellow" both mean: not green
    if colour == "green" and any(o.effect in ("max_yellow", "min_yellow") for o in overrides):
        return "yellow"
    return colour


def run_consensus(
    case_type: str, positions: list[Position], override_inputs: OverrideInputs | None = None
) -> ConsensusResult:
    weights = weights_for(case_type, [p.agent for p in positions])
    score, disagreement = vote(positions, weights)
    vote_colour = verdict_from_score(score)
    overrides = overrides_for(override_inputs or OverrideInputs())
    return ConsensusResult(
        verdict=apply_overrides(vote_colour, overrides),
        vote_verdict=vote_colour,
        score=round(score, 4),
        disagreement=round(disagreement, 4),
        debate_needed=disagreement > DEBATE_ABOVE,
        weights={a: round(w, 4) for a, w in weights.items()},
        overrides=overrides,
    )


def override_inputs_from_facts(
    facts: Mapping[str, Fact] | Iterable[Fact],
    *,
    scam: bool = False,
    guaranteed_claim_unbacked: bool = False,
    unverified_required_terms: list[str] | None = None,
) -> OverrideInputs:
    """Read emi_share / buffer_months_after / surplus_after facts (by id, prefix allowed) into OverrideInputs."""
    found: dict[str, float | None] = {}
    for f in as_fact_map(facts).values():
        base = f.id.rsplit(".", 1)[-1]
        if base in ("emi_share", "buffer_months_after", "surplus_after") and f.value is not None:
            found[base] = f.value
    return OverrideInputs(
        scam=scam,
        guaranteed_claim_unbacked=guaranteed_claim_unbacked,
        unverified_required_terms=unverified_required_terms or [],
        **found,
    )
