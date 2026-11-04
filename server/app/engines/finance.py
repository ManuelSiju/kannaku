"""Deterministic money maths. Every public function returns Fact(s); no LLM anywhere.

Rates in and out are fractions (0.07 = 7%). Missing inputs are None and produce status "unknown" facts,
never zeros. Fact ids are fixed (listed per function); pass `prefix` to namespace them when one case needs
the same calculation twice (ids become "<prefix>.<id>").
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from app.engines.fact import Fact, FactKind, known, unknown

__all__ = [
    "Fact",
    "share_of",
    "affordability",
    "endowment_return",
    "fd_value",
    "flat_to_effective",
    "irr_annual",
    "irr_rate",
    "sip_value",
]

Number = float | int | Decimal
_IRR_LO, _IRR_HI = -0.99, 10.0


def _id(prefix: str, name: str) -> str:
    return f"{prefix}.{name}" if prefix else name


def _npv(rate: float, cashflows: Sequence[tuple[float, float]]) -> float:
    return sum(amount / (1 + rate) ** t for t, amount in cashflows)


def irr_rate(cashflows: Sequence[tuple[Number, Number]]) -> float | None:
    """Rate r with NPV(r) = 0 for (time, amount) flows, by bisection (robust, no derivative).
    Time is in periods (years for a yearly IRR). None when the flows never change sign."""
    flows = [(float(t), float(a)) for t, a in cashflows]
    if not flows or all(a >= 0 for _, a in flows) or all(a <= 0 for _, a in flows):
        return None
    lo, hi = _IRR_LO, _IRR_HI
    f_lo, f_hi = _npv(lo, flows), _npv(hi, flows)
    if f_lo * f_hi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        f_mid = _npv(mid, flows)
        if abs(f_mid) < 1e-9 or hi - lo < 1e-12:
            break
        if f_lo * f_mid < 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def irr_annual(cashflows: Sequence[tuple[Number, Number]], *, kind: FactKind = "offer", prefix: str = "") -> Fact:
    """id "irr": yearly internal rate of return of (year, amount) cash flows (outflows negative)."""
    rate = irr_rate(cashflows)
    label = "Yearly return of these money flows (IRR)"
    formula = "r such that sum(amount / (1 + r)^year) = 0"
    flows = [[float(t), float(a)] for t, a in cashflows]
    if rate is None:
        return unknown(_id(prefix, "irr"), label, "fraction", kind, formula, ["sign change"], cashflows=flows)
    return known(_id(prefix, "irr"), label, round(rate, 6), "fraction", kind, formula, cashflows=flows)


def endowment_return(premium: Number, pay_years: int, payout: Number, payout_year: Number, *, prefix: str = "") -> Fact:
    """id "endowment_return": yearly return of a policy where `premium` is paid at the START of each of
    `pay_years` years (years 0 .. pay_years-1) and `payout` is received at `payout_year`."""
    flows = [(year, -float(premium)) for year in range(int(pay_years))] + [(float(payout_year), float(payout))]
    rate = irr_rate(flows)
    label = "Yearly return of this policy: what you pay in vs what you get back"
    formula = "IRR of -premium at years 0..pay_years-1 and +payout at payout_year"
    inputs = dict(premium=premium, pay_years=pay_years, payout=payout, payout_year=payout_year)
    if rate is None:
        return unknown(_id(prefix, "endowment_return"), label, "fraction", "offer", formula, ["sign change"], **inputs)
    return known(_id(prefix, "endowment_return"), label, round(rate, 6), "fraction", "offer", formula, **inputs)


def fd_value(yearly_amount: Number, years: int, rate: Number, *, kind: FactKind = "offer", prefix: str = "") -> Fact:
    """id "fd_value": value after `years` of depositing `yearly_amount` at the start of each year into a
    fixed deposit at `rate` a year, compounded yearly (annuity-due future value)."""
    a, n, r = float(yearly_amount), int(years), float(rate)
    value = a * n if r == 0 else a * ((1 + r) ** n - 1) / r * (1 + r)
    return known(
        _id(prefix, "fd_value"),
        f"Value after {n} years if the same yearly amount went into a fixed deposit instead",
        round(value, 2),
        "INR",
        kind,
        "A * ((1+r)^n - 1) / r * (1+r)",
        yearly_amount=yearly_amount,
        years=years,
        rate=rate,
    )


def sip_value(
    monthly_amount: Number, months: int, annual_rate: Number, *, kind: FactKind = "offer", prefix: str = ""
) -> Fact:
    """id "sip_value": value of a monthly SIP after `months`, investing at the start of each month,
    compounded monthly at annual_rate / 12."""
    p, n, i = float(monthly_amount), int(months), float(annual_rate) / 12
    value = p * n if i == 0 else p * ((1 + i) ** n - 1) / i * (1 + i)
    return known(
        _id(prefix, "sip_value"),
        f"Value of a monthly SIP after {n} months",
        round(value, 2),
        "INR",
        kind,
        "P * ((1+i)^n - 1) / i * (1+i), i = annual_rate / 12",
        monthly_amount=monthly_amount,
        months=months,
        annual_rate=annual_rate,
    )


def reducing_loan(principal: Number, rate_annual: Number, months: int, *, prefix: str = "") -> list[Fact]:
    """Reducing-balance loan. Returns [loan_emi, loan_total_interest, loan_effective_rate]; the quoted yearly rate is
    already the real one. EMI = P * i * (1+i)^n / ((1+i)^n - 1), i = rate / 12."""
    p, r, n = float(principal), float(rate_annual), int(months)
    i = r / 12
    emi = p / n if i == 0 else p * i * (1 + i) ** n / ((1 + i) ** n - 1)
    inputs = dict(principal=principal, rate_annual=rate_annual, months=months)
    return [
        known(
            _id(prefix, "loan_emi"),
            "Monthly instalment (EMI)",
            round(emi, 2),
            "INR",
            "offer",
            "P * i * (1+i)^n / ((1+i)^n - 1), i = rate / 12",
            **inputs,
        ),
        known(
            _id(prefix, "loan_total_interest"),
            "Total interest paid over the loan",
            round(emi * n - p, 2),
            "INR",
            "offer",
            "EMI * months - P",
            **inputs,
        ),
        known(
            _id(prefix, "loan_effective_rate"),
            "Real yearly interest rate of this reducing-balance loan",
            r,
            "fraction",
            "offer",
            "the quoted reducing-balance rate",
            **inputs,
        ),
    ]


def flat_to_effective(principal: Number, flat_rate_annual: Number, months: int, *, prefix: str = "") -> list[Fact]:
    """Flat-rate loan. Returns [loan_emi, loan_total_interest, loan_effective_rate]:
    interest = principal * flat_rate * months / 12, EMI = (principal + interest) / months, and the
    equivalent reducing-balance yearly rate = monthly IRR * 12."""
    p, f, n = float(principal), float(flat_rate_annual), int(months)
    inputs = dict(principal=principal, flat_rate_annual=flat_rate_annual, months=months)
    interest = p * f * n / 12
    emi = (p + interest) / n
    monthly = irr_rate([(0, p)] + [(m, -emi) for m in range(1, n + 1)])
    facts = [
        known(
            _id(prefix, "loan_emi"),
            "Monthly instalment (EMI)",
            round(emi, 2),
            "INR",
            "offer",
            "(P + P * flat_rate * months / 12) / months",
            **inputs,
        ),
        known(
            _id(prefix, "loan_total_interest"),
            "Total interest paid over the loan",
            round(interest, 2),
            "INR",
            "offer",
            "P * flat_rate * months / 12",
            **inputs,
        ),
    ]
    label = "Real yearly interest rate (reducing balance) of this flat-rate loan"
    formula = "12 * monthly IRR of +P at month 0 and -EMI at months 1..n"
    if monthly is None:
        facts.append(
            unknown(_id(prefix, "loan_effective_rate"), label, "fraction", "offer", formula, ["irr"], **inputs)
        )
    else:
        facts.append(
            known(
                _id(prefix, "loan_effective_rate"),
                label,
                round(monthly * 12, 6),
                "fraction",
                "offer",
                formula,
                **inputs,
            )
        )
    return facts


def affordability(
    monthly_income: Number | None,
    monthly_expenses: Number | None,
    savings: Number | None,
    existing_emi: Number | None,
    new_monthly_cost: Number | None,
    *,
    regular_commitments: Number | None,
    prefix: str = "",
) -> list[Fact]:
    """Family affordability after a new monthly commitment. Returns [emi_share, buffer_months_after,
    surplus_after], all kind "personal". Any missing input makes the facts that need it "unknown" (None),
    never zero; pass 0 only when the family really has none.

    monthly_expenses     household spending, EXCLUDING loan EMIs and regular commitments
    existing_emi         loan EMIs already paid each month
    regular_commitments  other recurring payments per month, e.g. yearly policy premiums / 12 (not EMIs)
    new_monthly_cost     the new offer's cost per month (an EMI, or a yearly premium / 12)

    emi_share           = (existing_emi + new_monthly_cost) / monthly_income          (FOIR, fraction)
    buffer_months_after = savings / (monthly_expenses + existing_emi + regular_commitments + new_monthly_cost)
    surplus_after       = monthly_income - monthly_expenses - existing_emi - regular_commitments - new_monthly_cost
    """
    vals = dict(
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        savings=savings,
        existing_emi=existing_emi,
        regular_commitments=regular_commitments,
        new_monthly_cost=new_monthly_cost,
    )
    outgo_names = ("monthly_expenses", "existing_emi", "regular_commitments", "new_monthly_cost")

    def need(*names: str) -> list[str]:
        return [n for n in names if vals[n] is None]

    def f(name: str) -> float:
        return float(vals[name])  # type: ignore[arg-type]

    out: list[Fact] = []

    label = "Share of monthly income going to loan EMIs after this"
    formula = "(existing_emi + new_monthly_cost) / monthly_income"
    missing = need("monthly_income", "existing_emi", "new_monthly_cost")
    if missing or f("monthly_income") <= 0:
        out.append(
            unknown(
                _id(prefix, "emi_share"), label, "fraction", "personal", formula, missing or ["monthly_income"], **vals
            )
        )
    else:
        share = (f("existing_emi") + f("new_monthly_cost")) / f("monthly_income")
        out.append(known(_id(prefix, "emi_share"), label, round(share, 4), "fraction", "personal", formula, **vals))

    label = "Months your savings would cover all monthly costs after this"
    formula = "savings / (monthly_expenses + existing_emi + regular_commitments + new_monthly_cost)"
    missing = need("savings", *outgo_names)
    outgo = 0.0 if missing else sum(f(n) for n in outgo_names)
    if missing or outgo <= 0:
        out.append(
            unknown(
                _id(prefix, "buffer_months_after"),
                label,
                "months",
                "personal",
                formula,
                missing or ["monthly costs"],
                **vals,
            )
        )
    else:
        out.append(
            known(
                _id(prefix, "buffer_months_after"),
                label,
                round(f("savings") / outgo, 2),
                "months",
                "personal",
                formula,
                **vals,
            )
        )

    label = "Money left each month after all costs and this"
    formula = "monthly_income - monthly_expenses - existing_emi - regular_commitments - new_monthly_cost"
    missing = need("monthly_income", *outgo_names)
    if missing:
        out.append(unknown(_id(prefix, "surplus_after"), label, "INR", "personal", formula, missing, **vals))
    else:
        surplus = f("monthly_income") - sum(f(n) for n in outgo_names)
        out.append(known(_id(prefix, "surplus_after"), label, round(surplus, 2), "INR", "personal", formula, **vals))
    return out


def share_of(
    id: str, label: str, part: Number | None, whole: Number | None, *, kind: FactKind, formula: str, **inputs: object
) -> Fact:
    """part / whole as a fraction; unknown if either is missing or whole is not positive."""
    if part is None or whole is None or float(whole) <= 0:
        missing = [n for n, v in (("part", part), ("whole", whole)) if v is None] or ["positive whole"]
        return unknown(id, label, "fraction", kind, formula, missing, part=part, whole=whole, **inputs)
    return known(id, label, round(float(part) / float(whole), 4), "fraction", kind, formula, part=part, whole=whole,
                 **inputs)  # fmt: skip
