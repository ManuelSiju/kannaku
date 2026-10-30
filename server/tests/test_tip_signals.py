import datetime as dt
import random

import pytest

from app.engines.tip_signals import PriceRow, pump_level, tip_signals

START = dt.date(2026, 5, 1)


def series(closes, volumes):
    return [
        {"date": START + dt.timedelta(days=i), "close": c, "volume": v}
        for i, (c, v) in enumerate(zip(closes, volumes, strict=True))
    ]


def by_id(facts):
    return {f.id: f for f in facts}


def pump_pattern():
    # 70 quiet days around 20, then 30 days of 5% jumps on huge volume, last 5 days extreme volume.
    rng = random.Random(1)
    closes = [20 + rng.uniform(-0.3, 0.3) for _ in range(70)]
    vols = [10_000 + rng.uniform(-500, 500) for _ in range(70)]
    for i in range(30):
        closes.append(closes[-1] * (1.05 if i % 3 else 1.01))
        vols.append(60_000 if i >= 25 else 25_000)
    return series(closes, vols)


def quiet_pattern():
    rng = random.Random(2)
    closes, vols = [100.0], [50_000.0]
    for _ in range(119):
        closes.append(closes[-1] * (1 + rng.uniform(-0.01, 0.011)))
        vols.append(50_000 + rng.uniform(-5_000, 5_000))
    return series(closes, vols)


def test_pump_pattern_is_high_risk():
    f = by_id(tip_signals(pump_pattern(), symbol="ZEPHYRX"))
    assert f["run_up_30d"].value > 0.5
    assert f["volume_spike"].value >= 3
    assert f["upper_circuit_hits_30d"].value >= 5
    assert f["pump_risk"].value_text == "high" and f["pump_risk"].value == 2
    assert all(x.kind == "offer" for x in f.values())
    assert "ZEPHYRX" in f["run_up_30d"].label


def test_quiet_pattern_is_low_risk():
    f = by_id(tip_signals(quiet_pattern()))
    assert abs(f["run_up_30d"].value) < 0.25
    assert f["volume_spike"].value < 2
    assert f["upper_circuit_hits_30d"].value == 0
    assert f["pump_risk"].value_text == "low"


def test_drawdown():
    closes = [100] * 10 + [150, 120, 90, 130]
    f = by_id(tip_signals(series(closes, [1] * len(closes))))
    assert f["max_drawdown_90d"].value == pytest.approx(0.4)


def test_short_history_is_unknown_not_zero():
    f = by_id(tip_signals(series([10, 11, 12], [1, 1, 1])))
    assert f["run_up_30d"].status == "unknown"
    assert f["volume_spike"].value is None
    assert f["pump_risk"].status == "unknown"


def test_rows_may_be_unsorted_models():
    rows = [PriceRow(**r) for r in reversed(pump_pattern())]
    assert by_id(tip_signals(rows))["pump_risk"].value_text == "high"


def test_circuit_threshold_configurable():
    closes = [100 * 1.03**i for i in range(40)]
    assert by_id(tip_signals(series(closes, [1] * 40)))["upper_circuit_hits_30d"].value == 0
    assert by_id(tip_signals(series(closes, [1] * 40), circuit_pct=2.9))["upper_circuit_hits_30d"].value == 30


@pytest.mark.parametrize(
    "run_up,spike,hits,level",
    [
        (0.6, 3.5, 0, "high"),
        (0.1, 1.0, 5, "high"),
        (0.3, 1.0, 0, "medium"),
        (0.0, 2.1, 0, "medium"),
        (0.0, 1.0, 2, "medium"),
        (0.1, 1.2, 1, "low"),
        (None, None, None, None),
    ],
)
def test_pump_level_thresholds(run_up, spike, hits, level):
    assert pump_level(run_up, spike, hits) == level


def test_run_up_and_circuit_hits_share_one_trading_day_window():
    f = by_id(tip_signals(pump_pattern()))
    ru, ch = f["run_up_30d"].inputs, f["upper_circuit_hits_30d"].inputs
    assert ru["window_trading_days"] == ch["window_trading_days"] == 30
    assert (ru["window_from"], ru["window_to"]) == (ch["window_from"], ch["window_to"])
    assert "trading days" in f["run_up_30d"].label and "trading days" in f["upper_circuit_hits_30d"].label
    assert "trading days" in f["volume_spike"].label and "trading days" in f["max_drawdown_90d"].label
