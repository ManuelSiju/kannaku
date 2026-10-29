"""Pump-and-dump signals for a stock tip, from daily price/volume rows. Deterministic; never says "buy".

Returns Facts (kind "offer"): run_up_30d, volume_spike, upper_circuit_hits_30d, max_drawdown_90d, pump_risk.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel

from app.engines.fact import Fact, known, unknown

# ---- thresholds (documented; tune here only) ----
UPPER_CIRCUIT_PCT = 4.9  # a day's close up >= this % from previous close counts as an upper-circuit hit
RUN_UP_HIGH = 0.50  # 30-day price rise
RUN_UP_MEDIUM = 0.25
VOLUME_SPIKE_HIGH = 3.0  # last-5-day avg volume / previous-60-day avg volume
VOLUME_SPIKE_MEDIUM = 2.0
CIRCUIT_HITS_HIGH = 5
CIRCUIT_HITS_MEDIUM = 2
# pump_risk:
#   high   if (run_up >= RUN_UP_HIGH and volume_spike >= VOLUME_SPIKE_HIGH) or circuit_hits >= CIRCUIT_HITS_HIGH
#   medium if run_up >= RUN_UP_MEDIUM or volume_spike >= VOLUME_SPIKE_MEDIUM or circuit_hits >= CIRCUIT_HITS_MEDIUM
#   low    otherwise; "unknown" if no signal could be computed
PUMP_LEVELS = {"low": 0, "medium": 1, "high": 2}


class PriceRow(BaseModel):
    date: dt.date
    close: float
    volume: float


def _rows(rows: Iterable[PriceRow | Mapping[str, Any]]) -> list[PriceRow]:
    parsed = [r if isinstance(r, PriceRow) else PriceRow.model_validate(r) for r in rows]
    return sorted(parsed, key=lambda r: r.date)


def tip_signals(
    rows: Iterable[PriceRow | Mapping[str, Any]], *, symbol: str = "", circuit_pct: float = UPPER_CIRCUIT_PCT
) -> list[Fact]:
    """Rows are trading days (date, close, volume), any order. Windows count trading days."""
    data = _rows(rows)
    closes = [r.close for r in data]
    vols = [r.volume for r in data]
    who = f" of {symbol}" if symbol else ""
    facts: list[Fact] = []

    label = f"Price rise{who} over the last 30 trading days"
    formula = "close[-1] / close[-31] - 1"
    if len(closes) >= 31 and closes[-31] > 0:
        run_up = closes[-1] / closes[-31] - 1
        facts.append(
            known(
                "run_up_30d",
                label,
                round(run_up, 4),
                "fraction",
                "offer",
                formula,
                symbol=symbol,
                close_then=closes[-31],
                close_now=closes[-1],
            )
        )
    else:
        run_up = None
        facts.append(unknown("run_up_30d", label, "fraction", "offer", formula, ["31 days of prices"], symbol=symbol))

    label = f"Trading volume{who} in the last 5 days compared with the 60 days before (times)"
    formula = "mean(volume[-5:]) / mean(volume[-65:-5])"
    base = vols[-65:-5]
    if len(vols) >= 65 and sum(base) > 0:
        spike = (sum(vols[-5:]) / 5) / (sum(base) / len(base))
        facts.append(known("volume_spike", label, round(spike, 2), "times", "offer", formula, symbol=symbol))
    else:
        spike = None
        facts.append(unknown("volume_spike", label, "times", "offer", formula, ["65 days of volume"], symbol=symbol))

    label = f"Days{who} in the last 30 trading days the price jumped {circuit_pct}% or more"
    formula = f"count(close[d] / close[d-1] - 1 >= {circuit_pct}%) over last 30 days"
    if len(closes) >= 31:
        window = closes[-31:]
        hits = sum(1 for a, b in zip(window, window[1:], strict=False) if a > 0 and (b / a - 1) * 100 >= circuit_pct)
        facts.append(
            known(
                "upper_circuit_hits_30d", label, hits, "count", "offer", formula, symbol=symbol, circuit_pct=circuit_pct
            )
        )
    else:
        hits = None
        facts.append(unknown("upper_circuit_hits_30d", label, "count", "offer", formula, ["31 days"], symbol=symbol))

    label = f"Biggest fall{who} from a high in the last 90 trading days"
    formula = "max over days of (1 - close / running peak) within last 90 days"
    window = closes[-90:]
    if len(window) >= 2:
        peak, worst = window[0], 0.0
        for c in window:
            peak = max(peak, c)
            if peak > 0:
                worst = max(worst, 1 - c / peak)
        facts.append(known("max_drawdown_90d", label, round(worst, 4), "fraction", "offer", formula, symbol=symbol))
    else:
        facts.append(unknown("max_drawdown_90d", label, "fraction", "offer", formula, ["2 days"], symbol=symbol))

    level = pump_level(run_up, spike, hits)
    label = f"Pump-and-dump warning level{who}"
    formula = "thresholds in engines/tip_signals.py"
    if level is None:
        facts.append(unknown("pump_risk", label, "level", "offer", formula, ["signals"], symbol=symbol))
    else:
        facts.append(
            known(
                "pump_risk",
                label,
                PUMP_LEVELS[level],
                "level",
                "offer",
                formula,
                symbol=symbol,
                run_up_30d=run_up,
                volume_spike=spike,
                upper_circuit_hits_30d=hits,
            )
        )
        facts[-1].value_text = level
    return facts


def pump_level(run_up: float | None, spike: float | None, hits: int | None) -> str | None:
    if run_up is None and spike is None and hits is None:
        return None
    r, s, h = run_up or 0.0, spike or 0.0, hits or 0
    if (r >= RUN_UP_HIGH and s >= VOLUME_SPIKE_HIGH) or h >= CIRCUIT_HITS_HIGH:
        return "high"
    if r >= RUN_UP_MEDIUM or s >= VOLUME_SPIKE_MEDIUM or h >= CIRCUIT_HITS_MEDIUM:
        return "medium"
    return "low"
