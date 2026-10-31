"""Step 5 (code): every number the council may use, computed through the shared tool functions
(app.mcp_server.tools), the same code the MCP server exposes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.db.repo import Repo
from app.engines.compare import compare_rates
from app.engines.fact import Fact
from app.mcp_server import tools
from app.pipeline.verify_terms import VerifiedTerm, term_fact

# (term, fact id, words) — the lower illustration keeps the plain engine id "endowment_return"
RETURN_FACTS = [
    ("maturity_low", "endowment_return", "at the lower illustrated bonus"),
    ("maturity_high", "f_return_high", "at the higher illustrated bonus"),
    ("sum_assured", "f_return_guaranteed", "on the guaranteed amount only"),
]
RETURN_COMPARISONS = [
    ("endowment_return", "cmp_return_low_vs_fd", "at the lower illustrated bonus"),
    ("f_return_high", "cmp_return_high_vs_fd", "at the higher illustrated bonus"),
    ("f_return_guaranteed", "cmp_guaranteed_vs_fd", "on the guaranteed amount only"),
]
LARGE_SHARE_OF_SAVINGS = 0.25  # an amount above this share of savings brings Sankz in


class Computed(BaseModel):
    facts: list[Fact]
    missing_required: list[str]  # required terms not verified -> "at most yellow" + questions
    flags: list[str]
    commitment: float | None  # money the family would commit (for guardian alerts)


def _facts(result: dict[str, Any]) -> list[Fact]:
    return [Fact.model_validate(f) for f in result["facts"]]


def compute_facts(
    case_type: str,
    terms: list[VerifiedTerm],
    family_id: int,
    repo: Repo,
    *,
    stock_symbol: str | None = None,
    flags: list[str] | None = None,
) -> Computed:
    t = {x.name: x.value for x in terms if x.verified and x.value is not None}
    flags = list(flags or [])
    facts: list[Fact] = [f for f in (term_fact(x) for x in terms) if f is not None]
    profile = _facts(tools.family_get_profile(family_id, repo))
    facts += profile
    facts += _facts(tools.rates_get_reference())  # every agent may compare against these assumptions
    savings = next((f.value for f in profile if f.id == "profile.savings"), None)
    rates = tools.reference_rates()
    missing: list[str] = []
    commitment: float | None = None

    def need(*names: str) -> bool:
        absent = [n for n in names if n not in t]
        missing.extend(a for a in absent if a not in missing)
        return not absent

    def afford(new_monthly_cost: float) -> None:
        facts.extend(
            _facts(tools.calc_affordability(new_monthly_cost=new_monthly_cost, family_id=family_id, repo=repo))
        )

    if case_type in ("insurance_offer", "ulip"):
        years = t.get("pay_years") or t.get("policy_years")
        if "pay_years" not in t and "policy_years" not in t:
            missing.append("pay_years")
        has_premium = need("premium")
        if not any(k in t for k in ("maturity_low", "maturity_high", "sum_assured")):
            missing.append("maturity_low")
        if has_premium and years:
            premium, payout_year = t["premium"], t.get("policy_years") or years
            commitment = premium
            returns: dict[str, Fact] = {}
            for key, fid, what in RETURN_FACTS:
                if key in t:
                    f = _facts(tools.calc_endowment_return(premium, int(years), t[key], payout_year))[0]
                    if fid != f.id:
                        f = f.model_copy(update={"id": fid, "label": f"{f.label} ({what})"})
                    returns[fid] = f
                    facts.append(f)
            facts += _facts(tools.calc_fd_value(premium, int(years), rates["fd_rate"]))
            fd = next(f for f in facts if f.id == "ref.fd_rate")
            for fid, cmp_id, what in RETURN_COMPARISONS:
                if fid in returns:
                    facts.append(
                        compare_rates(
                            cmp_id, f"This plan's yearly return {what}, compared with a fixed deposit", returns[fid], fd
                        )
                    )
            afford(premium / 12)

    elif case_type == "loan_offer":
        if need("loan_amount", "flat_rate", "tenure_months"):
            loan = _facts(tools.calc_flat_to_effective(t["loan_amount"], t["flat_rate"], int(t["tenure_months"])))
            facts += loan
            commitment = t["loan_amount"]
            emi = next(f.value for f in loan if f.id == "loan_emi")
            afford(float(emi or 0))
            effective = next(f for f in loan if f.id == "loan_effective_rate")
            quoted = next(f for f in facts if f.id == "term.flat_rate")
            facts.append(
                compare_rates(
                    "cmp_effective_vs_quoted",
                    "The loan's real yearly rate compared with the flat rate it was sold at",
                    effective,
                    quoted,
                )
            )

    elif case_type in ("stock_tip", "shares", "ipo"):
        if stock_symbol:
            signals = tools.stocks_tip_signals(stock_symbol)
            if signals["found"]:
                facts += _facts(signals)
            else:
                missing.append("price history")
        else:
            missing.append("stock name")
        if "invest_amount" in t:
            commitment = t["invest_amount"]
            if savings is None or t["invest_amount"] > LARGE_SHARE_OF_SAVINGS * savings:
                flags.append("amount_large")

    elif case_type == "sip_or_fund_question":
        if need("monthly_amount"):
            months = int(t.get("years", 10) * 12)
            facts += _facts(tools.calc_sip_value(t["monthly_amount"], months, rates["index_long_run_return"]))
            commitment = t["monthly_amount"] * 12
            afford(t["monthly_amount"])
            if savings is None or t["monthly_amount"] * 12 > LARGE_SHARE_OF_SAVINGS * savings:
                flags.append("amount_vs_savings")

    return Computed(facts=facts, missing_required=missing, flags=flags, commitment=commitment)
