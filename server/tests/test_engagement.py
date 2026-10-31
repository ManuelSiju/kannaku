"""Accuracy and engagement rules: linter, claim checks, category phrases, word budget, templates, notes."""

import pytest

from app.engines.compare import compare_rates
from app.engines.fact import Fact
from app.engines.finance import affordability
from app.engines.tip_signals import tip_signals
from app.pipeline.claims import check_claims, mentioned
from app.pipeline.evidence import render
from app.pipeline.explainer import CheckedLine
from app.pipeline.lint import lint
from app.pipeline.run import COUNCIL_WORD_BUDGET, _fit_budget, _short
from app.pipeline.schemas import SellerClaim
from app.pipeline.templates import followups, opener


# ---------------------------------------------------------------- B1 linter
@pytest.mark.parametrize(
    "line,rule",
    [
        ("One. Two. Three.", "too_many_sentences"),
        (
            "This is a very long sentence that goes on and on with far too many words for anyone to follow at all.",
            "sentence_too_long",
        ),
        ("It grows 3.8 percent while an FD gives 7 percent.", "too_many_numbers"),
        ("The IRR of this plan is poor.", "jargon"),
        ("The illustrated amount is not promised.", "jargon"),
        ("The stock has a high high risk.", "repeated_word"),
        ("This is risky.", "vague"),
        ("Not worth it.", "vague"),
    ],
)
def test_linter_rules(line, rule):
    assert rule in lint(line)


@pytest.mark.parametrize(
    "line",
    [
        "This plan grows only about 3.8 percent a year, lower than a fixed deposit.",
        "Nobody can promise a share will rise, so this is risky.",
        "Only 7.5 lakh rupees is guaranteed. The rest depends on bonuses.",
    ],
)
def test_linter_accepts_good_lines(line):
    assert lint(line) == []


# ---------------------------------------------------------------- A2 phrases
def test_categorical_facts_never_render_as_a_bare_word():
    rows = [{"date": f"2026-01-{d:02d}", "close": 10 * 1.05**d, "volume": 1000} for d in range(1, 32)]
    risk = next(f for f in tip_signals(rows) if f.id == "pump_risk")
    fd = Fact(id="ref.fd_rate", label="", value=0.07, unit="fraction", kind="offer", formula="")
    cmp = compare_rates("cmp_x", "", Fact(id="a", label="", value=0.03, unit="fraction", kind="offer", formula=""), fd)
    for f in (risk, cmp):
        assert f.display not in ("high", "medium", "low", "higher", "lower", "about the same")
    text = render("The stock has {pump_risk}. It grows {cmp_x} a fixed deposit.", [risk, cmp])
    assert "high high" not in text and "than than" not in text
    assert lint(text, "{pump_risk} {cmp_x}") == []


# ---------------------------------------------------------------- A3 premium is not an EMI
def test_premium_is_a_commitment_not_an_emi(demo_repo):
    from app.pipeline.compute import compute_facts
    from app.pipeline.verify_terms import VerifiedTerm

    def term(name, v, unit="INR"):
        return VerifiedTerm(
            name=name, value_text=str(v), value=v, unit=unit, quote_id="q1", source="page_1", verified=True
        )

    c = compute_facts(
        "insurance_offer",
        [term("premium", 50_000), term("pay_years", 15, "years"), term("maturity_low", 10_20_000)],
        1,
        demo_repo,
    )
    f = {x.id: x for x in c.facts}
    assert f["emi_share"].value == pytest.approx(2_400 / 45_000, abs=1e-4)  # existing scooter loan only
    assert f["premium_share_of_income"].value == pytest.approx((50_000 / 12) / 45_000, abs=1e-4)
    assert f["surplus_after"].value == pytest.approx(45_000 - 28_000 - 2_400 - 1_000 - 50_000 / 12, abs=0.01)
    # A5: one illustration amount missing -> asked for, and treated as a missing term
    assert "maturity_high" in c.missing_required
    assert c.questions == ["What do I get at the higher bonus rate?"]


# ---------------------------------------------------------------- A4 claim checks
def _f(id, v, unit="INR"):
    return Fact(id=id, label=id, value=v, unit=unit, kind="offer", formula="")


FACTS = [
    _f("term.sum_assured", 750_000),
    _f("term.maturity_high", 1_500_000),
    _f("endowment_return", 0.0375, "fraction"),
    _f("f_return_high", 0.083, "fraction"),
]
QUOTES = {
    "q3": {"source": "page_3", "text": "Important terms. Bonus rates are not guaranteed and may change every year."}
}


