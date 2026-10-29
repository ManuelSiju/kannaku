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
        if self.value_text is not None:
            return self.value_text
        if self.value is None:
            return "unknown"
        if self.unit == "fraction":
            return f"{self.value * 100:.1f}%"
        if self.unit == "INR":
            return format_inr(self.value)
        if self.unit in ("months", "years"):
            return f"{self.value:.1f} {self.unit}"
        return f"{self.value:g} {self.unit}".strip()


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
