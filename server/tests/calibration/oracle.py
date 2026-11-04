"""Independent checks of the key numbers: plain formulas, nothing imported from app.engines."""

from __future__ import annotations


def bisect(f, low: float, high: float) -> float:
    for _ in range(200):
        mid = (low + high) / 2
        if f(low) * f(mid) <= 0:
            high = mid
        else:
            low = mid
    return (low + high) / 2


def reducing_emi(principal: float, annual: float, months: int) -> float:
    r = annual / 12
    return principal * r * (1 + r) ** months / ((1 + r) ** months - 1)


def flat_loan(principal: float, annual: float, months: int) -> dict[str, float]:
    emi = principal * (1 + annual * months / 12) / months

    def npv(r: float) -> float:
        return principal - sum(emi / (1 + r) ** m for m in range(1, months + 1))

    return {"loan_emi": emi, "loan_effective_rate": 12 * bisect(npv, 1e-6, 0.2)}


def endowment_rate(premium: float, pay_years: int, payout: float, payout_year: float) -> float:
    def npv(r: float) -> float:
        return payout / (1 + r) ** payout_year - sum(premium / (1 + r) ** t for t in range(pay_years))

    return bisect(npv, -0.5, 1.0)


def sip_value(monthly: float, months: int, annual: float) -> float:
    i = annual / 12
    return sum(monthly * (1 + i) ** (months - m) for m in range(months))


def expected(spec: dict) -> dict[str, float]:
    """fact id -> value the fact must have. Rates in fractions, amounts in rupees."""
    kind = spec["kind"]
    if kind == "flat_loan":
        return flat_loan(spec["principal"], spec["rate"], spec["months"])
    if kind == "reducing_loan":
        return {"loan_emi": reducing_emi(spec["principal"], spec["rate"], spec["months"])}
    if kind == "endowment":
        args = (spec["premium"], spec["pay_years"], spec["payout"], spec["payout_year"])
        return {"endowment_return": endowment_rate(*args)}
    if kind == "sip":
        return {"sip_value": sip_value(spec["monthly"], spec["months"], spec["rate"])}
    if kind == "fd_lump":
        return {"fd_lump_value": spec["principal"] * (1 + spec["rate"]) ** spec["years"]}
    return {}


def compare(spec: dict, facts: dict[str, dict]) -> list[str]:
    """Empty = every number agrees: 0.1 percentage point for rates, ₹1 for amounts."""
    out = []
    for fid, want in expected(spec).items():
        fact = facts.get(fid)
        if fact is None or fact["value"] is None:
            out.append(f"{fid}: no fact (oracle {want:.4f})")
            continue
        limit = 0.001 if fact["unit"] == "fraction" else 1.0
        if abs(fact["value"] - want) > limit:
            out.append(f"{fid}: {fact['value']} but oracle {want:.4f}")
    return out
