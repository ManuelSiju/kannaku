"""Tool functions shared by the MCP server (server.py) and the in-process pipeline.

Every function returns a JSON-ready dict with a "facts" list of Fact.model_dump() objects, unchanged, so the
evidence checker can match their ids. Profile/item facts are kind "personal"; offer maths and reference rates
are kind "offer". Unknown values are facts with status "unknown" and value None, never zero.

Fact ids:
  profile.monthly_income | profile.monthly_expenses | profile.savings    (monthly_expenses excludes loan EMIs)
  existing_emi        sum of active confirmed loan items, per month
  regular_commitments other active confirmed recurring items per month (yearly premiums / 12), not EMIs
  item.<id>.amount    one family item
  holdings.*          mutual fund, share and SIP totals, as on the statement date (only when the family has some)
  tip.held_*          the family's own holding of the share in a tip (only when they hold it)
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
from app.db.repo import PROFILE_FIELDS, FamilyItem, NotConfirmed, ProfileValue, Repo
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
def _member_names(family_id: int, repo: Repo | None) -> dict[int, str]:
    return {m["id"]: m["name"] for m in _repo(repo).members(family_id)}


def _household_values(family_id: int, repo: Repo | None) -> dict[str, list[ProfileValue]]:
    """Per field, the values that count in the family budget. Without members, the latest one only."""
    values: dict[str, list[ProfileValue]] = {}
    for pv in _repo(repo).profile_values(family_id):
        if pv.in_household:
            values.setdefault(pv.field, []).append(pv)
    return values if get_settings().feature_members else {k: v[-1:] for k, v in values.items()}


def profile_facts(family_id: int, repo: Repo | None = None) -> list[Fact]:
    values = _household_values(family_id, repo)
    names = _member_names(family_id, repo)
    out = []
    for field in PROFILE_FIELDS:
        rows = values.get(field)
        fid, label = f"profile.{field}", _PROFILE_LABELS[field]
        if not rows:
            out.append(unknown(fid, label, "INR", "personal", "not told yet", [field]))
            continue
        pv = rows[0]
        members = {"members": [names.get(r.member_id, "") for r in rows]} if get_settings().feature_members else {}
        if len(rows) == 1:
            how, source, source_ref = f"confirmed value ({pv.source})", pv.source, pv.source_ref
        else:
            how, source, source_ref = f"sum of confirmed values ({', '.join(members['members'])})", "several", None
        out.append(
            known(
                fid,
                label,
                sum(r.value for r in rows),
                pv.unit,
                "personal",
                how,
                source=source,
                source_ref=source_ref,
                updated_at=max(r.updated_at for r in rows),
                **members,
            )
        )
    return out


def _budget_items(family_id: int, repo: Repo | None, kind: Any = None) -> list[FamilyItem]:
    return [i for i in _repo(repo).list_items(family_id, kind) if i.in_household]


def _owners(items: list[FamilyItem], family_id: int, repo: Repo | None) -> dict[str, list[str]]:
    if not get_settings().feature_members:
        return {}
    names = _member_names(family_id, repo)
    return {"members": sorted({names.get(i.member_id or 0, "Family") for i in items})}


def existing_emi_fact(family_id: int, repo: Repo | None = None, today: date | None = None) -> Fact:
    loans = [i for i in _budget_items(family_id, repo, "loan") if i.active_on(today or date.today())]
    total = sum(i.monthly_amount() for i in loans)
    return known(
        "existing_emi",
        "Loan EMIs the family already pays each month",
        round(total, 2),
        "INR",
        "personal",
        "sum of active confirmed loan items, per month",
        items=[i.id for i in loans],
        **_owners(loans, family_id, repo),
    )


def regular_commitments_fact(family_id: int, repo: Repo | None = None, today: date | None = None) -> Fact:
    day = today or date.today()
    sips = get_settings().feature_holdings
    items = [i for i in _budget_items(family_id, repo) if i.kind != "loan" and i.frequency != "once"]
    items = [i for i in items if i.active_on(day) and (sips or i.kind != "sip")]
    total = sum(i.monthly_amount() for i in items)
    return known(
        "regular_commitments",
        "Other regular payments each month, such as policy premiums (not loan EMIs)",
        round(total, 2),
        "INR",
        "personal",
        "sum of active confirmed non-loan items, per month (yearly / 12)",
        items=[i.id for i in items],
        **_owners(items, family_id, repo),
    )


def holdings_facts(family_id: int, repo: Repo | None = None) -> list[Fact]:
    """What the family has invested, from confirmed statements. Whoever holds it, and whether or not it counts in the
    budget: none of it is cash, so no budget or buffer figure uses it. Nothing here when the family has no holdings."""
    if not get_settings().feature_holdings:
        return []
    items = _repo(repo).list_items(family_id)
    funds = [i for i in items if i.kind == "mf_holding"]
    stocks = [i for i in items if i.kind == "stock_holding"]
    sips = [i for i in items if i.kind == "sip"]
    if not (funds or stocks or sips):
        return []
    owners = _owners(funds + stocks + sips, family_id, repo)

    def fact(fid: str, label: str, value: float, formula: str, unit: str = "INR") -> Fact:
        return known(fid, f"{label}, as on statement date", value, unit, "personal", formula, **owners)

    fund_total = sum(i.amount for i in funds)
    stock_total = sum(i.amount for i in stocks)
    out = [
        fact("holdings.mf_value_total", "Value of the family's mutual funds", fund_total, "sum of mutual fund values"),
        fact(
            "holdings.equity_mf_value",
            "Value of the family's equity mutual funds",
            sum(i.amount for i in funds if i.category == "equity"),
            "sum of mutual fund values with category equity",
        ),
        fact("holdings.stock_value_total", "Value of the family's shares", stock_total, "sum of share values"),
        fact(
            "holdings.total_value", "Value of all the family's investments", fund_total + stock_total, "funds + shares"
        ),
        fact("holdings.sip_monthly", "The family's SIPs each month", sum(i.amount for i in sips), "sum of SIP amounts"),
    ]
    if stock_total:
        out.append(
            fact(
                "holdings.largest_stock_share",
                "The biggest share as a part of all the family's shares",
                max(i.amount for i in stocks) / stock_total,
                "largest share value / value of all shares",
                "fraction",
            )
        )
    return out


def tip_holding_facts(family_id: int, symbol: str, repo: Repo | None = None) -> list[Fact]:
    """The family's own holding of a tipped share; nothing if they do not hold it."""
    if not get_settings().feature_holdings:
        return []
    stocks = _repo(repo).list_items(family_id, "stock_holding")
    held = [i for i in stocks if normalize_symbol(i.symbol or "") == normalize_symbol(symbol)]
    if not held:
        return []
    owners = _owners(held, family_id, repo)
    value = sum(i.amount for i in held)
    return [
        known(
            "tip.held_shares",
            f"Shares of {held[0].symbol} the family already holds, as on statement date",
            sum(i.units or 0 for i in held),
            "shares",
            "personal",
            "shares on the confirmed statement",
            **owners,
        ),
        known(
            "tip.held_value",
            f"Value of the family's {held[0].symbol} shares, as on statement date",
            value,
            "INR",
            "personal",
            "value on the confirmed statement",
            **owners,
        ),
        known(
            "tip.held_share_of_stocks",
            f"{held[0].symbol} as a part of all the family's shares, as on statement date",
            value / sum(i.amount for i in stocks),
            "fraction",
            "personal",
            "value of this share / value of all shares",
            **owners,
        ),
    ]


