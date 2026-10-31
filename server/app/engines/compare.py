"""Comparison facts: code decides "higher" / "lower" / "about the same", so agents never judge direction themselves."""

from __future__ import annotations

from app.engines.fact import Fact

TOLERANCE_PP = 0.5  # within ±0.5 percentage points counts as "about the same"


def compare_rates(id: str, label: str, a: Fact, b: Fact, *, tolerance_pp: float = TOLERANCE_PP) -> Fact:
    """Compare two fraction facts (a vs b). value = difference in percentage points; value_text = the direction,
    which is what a {cmp_...} placeholder speaks."""
    formula = f"{a.id} - {b.id} in percentage points; within ±{tolerance_pp:g} = about the same"
    inputs = {a.id: a.value, b.id: b.value, "tolerance_pp": tolerance_pp}
    if a.value is None or b.value is None:
        return Fact(
            id=id,
            label=label,
            value=None,
            unit="percentage points",
            kind="offer",
            formula=formula,
            inputs=inputs | {"missing": [x.id for x in (a, b) if x.value is None]},
            status="unknown",
        )
    diff = (a.value - b.value) * 100
    word = "higher" if diff > tolerance_pp else "lower" if diff < -tolerance_pp else "about the same"
    return Fact(
        id=id,
        label=label,
        value=round(diff, 2),
        unit="percentage points",
        kind="offer",
        formula=formula,
        inputs=inputs,
        value_text=word,
    )
