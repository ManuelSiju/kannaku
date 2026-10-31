"""Code-owned question bank (questions.py) and Vick's signal rules (vick.py)."""

from __future__ import annotations

import itertools

import pytest

from app.engines.fact import Fact
from app.engines.tip_signals import tip_signals
from app.pipeline import questions as Q
from app.pipeline import vick
from app.pipeline.claims import ClaimCheck
from app.pipeline.council import check_round
from app.pipeline.explainer import fallback_turns
from app.pipeline.router import route
from app.pipeline.schemas import ExplainerOutput
from tests.fakes import FakeLLM, load_fixture
from tests.test_e2e_cases import TIP_Q, ask, harness  # noqa: F401  (fixture)

STOCK_BANNED = ("fundamental", "seller")


def claim(text, status="contradicted"):
    return ClaimCheck(claim=text, status=status)


def ids(qs):
    return [q.id for q in qs]


# ---------------------------------------------------------------- the bank


def test_insurance_bank_puts_claims_then_missing_terms_first():
    qs = Q.candidates("insurance_offer", ["maturity_low", "premium"], [claim("guaranteed 15 lakh")])
    assert ids(qs)[:3] == ["ins_guaranteed", "ins_lower_bonus", "show_premium"]
    assert qs[0].reason == "claim" and qs[1].reason == "missing:maturity_low"
    assert qs[2].text == "Can you show me the yearly premium in writing?"
    assert {"ins_stop_early", "ins_bonus_rate"} <= set(ids(qs))


def test_loan_bank_and_rate_claim():
    qs = Q.candidates("loan_offer", [], [claim("only 12 percent a year")])
    assert ids(qs) == ["loan_reducing_rate", "loan_charges"]
    assert qs[0].reason == "claim"


def test_chit_fund_bank_and_route():
    assert ids(Q.candidates("chit_fund", [], [])) == ["chit_registered", "chit_foreman_cut"]
    assert route("chit_fund") == ["sankz"]


def test_no_bank_no_questions():
    assert Q.candidates("sip_or_fund_question", ["monthly_amount"], []) == []
    assert Q.pick("sip_or_fund_question", [], [("x", "Anything?")], [], "full").questions == []


def test_bank_questions_are_short_and_stock_has_no_seller():
    for group, bank in Q.BANK.items():
        for b in bank:
            assert set(b.text) == {"en", "ml", "hi"}
            assert len(b.text["en"].split()) <= Q.MAX_WORDS
            assert all(k in b.text["en"].lower() for k in b.keys), b.id
            if group == "stock":
                assert b.audience != "seller"
                assert not any(w in b.text["en"].lower() for w in STOCK_BANNED)


def test_pick_keeps_good_rewording_and_rejects_meaning_changes():
    bank = Q.candidates("insurance_offer", [], [])
    p = Q.pick(
        "insurance_offer",
        bank,
        [
            ("ins_guaranteed", "Can you show me in writing what is guaranteed?"),
            ("ins_stop_early", "What do I get if I stop paying early?"),  # lost the "3"
            ("made_up", "Is this company good?"),
        ],
        [],
        "full",
    )
    assert [q.text for q in p.questions] == [
        "Can you show me in writing what is guaranteed?",
        "What do I get if I stop after 3 years?",
    ]
    assert p.reworded == [
        {
            "id": "ins_guaranteed",
            "from": "How much is guaranteed in writing?",
            "to": "Can you show me in writing what is guaranteed?",
        }
    ]
    assert {r["id"]: r["why"] for r in p.rejected} == {
        "ins_stop_early": "changed a number",
        "made_up": "not in the question bank",
    }


def test_pick_without_model_choice_uses_the_bank_order():
    bank = Q.candidates("insurance_offer", ["maturity_high"], [])
    p = Q.pick("insurance_offer", bank, [], [], "full")
    assert ids(p.questions) == ["ins_higher_bonus", "ins_guaranteed", "ins_lower_bonus"]


def test_triggered_questions_are_kept_and_come_first():
    bank = Q.candidates("loan_offer", ["flat_rate"], [])
    p = Q.pick("loan_offer", bank, [("loan_charges", "")], [], "full")
    assert ids(p.questions) == ["loan_reducing_rate", "loan_charges"]


