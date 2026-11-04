"""Step 5 (code): every number the council may use, computed through the shared tool functions
(app.mcp_server.tools), the same code the MCP server exposes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.db.repo import Repo
from app.engines.compare import compare_rates
from app.engines.fact import Fact
from app.engines.finance import share_of
from app.mcp_server import tools
from app.pipeline.verify_terms import VerifiedTerm, term_fact

# (term, fact id, words) — the lower bonus keeps the plain engine id "endowment_return"
RETURN_FACTS = [
    ("maturity_low", "endowment_return", "at the lower bonus rate"),
    ("maturity_high", "f_return_high", "at the higher bonus rate"),
    ("sum_assured", "f_return_guaranteed", "on the guaranteed amount only"),
]
# (return fact, comparison id suffix, words)
RETURN_COMPARISONS = [
    ("endowment_return", "return_low", "at the lower bonus rate"),
    ("f_return_high", "return_high", "at the higher bonus rate"),
    ("f_return_guaranteed", "guaranteed", "on the guaranteed amount only"),
]
BENCHMARKS = [("ref.fd_rate", "fd", "a fixed deposit"), ("ref.inflation", "inflation", "rising prices (inflation)")]
LARGE_SHARE_OF_SAVINGS = 0.25  # an amount above this share of savings brings Sankz in
MISSING_PAIR_QUESTION = {
    "maturity_low": "What do I get at the lower bonus rate?",
    "maturity_high": "What do I get at the higher bonus rate?",
}


class Computed(BaseModel):
    facts: list[Fact]
    missing_required: list[str]  # required terms not verified -> "at most yellow" + questions
    flags: list[str]
    commitment: float | None  # money the family would commit (for guardian alerts)
    questions: list[str] = []  # code-written "ask him this" questions (e.g. a missing illustration amount)


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
    by_id = lambda fid: next((f for f in facts if f.id == fid), None)  # noqa: E731
    savings = by_id("profile.savings").value if by_id("profile.savings") else None
    income = by_id("profile.monthly_income").value if by_id("profile.monthly_income") else None
    rates = tools.reference_rates()
    missing: list[str] = []
    questions: list[str] = []
    commitment: float | None = None

    def need(*names: str) -> bool:
        absent = [n for n in names if n not in t]
        missing.extend(a for a in absent if a not in missing)
        return not absent

    def afford_emi(new_emi: float) -> None:
        """A loan: the new EMI counts in the EMI share."""
        facts.extend(_facts(tools.calc_affordability(new_monthly_cost=new_emi, family_id=family_id, repo=repo)))

    def afford_commitment(monthly: float) -> None:
        """A premium or SIP is a regular commitment, not an EMI: it counts in the buffer and the surplus, while the
        EMI share stays at the family's existing loans."""
        existing = tools.regular_commitments_fact(family_id, repo).value or 0.0
        facts.extend(
            _facts(
                tools.calc_affordability(
                    new_monthly_cost=0, regular_commitments=existing + monthly, family_id=family_id, repo=repo
                )
            )
        )

    def compare(cmp_id: str, label: str, a_id: str, b_id: str) -> None:
        a, b = by_id(a_id), by_id(b_id)
        if a is not None and b is not None:
            facts.append(compare_rates(cmp_id, label, a, b))

    if case_type in ("insurance_offer", "ulip"):
        years = t.get("pay_years") or t.get("policy_years")
        if "pay_years" not in t and "policy_years" not in t:
            missing.append("pay_years")
        has_premium = need("premium")
        if not any(k in t for k in ("maturity_low", "maturity_high", "sum_assured")):
            missing.append("maturity_low")
        for key, other in (("maturity_low", "maturity_high"), ("maturity_high", "maturity_low")):
            if other in t and key not in t:  # illustrations come in pairs; ask for the one we could not read
                missing.append(key)
                questions.append(MISSING_PAIR_QUESTION[key])
        if has_premium and years:
            premium, payout_year = t["premium"], t.get("policy_years") or years
            commitment = premium
            for key, fid, what in RETURN_FACTS:
                if key in t:
                    f = _facts(tools.calc_endowment_return(premium, int(years), t[key], payout_year))[0]
                    if fid != f.id:
                        f = f.model_copy(update={"id": fid, "label": f"{f.label} ({what})"})
                    facts.append(f)
            facts += _facts(tools.calc_fd_value(premium, int(years), rates["fd_rate"]))
            for fid, suffix, what in RETURN_COMPARISONS:
                for bench_id, bench, bench_words in BENCHMARKS:
                    compare(
                        f"cmp_{suffix}_vs_{bench}",
                        f"This plan's yearly return {what}, compared with {bench_words}",
                        fid,
                        bench_id,
                    )
            afford_commitment(premium / 12)
            facts += tools.holdings_facts(family_id, repo)
            facts.append(
                share_of(
                    "premium_share_of_income",
                    "The premium per month as a share of your monthly income",
                    premium / 12,
                    income,
                    kind="personal",
                    formula="(premium / 12) / monthly_income",
                )
            )
            facts.append(
                share_of(
                    "premium_share_of_savings",
                    "One year's premium as a share of your savings",
                    premium,
                    savings,
                    kind="personal",
                    formula="premium / savings",
                )
            )

    elif case_type == "loan_offer":
        if need("loan_amount", "flat_rate", "tenure_months"):
            loan = _facts(tools.calc_flat_to_effective(t["loan_amount"], t["flat_rate"], int(t["tenure_months"])))
            facts += loan
            commitment = t["loan_amount"]
            emi = next(f.value for f in loan if f.id == "loan_emi")
            afford_emi(float(emi or 0))
            compare(
                "cmp_effective_vs_quoted",
                "The loan's real yearly rate compared with the flat rate it was sold at",
                "loan_effective_rate",
                "term.flat_rate",
            )
            compare(
                "cmp_effective_vs_typical",
                "The loan's real yearly rate compared with a normal bank personal loan (assumption)",
                "loan_effective_rate",
                "ref.typical_personal_loan_rate",
            )

    elif case_type in ("stock_tip", "shares", "ipo"):
        facts += tools.holdings_facts(family_id, repo)
        if stock_symbol:
            facts += tools.tip_holding_facts(family_id, stock_symbol, repo)
            signals = tools.stocks_tip_signals(stock_symbol)
            if signals["found"]:
                facts += _facts(signals)
                compare(
                    "cmp_run_up_vs_index",
                    "This share's rise compared with the market index over the same days",
                    "run_up_30d",
                    "ref.index_return_30d",
                )
            else:
                missing.append("price history")
        else:
            missing.append("stock name")
        if "invest_amount" in t:
            commitment = t["invest_amount"]
            facts.append(
                share_of(
                    "invest_share_of_savings",
                    "The amount you would put in, as a share of your savings",
                    t["invest_amount"],
                    savings,
                    kind="personal",
                    formula="invest_amount / savings",
                )
            )
            if savings is None or t["invest_amount"] > LARGE_SHARE_OF_SAVINGS * savings:
                flags.append("amount_large")

    elif case_type == "sip_or_fund_question":
        if need("monthly_amount"):
            months = int(t.get("years", 10) * 12)
            facts += _facts(tools.calc_sip_value(t["monthly_amount"], months, rates["index_long_run_return"]))
            commitment = t["monthly_amount"] * 12
            afford_commitment(t["monthly_amount"])
            if savings is None or t["monthly_amount"] * 12 > LARGE_SHARE_OF_SAVINGS * savings:
                flags.append("amount_vs_savings")

    if any(f.id.startswith("holdings.") for f in facts):
        facts = [
            f.model_copy(update={"formula": f"{f.formula} (bank savings only: investments are not cash)"})
            if f.id == "buffer_months_after"
            else f
            for f in facts
        ]
    return Computed(facts=facts, missing_required=missing, flags=flags, commitment=commitment, questions=questions)