def test_guarantee_claim_contradicted_by_document():
    (c,) = check_claims([SellerClaim(text="guaranteed to give 15 lakh")], FACTS, QUOTES, "insurance_offer")
    assert c.status == "contradicted" and c.evidence_ids == ["q3", "term.maturity_high"]
    assert c.evidence == "Bonus rates are not guaranteed and may change every year"


def test_guarantee_of_the_sum_assured_is_supported():
    (c,) = check_claims([SellerClaim(text="7.5 lakh is guaranteed")], FACTS, QUOTES, "insurance_offer")
    assert c.status == "supported"


def test_return_claim_above_best_case_is_contradicted():
    (c,) = check_claims([SellerClaim(text="you will get 12% every year")], FACTS, QUOTES, "insurance_offer")
    assert c.status == "contradicted" and c.evidence_ids == ["f_return_high"]


def test_stock_guarantee_cannot_be_verified():
    (c,) = check_claims([SellerClaim(text="Upper circuit guaranteed")], [], {}, "stock_tip")
    assert c.status == "cant_verify" and "share price" in c.reason


def test_mentioned():
    (c,) = check_claims([SellerClaim(text="guaranteed to give 15 lakh")], FACTS, QUOTES, "insurance_offer")
    assert mentioned(c, ["The 15 lakh is not guaranteed."])
    assert not mentioned(c, ["This plan grows slowly."])


# ---------------------------------------------------------------- B5 word budget, short answer
def L(kind, words, speaker="dani"):
    return CheckedLine(speaker=speaker, text=" ".join(["word"] * words) + ". More words here.", kind=kind)


def test_word_budget_drops_rebuttals_first_then_trims_agents():
    lines = [
        L("opener", 5, "alfii"),
        L("agent", 40),
        L("agent", 40, "sankz"),
        L("rebuttal", 30),
        L("conclusion", 15, "alfii"),
    ]
    out = _fit_budget(lines)
    assert all(x.kind != "rebuttal" for x in out)
    assert sum(len(x.text.split()) for x in out) <= COUNCIL_WORD_BUDGET
    assert [x.kind for x in out] == ["opener", "agent", "agent", "conclusion"]


def test_short_answer():
    assert _short("Check the bonus rate first. Ask them.", "yellow", "en") == "Check the bonus rate first."
    assert _short(" ".join(["long"] * 25) + ".", "yellow", "en") == "Be careful; get clear answers before you decide."


# ---------------------------------------------------------------- templates
def test_openers_and_followups():
    assert opener(["dani", "sankz"]) == "Let me ask Dani and Sankz."
    assert opener(["vick", "sankz", "dani"]) == "Let me ask Vick, Sankz and Dani."
    assert opener(["sankz"], "hi") == "चलिए, सैंक्स से पूछते हैं।"
    for case in ("insurance_offer", "loan_offer", "stock_tip", "out_of_scope"):
        assert 1 <= len(followups(case)) <= 3
        assert all(len(q.split()) <= 8 for q in followups(case))


def test_affordability_signature_still_needs_commitments():
    with pytest.raises(TypeError):
        affordability(1, 1, 1, 1, 1)  # regular_commitments is keyword-only and required


def test_double_comparison_is_rejected():
    assert "double_comparison" in lint("This loan costs you more higher than the quoted rate.")
    assert lint("This loan costs even higher than a bank loan.") == []


def test_bonus_rate_terms_are_percentages():
    from app.pipeline.verify_terms import term_unit

    assert term_unit("bonus_rate_low") == term_unit("flat_rate") == "fraction"


def test_auto_placeholder_variants_and_identical_values():
    from app.pipeline.evidence import check_argument

    facts = [
        Fact(id="term.sum_assured", label="", value=750_000, unit="INR", kind="offer", formula=""),
        Fact(id="term.maturity_high", label="", value=1_500_000, unit="INR", kind="offer", formula=""),
        Fact(id="term.pay_years", label="", value=15, unit="years", kind="offer", formula=""),
        Fact(id="term.policy_years", label="", value=15, unit="years", kind="offer", formula=""),
    ]
    r = check_argument("Only ₹7,50,000 is guaranteed, not 15 lakh, after 15 years.", [], facts, {})
    assert r.kept, r
    assert r.cited == ["term.sum_assured", "term.maturity_high", "term.pay_years"]


def test_dangling_than_is_rejected():
    assert "dangling_than" in lint("It costs 21.6 percent, higher than and higher than other loans.")


def test_red_short_answer_is_never_conditional():
    assert _short("Do not invest without clear facts.", "red", "en") == "Please don't go ahead with this as it is."


def test_red_conclusion_with_a_loophole_is_replaced(harness_red_conclusion):
    lines = harness_red_conclusion
    assert lines[-1].startswith("My advice: do not go ahead with this as it is.")
    assert "without" not in lines[-1].split(".")[0]