def test_malayalam_questions_are_never_reworded():
    bank = Q.candidates("loan_offer", [], [], "ml")
    p = Q.pick("loan_offer", bank, [("loan_charges", "വേറെ ചാർജുകൾ ഉണ്ടോ?")], [], "full", "ml")
    assert p.questions[0].text == Q.BANK["loan"][1].text["ml"]


def test_discreet_mode_drops_the_afford_question():
    bank = Q.candidates("stock_tip", [], [])
    assert "stock_lose" in ids(Q.pick("stock_tip", bank, [], [], "full").questions)
    assert "stock_lose" not in ids(Q.pick("stock_tip", bank, [], [], "discreet").questions)


STOCK_PICKS = [
    ("stock_who", "Is the company's fundamentals strong?"),
    ("stock_why_rising", "Why is it rising this fast, seller?"),
    ("stock_who", "Ask the seller who sent this tip and if they own it?"),
    ("ins_guaranteed", "How much is guaranteed in writing?"),
    ("fundamentals", "Are the company fundamentals strong?"),
    ("stock_lose", "Can you afford to lose this money?"),
]


@pytest.mark.parametrize("case_type", ["stock_tip", "shares", "ipo"])
@pytest.mark.parametrize("unverified", [[], ["stock name"], ["price history", "invest_amount"]])
@pytest.mark.parametrize("mode", ["full", "discreet"])
def test_stock_questions_never_ask_about_fundamentals_or_the_seller(case_type, unverified, mode):
    claims = [claim("Upper circuit guaranteed", "cant_verify"), claim("target 180 in 2 weeks")]
    bank = Q.candidates(case_type, unverified, claims)
    for n in range(len(STOCK_PICKS) + 1):
        for picks in itertools.combinations(STOCK_PICKS, n):
            for q in Q.pick(case_type, bank, list(picks), [], mode).questions:
                assert not any(w in q.text.lower() for w in STOCK_BANNED), q.text
                assert q.audience in ("sender", "self")


def test_explainer_output_accepts_old_string_questions():
    out = ExplainerOutput.model_validate(
        {"verdict_sentence": {"speaker": "alfii", "text": "x"}, "questions": ["Free text?", {"id": "a", "text": "b"}]}
    )
    assert [(q.id, q.text) for q in out.questions] == [("", "Free text?"), ("a", "b")]


def test_stock_tip_end_to_end_questions(harness):  # noqa: F811
    client, state, _ = harness
    state["llm"] = FakeLLM(load_fixture("stock_tip"))
    res = ask(client, TIP_Q)
    qs = res["verdict"]["questions"]
    assert qs and qs[0] == "Who sent this tip, and does that person own the stock?"  # model's rewording kept
    assert not any(w in q.lower() for q in qs for w in STOCK_BANNED)
    bundle = client.get(f"/cases/{res['case_id']}").json()
    step = next(tr for tr in bundle["trace"] if tr["step"] == "questions")["detail"]
    assert step["bank"][0] == "stock_who" and step["reworded"][0]["id"] == "stock_who"


# ---------------------------------------------------------------- Vick


def _rows(prices, vols):
    import datetime as dt

    d0 = dt.date(2026, 6, 1)
    days = [d0 + dt.timedelta(days=i) for i in range(len(prices))]
    return [{"date": d, "close": c, "volume": v} for d, c, v in zip(days, prices, vols, strict=True)]


def pumped():
    prices = [100.0] * 70 + [100 * 1.02**i for i in range(1, 31)]
    vols = [1000.0] * 95 + [4000.0] * 5
    return tip_signals(_rows(prices, vols), symbol="ZEPHYRX")


def test_strongest_signal_is_relative_to_its_threshold():
    facts = pumped()
    sig = vick.known_signals(facts)
    run_up, spike = sig["run_up_30d"].value, sig["volume_spike"].value
    expected = "run_up_30d" if run_up / 0.5 > spike / 3.0 else "volume_spike"
    assert vick.strongest(facts) == expected
    assert vick.strongest([]) is None


