"""Tool functions shared by the MCP server (server.py) and the in-process pipeline.

Every function returns a JSON-ready dict with a "facts" list of Fact.model_dump() objects, unchanged, so the
evidence checker can match their ids. Profile/item facts are kind "personal"; offer maths and reference rates
are kind "offer". Unknown values are facts with status "unknown" and value None, never zero.

Fact ids:
  profile.monthly_income | profile.monthly_expenses | profile.savings    (monthly_expenses excludes loan EMIs)
  existing_emi        sum of active confirmed loan items, per month
  regular_commitments other active confirmed recurring items per month (yearly premiums / 12), not EMIs
  item.<id>.amount    one family item
  ref.fd_rate | ref.inflation | ref.index_long_run_return
  engine ids as in app.engines (irr, endowment_return, fd_value, sip_value, loan_*, emi_share, ...)
"""

from __future__ import annotations

import csv
import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import SERVER_ROOT, get_settings
from app.db.repo import PROFILE_FIELDS, FamilyItem, NotConfirmed, Repo
from app.engines import finance
from app.engines.fact import Fact, known, unknown
from app.engines.tip_signals import tip_signals

STOCKS_DIR = SERVER_ROOT / "demo_assets" / "stocks"

_PROFILE_LABELS = {
    "monthly_income": "Family's monthly income",
    "monthly_expenses": "Family's monthly household spending (not counting loan EMIs)",
    "savings": "Family's savings",
}


@lru_cache
def default_repo() -> Repo:
    return Repo(get_settings().db_path)


def _repo(repo: Repo | None) -> Repo:
    return repo or default_repo()


def _dump(facts: list[Fact]) -> list[dict[str, Any]]:
    return [f.model_dump() for f in facts]


# ---------------------------------------------------------------- family
def profile_facts(family_id: int, repo: Repo | None = None) -> list[Fact]:
    values = {pv.field: pv for pv in _repo(repo).profile_values(family_id)}
    out = []
    for field in PROFILE_FIELDS:
        pv = values.get(field)
        fid, label = f"profile.{field}", _PROFILE_LABELS[field]
        if pv is None:
            out.append(unknown(fid, label, "INR", "personal", "not told yet", [field]))
        else:
            out.append(
                known(
                    fid,
                    label,
                    pv.value,
                    pv.unit,
                    "personal",
                    f"confirmed value ({pv.source})",
                    source=pv.source,
                    source_ref=pv.source_ref,
                    updated_at=pv.updated_at,
                )
            )
    return out


def existing_emi_fact(family_id: int, repo: Repo | None = None, today: date | None = None) -> Fact:
    loans = [i for i in _repo(repo).list_items(family_id, "loan") if i.active_on(today or date.today())]
    total = sum(i.monthly_amount() for i in loans)
    return known(
        "existing_emi",
        "Loan EMIs the family already pays each month",
        round(total, 2),
        "INR",
        "personal",
        "sum of active confirmed loan items, per month",
        items=[i.id for i in loans],
    )


def regular_commitments_fact(family_id: int, repo: Repo | None = None, today: date | None = None) -> Fact:
    day = today or date.today()
    items = [i for i in _repo(repo).list_items(family_id) if i.kind != "loan" and i.frequency != "once"]
    items = [i for i in items if i.active_on(day)]
    total = sum(i.monthly_amount() for i in items)
    return known(
        "regular_commitments",
        "Other regular payments each month, such as policy premiums (not loan EMIs)",
        round(total, 2),
        "INR",
        "personal",
        "sum of active confirmed non-loan items, per month (yearly / 12)",
        items=[i.id for i in items],
    )


def family_get_profile(family_id: int, repo: Repo | None = None) -> dict[str, Any]:
    facts = profile_facts(family_id, repo)
    return {
        "family_id": family_id,
        "values": [
            {
                "field": f.id.removeprefix("profile."),
                "status": f.status,
                "value": f.value,
                "source": f.inputs.get("source"),
            }
            for f in facts
        ],
        "facts": _dump(facts + [existing_emi_fact(family_id, repo), regular_commitments_fact(family_id, repo)]),
    }


def _item_fact(item: FamilyItem) -> Fact:
    per = {"monthly": "a month", "yearly": "a year", "once": "once"}[item.frequency]
    return known(
        f"item.{item.id}.amount",
        f"{item.name}: amount paid {per}",
        item.amount,
        "INR",
        "personal",
        f"confirmed item ({item.source})",
        item_kind=item.kind,
        frequency=item.frequency,
        end_date=item.end_date,
        source=item.source,
    )


def family_list_items(family_id: int, kind: str | None = None, repo: Repo | None = None) -> dict[str, Any]:
    items = _repo(repo).list_items(family_id, kind)  # type: ignore[arg-type]
    return {"items": [i.model_dump() for i in items], "facts": _dump([_item_fact(i) for i in items])}


def family_save_item(family_id: int, item: dict[str, Any], confirmed: bool, repo: Repo | None = None) -> dict[str, Any]:
    """Refuses (saved=False) unless the family confirmed the item."""
    parsed = FamilyItem.model_validate(item)
    try:
        item_id = _repo(repo).save_item(family_id, parsed, confirmed)
    except NotConfirmed as e:
        return {"saved": False, "reason": str(e), "facts": []}
    parsed.id = item_id
    return {"saved": True, "item_id": item_id, "facts": _dump([_item_fact(parsed)])}


# ---------------------------------------------------------------- case
def case_get_terms(case_id: int, repo: Repo | None = None) -> dict[str, Any]:
    return {"case_id": case_id, "terms": _repo(repo).get_terms(case_id), "facts": []}


