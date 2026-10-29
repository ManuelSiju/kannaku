"""Rule-based router: which specialists a case needs (max 3). Alfii (curator) is never routed; she always runs.

Flags (any of these may be set):
  market_linked      insurance whose returns depend on markets (ULIP)  -> adds vick
  amount_vs_savings  the amount matters relative to the family's savings -> adds sankz to fund/stock questions
  amount_large       alias of amount_vs_savings for stock tips
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

Agent = str  # "sankz" | "dani" | "vick"
MAX_AGENTS = 3

CASE_TYPES = {
    "insurance_offer",
    "ulip",
    "market_linked_insurance",
    "loan_offer",
    "sip_or_fund_question",
    "investment_question",
    "stock_tip",
    "shares",
    "ipo",
    "general_money",
    "general",
    "scam_or_payment_request",
    "out_of_scope",
}

# Unknown case types fall back to general_money; the pipeline classifies "unknown" with the LLM first.
FALLBACK_CASE_TYPE = "general_money"


def _flag_set(flags: Mapping[str, bool] | Iterable[str] | None) -> set[str]:
    if flags is None:
        return set()
    if isinstance(flags, Mapping):
        return {k for k, v in flags.items() if v}
    return set(flags)


def route(case_type: str, flags: Mapping[str, bool] | Iterable[str] | None = None) -> list[Agent]:
    f = _flag_set(flags)
    big_amount = bool(f & {"amount_vs_savings", "amount_large"})
    ct = case_type if case_type in CASE_TYPES else FALLBACK_CASE_TYPE

    if ct in ("scam_or_payment_request", "out_of_scope"):
        agents: list[Agent] = []
    elif ct in ("ulip", "market_linked_insurance") or (ct == "insurance_offer" and "market_linked" in f):
        agents = ["dani", "sankz", "vick"]
    elif ct == "insurance_offer":
        agents = ["dani", "sankz"]
    elif ct == "loan_offer":
        agents = ["sankz"]
    elif ct in ("sip_or_fund_question", "investment_question"):
        agents = ["dani", "sankz"] if big_amount else ["dani"]
    elif ct in ("stock_tip", "shares", "ipo"):
        agents = ["vick", "sankz"] if big_amount else ["vick"]
    else:  # general_money / general
        agents = ["sankz", "dani"]
    return agents[:MAX_AGENTS]
