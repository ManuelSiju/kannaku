"""Every figure of the demo cases, recomputed without our engines. Run from server/ after make meta-run:

    ../.venv/bin/python -m tests.calibration.numbers_audit

Reads docs/reports/meta_run_facts.json, writes docs/reports/numbers_audit.md. Exit code 1 on any mismatch.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from tests.calibration.oracle import endowment_rate, flat_loan

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs" / "reports"
INCOME, EXPENSES, SAVINGS, EMI, REGULAR = 45_000, 28_000, 160_000, 2_400, 12_000 / 12


def afford(new: float) -> dict[str, float]:
    return {
        "surplus_after": INCOME - EXPENSES - EMI - REGULAR - new,
        "buffer_months_after": SAVINGS / (EXPENSES + EMI + REGULAR + new),
    }


def endowment() -> dict[str, float]:
    premium, years = 50_000, 15
    fd = sum(premium * 1.07 ** (years - t) for t in range(years))
    return {
        "term.premium": premium,
        "term.sum_assured": 750_000,
        "term.maturity_low": 1_020_000,
        "term.maturity_high": 1_500_000,
        "endowment_return": endowment_rate(premium, years, 1_020_000, years),
        "f_return_high": endowment_rate(premium, years, 1_500_000, years),
        "f_return_guaranteed": endowment_rate(premium, years, 750_000, years),
        "fd_value": fd,
        "premium_share_of_income": premium / 12 / INCOME,
        "premium_share_of_savings": premium / SAVINGS,
        "emi_share": EMI / INCOME,
        **afford(premium / 12),
    }


def loan() -> dict[str, float]:
    got = flat_loan(100_000, 0.12, 24)
    return {
        **got,
        "loan_total_interest": 100_000 * 0.12 * 2,
        "emi_share": (EMI + got["loan_emi"]) / INCOME,
        **afford(got["loan_emi"]),
    }


def tip() -> dict[str, float]:
    path = ROOT / "server" / "demo_assets" / "stocks" / "ZEPHYRX.csv"
    rows = sorted(csv.DictReader(path.open()), key=lambda r: r["date"])
    close = [float(r["close"]) for r in rows]
    volume = [float(r["volume"]) for r in rows]
    recent = sum(volume[-5:]) / 5
    base = sum(volume[-65:-5]) / 60
    return {
        "run_up_30d": close[-1] / close[-31] - 1,
        "volume_spike": recent / base,
        "invest_share_of_savings": 100_000 / SAVINGS,
    }


def main() -> int:
    data = json.loads((REPORT / "meta_run_facts.json").read_text())["facts"]
    lines = ["# Numbers audit\n", "Recomputed from the inputs with plain formulas, not our engines.\n"]
    bad = 0
    for name, want in (("endowment PDF", endowment()), ("flat loan", loan()), ("ZEPHYRX tip", tip())):
        facts = {f["id"]: f for f in data[name]}
        lines += [f"## {name}\n", "| figure | shown | oracle | match |", "|---|---|---|---|"]
        for fid, value in want.items():
            fact = facts.get(fid)
            if fact is None:
                lines.append(f"| {fid} | not in this run | {value:.4f} | n/a |")
                continue
            limit = 0.001 if fact["unit"] == "fraction" else 0.05 if fact["unit"] in ("months", "times") else 1
            ok = abs(fact["value"] - value) <= limit
            bad += not ok
            lines.append(f"| {fid} | {fact['display']} ({fact['value']}) | {value:.4f} | {'yes' if ok else 'NO'} |")
        lines.append("")
    (REPORT / "numbers_audit.md").write_text("\n".join(lines))
    print(f"mismatches: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
