"""Exact threshold values land on the documented side (app/pipeline/consensus.py)."""

import pytest

from app.pipeline import consensus
from app.pipeline.consensus import OverrideInputs, Position, overrides_for, run_consensus, verdict_from_score
from tests.calibration import oracle


@pytest.mark.parametrize(("score", "colour"), [(0.2, "yellow"), (-0.2, "yellow"), (0.2001, "green"), (-0.2001, "red")])
def test_score_boundaries(score, colour):
    assert verdict_from_score(score) == colour


def rules(**kw) -> list[str]:
    return [o.rule for o in overrides_for(OverrideInputs(**kw))]


@pytest.mark.parametrize(
    ("share", "expected"),
    [(0.40, []), (0.4001, ["emi_share_over_40"]), (0.60, ["emi_share_over_40"]), (0.6001, ["emi_share_over_60"])],
)
def test_emi_share_boundaries(share, expected):
    assert rules(emi_share=share) == expected


@pytest.mark.parametrize(
    ("months", "expected"),
    [(3, []), (2.99, ["buffer_under_3_months"]), (1, ["buffer_under_3_months"]), (0.99, ["buffer_under_1_month"])],
)
def test_buffer_boundaries(months, expected):
    assert rules(buffer_months_after=months) == expected


@pytest.mark.parametrize(("disagreement", "debate"), [(0.4, False), (0.4001, True)])
def test_disagreement_boundary(monkeypatch, disagreement, debate):
    monkeypatch.setattr(consensus, "vote", lambda *_: (0.0, disagreement))
    positions = [
        Position(agent="sankz", stance="for", strength=1),
        Position(agent="dani", stance="against", strength=1),
    ]
    assert run_consensus("general_money", positions).debate_needed is debate


def test_oracle_agrees_with_the_published_demo_numbers():
    assert oracle.flat_loan(100_000, 0.12, 24)["loan_emi"] == pytest.approx(5166.67, abs=0.01)
    assert oracle.flat_loan(100_000, 0.12, 24)["loan_effective_rate"] == pytest.approx(0.216, abs=0.001)
    assert oracle.endowment_rate(50_000, 15, 1_020_000, 15) == pytest.approx(0.038, abs=0.001)
