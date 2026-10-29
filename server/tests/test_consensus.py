import pytest

from app.engines.finance import affordability
from app.pipeline.consensus import (
    OverrideInputs,
    Position,
    override_inputs_from_facts,
    run_consensus,
    weights_for,
)


def P(agent, stance, strength=1.0):
    return Position(agent=agent, stance=stance, strength=strength)


def test_unanimous_against_is_red():
    r = run_consensus("insurance_offer", [P("dani", "against", 0.9), P("sankz", "against", 0.8)])
    assert r.verdict == "red" and r.score == pytest.approx(-0.85)
    assert r.disagreement == 0 and not r.debate_needed


def test_unanimous_for_is_green():
    assert run_consensus("insurance_offer", [P("dani", "for"), P("sankz", "for", 0.6)]).verdict == "green"


def test_split_is_yellow_and_needs_debate():
    r = run_consensus("insurance_offer", [P("dani", "for", 0.8), P("sankz", "against", 0.8)])
    assert r.verdict == "yellow" and r.score == pytest.approx(0.0)
    assert r.disagreement == pytest.approx(1.0) and r.debate_needed


def test_all_unsure_is_yellow():
    r = run_consensus("general", [P("sankz", "unsure", 0.5), P("dani", "unsure", 0.0)])
    assert r.verdict == "yellow" and r.score == 0 and r.disagreement == 0


def test_single_voter_has_no_disagreement():
    r = run_consensus("loan_offer", [P("sankz", "against", 0.5)])
    assert r.disagreement == 0 and r.verdict == "red"


def test_weights_renormalised_over_called_agents():
    assert weights_for("insurance_offer", ["dani", "sankz"]) == {"dani": 0.5, "sankz": 0.5}
    w = weights_for("stock_tip", ["vick", "sankz"])
    assert w["vick"] == pytest.approx(0.6)
    assert sum(weights_for("ulip", ["dani", "sankz", "vick"]).values()) == pytest.approx(1.0)


def test_weighted_score():
    # stock tip: vick 0.6 against strength 1, sankz 0.4 for strength 0.5 -> (-0.6 + 0.2) / 1.0 = -0.4
    r = run_consensus("stock_tip", [P("vick", "against"), P("sankz", "for", 0.5)])
    assert r.score == pytest.approx(-0.4) and r.verdict == "red"


GREEN = [P("dani", "for"), P("sankz", "for")]


@pytest.mark.parametrize(
    "inputs,verdict,rule",
    [
        (OverrideInputs(scam=True), "red", "scam_signal"),
        (OverrideInputs(buffer_months_after=0.5), "red", "buffer_under_1_month"),
        (OverrideInputs(buffer_months_after=2.0), "yellow", "buffer_under_3_months"),
        (OverrideInputs(emi_share=0.65), "red", "emi_share_over_60"),
        (OverrideInputs(emi_share=0.45), "yellow", "emi_share_over_40"),
        (OverrideInputs(surplus_after=-500), "red", "negative_surplus"),
        (OverrideInputs(guaranteed_claim_unbacked=True), "yellow", "unbacked_guarantee"),
        (OverrideInputs(unverified_required_terms=["premium"]), "yellow", "unverified_terms"),
    ],
)
def test_each_override(inputs, verdict, rule):
    r = run_consensus("insurance_offer", GREEN, inputs)
    assert r.vote_verdict == "green"
    assert r.verdict == verdict
    assert rule in [o.rule for o in r.overrides]


def test_caps_do_not_make_red_better():
    r = run_consensus(
        "insurance_offer", [P("dani", "against"), P("sankz", "against")], OverrideInputs(buffer_months_after=2.0)
    )
    assert r.verdict == "red"


def test_no_overrides_when_values_fine_or_unknown():
    r = run_consensus(
        "insurance_offer", GREEN, OverrideInputs(buffer_months_after=6, emi_share=0.1, surplus_after=5000)
    )
    assert r.verdict == "green" and r.overrides == []
    assert run_consensus("insurance_offer", GREEN, OverrideInputs()).overrides == []


def test_override_inputs_from_facts():
    facts = affordability(45_000, 28_000, 10_000, 2_400, 4_167, prefix="new")
    o = override_inputs_from_facts(facts, scam=False)
    assert o.buffer_months_after == pytest.approx(10_000 / (28_000 + 2_400 + 4_167), abs=0.01)
    assert run_consensus("insurance_offer", GREEN, o).verdict == "red"  # < 1 month buffer
    missing = override_inputs_from_facts(affordability(45_000, None, None, 0, 4_167))
    assert missing.buffer_months_after is None and missing.surplus_after is None