def family_get_profile(family_id: int, repo: Repo | None = None) -> dict[str, Any]:
    facts = profile_facts(family_id, repo)
    out: dict[str, Any] = {
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
    if get_settings().feature_members:
        rows = _repo(repo).profile_values(family_id)
        out["member_values"] = [
            {
                "member_id": m["id"],
                "name": m["name"],
                "role": m["role"],
                "values": [
                    {"field": r.field, "value": r.value, "source": r.source, "in_household": r.in_household}
                    for r in rows
                    if r.member_id == m["id"]
                ],
            }
            for m in _repo(repo).members(family_id)
        ]
        out["household"] = {f.id.removeprefix("profile."): f.value for f in facts}
    if get_settings().feature_snapshot:
        out["snapshot"] = family_snapshot(family_id, repo)
    return out


def family_snapshot(family_id: int, repo: Repo | None = None) -> dict[str, float | None]:
    """The family's money at a glance, every figure taken from a fact. Unknown stays None, never zero."""
    prof = {f.id.removeprefix("profile."): f.value for f in profile_facts(family_id, repo)}
    emi = existing_emi_fact(family_id, repo).value or 0.0
    regular = regular_commitments_fact(family_id, repo).value or 0.0
    held = {f.id: f.value for f in holdings_facts(family_id, repo)}
    afford = {
        f["id"]: f["value"] for f in calc_affordability(new_monthly_cost=0, family_id=family_id, repo=repo)["facts"]
    }
    spending = prof["monthly_expenses"]
    return {
        "savings": prof["savings"],
        "holdings_total": held.get("holdings.total_value"),
        "money_in": prof["monthly_income"],
        "money_out": None if spending is None else spending + emi + regular,
        "emi_share": afford.get("emi_share"),
    }


def _item_fact(item: FamilyItem) -> Fact:
    per = {"monthly": "a month", "yearly": "a year", "once": "once"}[item.frequency]
    held = item.kind in ("mf_holding", "stock_holding")
    return known(
        f"item.{item.id}.amount",
        f"{item.name}: value as on statement date" if held else f"{item.name}: amount paid {per}",
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


def family_list_documents(family_id: int, repo: Repo | None = None) -> dict[str, Any]:
    keep = ("id", "case_id", "filename", "doc_type", "terms", "times_seen", "first_seen", "last_seen")
    return {"documents": [{k: d[k] for k in keep} for d in _repo(repo).family_documents(family_id)]}


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
        "typical_personal_loan_rate": "Typical yearly interest rate of a normal bank personal loan (assumption)",
        "index_return_30d": "Stock-market index rise over the last 30 trading days (assumption)",
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
        if k in r  # optional assumptions (e.g. index_return_30d) only when the snapshot has them
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


def calc_reducing_loan(principal: float, rate_annual: float, months: int) -> dict[str, Any]:
    return {"facts": _dump(finance.reducing_loan(principal, rate_annual, months))}


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
