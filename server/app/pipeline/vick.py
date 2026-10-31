"""Vick's rules (stock cases): every argument cites a pump-and-dump signal, and his spoken line names the strongest
signal by its value. If neither his line nor his own argument does, code writes the line from the facts.

The rules apply only when the case has at least one known signal (a ULIP or a stock with no price history has none).
"""

from __future__ import annotations

from collections.abc import Iterable

from app.engines.fact import Fact
from app.engines.tip_signals import CIRCUIT_HITS_HIGH, RUN_UP_HIGH, RUN_WINDOW, VOLUME_SPIKE_HIGH
from app.pipeline.evidence import render
from app.pipeline.templates import t

SIGNALS = ("run_up_30d", "volume_spike", "upper_circuit_hits_30d", "pump_risk")
# a signal's size relative to its "high" threshold decides which one is the strongest (thresholds are not changed)
_SCALE = {"run_up_30d": RUN_UP_HIGH, "volume_spike": VOLUME_SPIKE_HIGH, "upper_circuit_hits_30d": CIRCUIT_HITS_HIGH}


def known_signals(facts: Iterable[Fact]) -> dict[str, Fact]:
    return {f.id: f for f in facts if f.id in SIGNALS and f.status == "known" and f.value is not None}


def argument_problem(cited: Iterable[str], facts: Iterable[Fact]) -> str | None:
    sig = known_signals(facts)
    if sig and not set(cited) & set(sig):
        return "Vick must cite a warning signal: " + ", ".join(sig)
    return None


def strongest(facts: Iterable[Fact]) -> str | None:
    sig = known_signals(facts)
    sized = {k: (sig[k].value or 0) / scale for k, scale in _SCALE.items() if k in sig and (sig[k].value or 0) > 0}
    if sized:
        return max(sized, key=lambda k: sized[k])
    return "pump_risk" if "pump_risk" in sig else None


def line_problem(cited: Iterable[str], facts: Iterable[Fact]) -> str | None:
    top = strongest(facts)
    if top and top not in set(cited):
        return f"Vick must name the strongest signal {{{top}}} by its value"
    return None


def template_line(facts: list[Fact], lang: str = "en") -> tuple[str, str, list[str]] | None:
    """(spoken, screen, cited) written by code from the strongest signal, or None without signals."""
    top = strongest(facts)
    if top is None:
        return None
    sig = known_signals(facts)
    key = {
        "run_up_30d": "vick_run_up_volume" if "volume_spike" in sig else "vick_run_up",
        "volume_spike": "vick_volume_run_up" if (sig.get("run_up_30d") and (sig["run_up_30d"].value or 0) > 0)
        else "vick_volume",
        "upper_circuit_hits_30d": "vick_circuit",
        "pump_risk": "vick_pump",
    }[top]  # fmt: skip
    risky = "pump_risk" in sig and (sig["pump_risk"].value or 0) >= 1  # medium or high
    text = t(lang, key, days=str(RUN_WINDOW), **{s: "{" + s + "}" for s in SIGNALS})
    text = f"{text} {t(lang, 'vick_tail_pump' if risky else 'vick_tail')}"
    cited = [s for s in SIGNALS if "{" + s + "}" in text]
    return render(text, facts, lang), render(text, facts), cited