def test_vick_argument_without_a_signal_is_dropped():
    from app.pipeline.schemas import CouncilOutput

    facts = pumped() + [Fact(id="ref.fd_rate", label="FD", value=0.07, unit="fraction", kind="offer", formula="x")]
    out = CouncilOutput.model_validate(
        {
            "opinions": [
                {
                    "agent": "vick",
                    "stance": "against",
                    "strength": 0.9,
                    "arguments": [
                        {"text": "A fixed deposit pays {ref.fd_rate} with no risk.", "cited_ids": []},
                        {"text": "It rose {run_up_30d} in a month.", "cited_ids": []},
                    ],
                }
            ]
        }
    )
    r = check_round(out, ["vick"], facts, {}, round=1)
    kept = [a.kept for a in r.arguments]
    assert kept == [False, True]
    assert r.arguments[0].drop_reason.startswith("Vick must cite a warning signal")


def test_vick_rule_needs_signals():
    assert vick.argument_problem([], []) is None
    assert vick.line_problem([], []) is None
    assert vick.template_line([], "en") is None


@pytest.mark.parametrize("lang", ["en", "ml", "hi"])
def test_vick_template_names_the_strongest_signal(lang):
    facts = pumped()
    spoken, screen, cited = vick.template_line(facts, lang)
    top = vick.strongest(facts)
    assert top in cited and "{" not in spoken and "{" not in screen
    by_id = {f.id: f for f in facts}
    assert by_id[top].display in screen and by_id[top].spoken(lang) in spoken
    if lang == "en":
        assert screen.endswith("That is how pump-and-dump schemes look.")
        assert "30 trading days" in screen


def test_vick_line_without_the_strongest_signal_falls_back_to_the_template():
    facts = pumped()
    top = vick.strongest(facts)
    other = "pump_risk"
    args = [{"agent": "vick", "text": f"This shows {{{other}}}.", "cited_ids": []}]
    lines, notes = fallback_turns(["vick"], args, facts, {}, "full")
    assert notes == [] and len(lines) == 1
    assert top in lines[0].cited_ids


def test_stock_tip_end_to_end_vick_names_the_strongest_signal(harness):  # noqa: F811
    client, state, _ = harness
    state["llm"] = FakeLLM(load_fixture("stock_tip"))
    res = ask(client, TIP_Q)
    details = {d["id"]: d["value"] for d in res["screen_details"]}
    # 222% / 50% beats 22 jumps / 5 and 4 times / 3
    assert (details["run_up_30d"], details["upper_circuit_hits_30d"], details["volume_spike"]) == (
        "222%",
        "22",
        "4 times",
    )
    vick_line = next(ln["text"] for ln in res["spoken_lines"] if ln["speaker"] == "vick")
    assert "222 percent" in vick_line


def test_vick_line_missing_the_strongest_signal_is_replaced(harness):  # noqa: F811
    client, state, _ = harness
    script = load_fixture("stock_tip")
    script["ExplainerOutput"]["agent_lines"][0]["text"] = "This share shows {pump_risk}."
    state["llm"] = llm = FakeLLM(script)
    res = ask(client, TIP_Q)
    vick_line = next(ln["text"] for ln in res["spoken_lines"] if ln["speaker"] == "vick")
    # his own argument fails the style linter, so code writes his line from the strongest signal
    assert (
        vick_line
        == "It rose 222 percent in 30 trading days on 4 times normal volume. That is how pump-and-dump schemes look."
    )
    assert "RewriteOutput" in llm.calls


def test_model_ask_sentences_leave_the_conclusion(harness):  # noqa: F811
    from tests.test_e2e_cases import LOAN_Q

    client, state, _ = harness
    script = load_fixture("flat_loan")
    script["ExplainerOutput"]["verdict_sentence"]["text"] = (
        "Please do not sign this loan. Ask them about the reducing-balance rate first."
    )
    state["llm"] = FakeLLM(script)
    res = ask(client, LOAN_Q)
    final = res["spoken_lines"][-1]["text"]
    assert final == "Please do not sign this loan."  # "do not sign" is itself the next step (ACTION_CUES)