def case_get_quotes(case_id: int, repo: Repo | None = None) -> dict[str, Any]:
    return {"case_id": case_id, "quotes": [q.model_dump() for q in _repo(repo).get_quotes(case_id)], "facts": []}


# ---------------------------------------------------------------- reference rates
def reference_rates(path: Path | None = None) -> dict[str, Any]:
    return json.loads(Path(path or get_settings().reference_rates_path).read_text())


def rates_get_reference(path: Path | None = None) -> dict[str, Any]:
    r = reference_rates(path)
    as_of = r["as_of"]
    labels = {
        "fd_rate": "Typical fixed deposit interest rate (assumption)",
        "inflation": "Yearly price rise / inflation (assumption)",
        "index_long_run_return": "Long-run yearly return of a stock-market index fund (assumption)",
    }
    facts = [
        known(
            f"ref.{k}",
            f"{label}, as of {as_of}",
            r[k],
            "fraction",
            "offer",
            "reference snapshot",
            as_of=as_of,
            assumption=True,
        )
        for k, label in labels.items()
    ]
    return {"as_of": as_of, "note": r.get("note", ""), "facts": _dump(facts)}


# ---------------------------------------------------------------- stocks (local cache)
def normalize_symbol(symbol: str) -> str:
    """'ZEPHYRX LTD', 'NSE:ZEPHYRX', 'zephyrx.ns' -> 'ZEPHYRX' (company suffixes and exchange tags removed)."""
    s = symbol.upper().strip()
    s = re.sub(r"^(?:NSE|BSE)\s*[:\-]\s*", "", s)
    s = re.sub(r"\.(?:NS|BO)$", "", s)
    s = re.sub(r"\s+(?:LTD\.?|LIMITED|INC\.?|PVT\.?|CORP\.?)$", "", s)
    return "".join(ch for ch in s if ch.isalnum())


def known_symbols() -> list[str]:
    return sorted(f.stem for f in STOCKS_DIR.glob("*.csv"))


def find_known_symbol(text: str) -> str | None:
    """A ticker we have price history for, named as a whole word in the text (fallback when the case builder
    returns no usable stock_symbol)."""
    for sym in known_symbols():
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(sym)}(?![A-Za-z0-9])", text, re.I):
            return sym
    return None


def _stock_file(symbol: str) -> Path:
    return STOCKS_DIR / f"{normalize_symbol(symbol)}.csv"


def stocks_get_history(symbol: str) -> dict[str, Any]:
    path = _stock_file(symbol)
    if not path.exists():
        return {"symbol": normalize_symbol(symbol), "found": False, "rows": [], "facts": []}
    with path.open() as f:
        rows = [
            {"date": r["date"], "close": float(r["close"]), "volume": float(r["volume"])} for r in csv.DictReader(f)
        ]
    return {"symbol": normalize_symbol(symbol), "found": True, "rows": rows, "facts": []}


def stocks_tip_signals(symbol: str) -> dict[str, Any]:
    hist = stocks_get_history(symbol)
    if not hist["found"]:
        return {"symbol": hist["symbol"], "found": False, "facts": []}
    return {"symbol": hist["symbol"], "found": True, "facts": _dump(tip_signals(hist["rows"], symbol=hist["symbol"]))}


# ---------------------------------------------------------------- calculators
def calc_irr(cashflows: list[list[float]], kind: str = "offer") -> dict[str, Any]:
    """cashflows: [[year, amount], ...], money paid out negative."""
    return {"facts": _dump([finance.irr_annual([(t, a) for t, a in cashflows], kind=kind)])}  # type: ignore[arg-type]


def calc_endowment_return(premium: float, pay_years: int, payout: float, payout_year: float) -> dict[str, Any]:
    return {"facts": _dump([finance.endowment_return(premium, pay_years, payout, payout_year)])}


def calc_fd_value(yearly_amount: float, years: int, rate: float) -> dict[str, Any]:
    return {"facts": _dump([finance.fd_value(yearly_amount, years, rate)])}


def calc_sip_value(monthly_amount: float, months: int, annual_rate: float) -> dict[str, Any]:
    return {"facts": _dump([finance.sip_value(monthly_amount, months, annual_rate)])}


def calc_flat_to_effective(principal: float, flat_rate_annual: float, months: int) -> dict[str, Any]:
    return {"facts": _dump(finance.flat_to_effective(principal, flat_rate_annual, months))}


def calc_affordability(
    monthly_income: float | None = None,
    monthly_expenses: float | None = None,
    savings: float | None = None,
    existing_emi: float | None = None,
    new_monthly_cost: float | None = None,
    family_id: int | None = None,
    repo: Repo | None = None,
    regular_commitments: float | None = None,
) -> dict[str, Any]:
    """Explicit values win; with family_id, missing ones are filled from the confirmed profile and items."""
    if family_id is not None:
        prof = {f.id.removeprefix("profile."): f.value for f in profile_facts(family_id, repo)}
        monthly_income = monthly_income if monthly_income is not None else prof["monthly_income"]
        monthly_expenses = monthly_expenses if monthly_expenses is not None else prof["monthly_expenses"]
        savings = savings if savings is not None else prof["savings"]
        if existing_emi is None:
            existing_emi = existing_emi_fact(family_id, repo).value
        if regular_commitments is None:
            regular_commitments = regular_commitments_fact(family_id, repo).value
    facts = finance.affordability(
        monthly_income,
        monthly_expenses,
        savings,
        existing_emi,
        new_monthly_cost,
        regular_commitments=regular_commitments,
    )
    return {"facts": _dump(facts)}
