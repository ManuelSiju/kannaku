"""Fact: one number produced by deterministic code. Agents may only quote numbers they cite as facts.

Conventions (shared by every engine):
- Money is in rupees (unit "INR"); durations in "years" / "months"; counts in "count".
- Rates, returns and shares are FRACTIONS with unit "fraction" (0.038 means 3.8%), so thresholds such as
  emi_share > 0.60 compare directly. Use `Fact.display` for the spoken/screen form.
- Missing inputs never become zero: value is None and status is "unknown".
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

FactKind = Literal["offer", "personal"]


class Fact(BaseModel):
    id: str
    label: str  # plain words, says exactly what is measured
    value: float | None
    unit: str
    kind: FactKind
    formula: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    status: Literal["known", "unknown"] = "known"
    value_text: str | None = None  # for categorical facts, e.g. pump_risk "high"

    @property
    def display(self) -> str:
        """Plain, speakable form; this is what replaces a {fact_id} placeholder in model text."""
        if self.value_text is not None:
            return self.value_text
        if self.value is None:
            return "unknown"
        v = self.value
        if self.unit == "fraction":
            pct = v * 100
            return f"{round(pct)}%" if abs(pct) >= 100 else f"{_trim(round(pct, 1))}%"
        if self.unit == "INR":
            return speakable_inr(v)
        if self.unit in ("months", "years"):
            n = _trim(round(v, 1))
            return f"{n} {self.unit[:-1] if n == '1' else self.unit}"
        if self.unit == "times":
            return f"{_trim(round(v, 1))} times"
        if self.unit in ("count", "level"):
            return _trim(round(v, 1))
        return f"{_trim(round(v, 2))} {self.unit}".strip()


def _trim(x: float) -> str:
    return f"{x:,.2f}".rstrip("0").rstrip(".") if x % 1 else f"{int(x)}"


def speakable_inr(amount: float) -> str:
    """₹13.44 lakh / ₹2.5 crore for big amounts; whole rupees with Indian grouping below one lakh."""
    a = abs(amount)
    sign = "-" if amount < 0 else ""
    if a >= 1e7:
        return f"{sign}₹{_trim(round(a / 1e7, 2))} crore"
    if a >= 1e5:
        return f"{sign}₹{_trim(round(a / 1e5, 2))} lakh"
    return format_inr(round(amount))


def known(id: str, label: str, value: float, unit: str, kind: FactKind, formula: str, **inputs: Any) -> Fact:
    return Fact(id=id, label=label, value=value, unit=unit, kind=kind, formula=formula, inputs=_plain(inputs))


def unknown(id: str, label: str, unit: str, kind: FactKind, formula: str, missing: list[str], **inputs: Any) -> Fact:
    inputs = {**_plain(inputs), "missing": missing}
    return Fact(id=id, label=label, value=None, unit=unit, kind=kind, formula=formula, inputs=inputs, status="unknown")


def _plain(d: dict[str, Any]) -> dict[str, Any]:
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in d.items()}


def format_inr(amount: float) -> str:
    """Indian grouping: 1344400 -> '₹13,44,400'; 5166.67 -> '₹5,166.67'."""
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    whole, frac = f"{amount:.2f}".split(".")
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    body = ",".join(groups + [tail]) if groups else tail
    return f"{sign}₹{body}" + ("" if frac == "00" else f".{frac}")
