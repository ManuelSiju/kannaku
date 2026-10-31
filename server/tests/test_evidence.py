from app.engines.finance import affordability, endowment_return, fd_value
from app.pipeline.evidence import Dropped, Kept, check_argument, placeholders, raw_number, render

FACTS = [
    endowment_return(50_000, 15, 10_20_000, 15),  # 3.8%
    fd_value(50_000, 15, 0.07),  # ₹13.44 lakh
    *affordability(45_000, 28_000, 1_60_000, 2_400, 50_000 / 12, regular_commitments=1_000),
]
QUOTES = {"q1": "Bonus rates are not guaranteed and may change every year.",
          "q2": "Illustrated maturity value at 8% bonus: Rs. 15,00,000"}  # fmt: skip


def test_placeholder_is_rendered_and_counts_as_citation():
    r = check_argument("This plan grows your money by only about {endowment_return} a year.", [], FACTS, QUOTES)
    assert isinstance(r, Kept)
    assert r.rendered == "This plan grows your money by only about 3.8% a year."
    assert r.cited == ["endowment_return"]


def test_two_placeholders_and_a_quote():
    text = "It returns {endowment_return}; an FD would give {fd_value}, and the bonus is not guaranteed."
    r = check_argument(text, ["q1"], FACTS, QUOTES)
    assert r.kept and r.rendered.endswith("an FD would give ₹13.44 lakh, and the bonus is not guaranteed.")
    assert r.cited == ["q1", "endowment_return", "fd_value"]


def test_raw_number_equal_to_one_fact_display_becomes_placeholder():
    r = check_argument("This plan returns about 3.8% a year.", [], FACTS, QUOTES)
    assert isinstance(r, Kept) and r.rendered == "This plan returns about 3.8% a year."
    assert r.cited == ["endowment_return"]
    assert r.fixes == ["auto_placeholder '3.8%' -> {endowment_return}"]


def test_raw_number_not_matching_a_display_is_dropped():
    r = check_argument("This plan returns about 3.75% a year.", ["endowment_return"], FACTS, QUOTES)
    assert isinstance(r, Dropped) and "raw number" in r.reason


def test_invented_number_dropped():
    assert not check_argument("An FD would give you 8% a year.", ["fd_value"], FACTS, QUOTES).kept


def test_digit_inside_words_dropped():
    assert not check_argument("Over the last 30 trading days it rose {endowment_return}.", [], FACTS, QUOTES).kept


def test_unknown_placeholder_dropped():
    r = check_argument("It returns {made_up_rate} a year.", [], FACTS, QUOTES)
    assert isinstance(r, Dropped) and "made_up_rate" in r.reason


def test_unknown_citation_dropped():
    r = check_argument("Bonus is not guaranteed.", ["q9"], FACTS, QUOTES)
    assert isinstance(r, Dropped) and "q9" in r.reason


def test_no_citation_dropped():
    assert not check_argument("This is a bad plan.", [], FACTS, QUOTES).kept


def test_quote_backs_a_claim_without_numbers():
    assert check_argument("The bonus is not guaranteed.", ["q1"], FACTS, QUOTES).kept


def test_kind_filter():
    text = "You would have {surplus_after} left each month."
    assert check_argument(text, [], FACTS, QUOTES).kept
    r = check_argument(text, [], FACTS, QUOTES, kind_filter="offer")
    assert isinstance(r, Dropped) and "surplus_after" in r.reason


def test_helpers():
    assert placeholders("{a} and {b.c} and {a}") == ["a", "b.c"]
    assert render("{fd_value} vs {nope}", FACTS) == "₹13.44 lakh vs {nope}"
    assert "15 years" in raw_number("about {fd_value} in 15 years")
    assert raw_number("no digits {fd_value}") is None


def test_unambiguous_short_placeholder_is_resolved():
    from app.engines.fact import Fact

    facts = [*FACTS, Fact(id="term.sum_assured", label="", value=750_000, unit="INR", kind="offer", formula="")]
    r = check_argument("Only {sum_assured} is guaranteed.", [], facts, QUOTES)
    assert r.kept and r.rendered == "Only ₹7.5 lakh is guaranteed." and r.cited == ["term.sum_assured"]


def test_ambiguous_short_placeholder_is_rejected():
    from app.engines.fact import Fact

    facts = [Fact(id=f"{p}.x", label="", value=1, unit="INR", kind="offer", formula="") for p in ("a", "b")]
    assert not check_argument("It is {x}.", [], facts, QUOTES).kept


def test_small_amount_does_not_match_by_lakh_rounding():
    from app.pipeline.evidence import TextNumber, value_matches

    assert not value_matches(TextNumber(value=50_000, is_percent=False, text="50,000"), 45_000, "INR")
    assert value_matches(TextNumber(value=13_40_000, is_percent=False, text="13.4 lakh"), 13_44_402.68, "INR")


# ---------------------------------------------------------------- comparison facts
from app.engines.compare import compare_rates  # noqa: E402
from app.engines.fact import Fact  # noqa: E402


def _rate(id, v):
    return Fact(id=id, label="", value=v, unit="fraction", kind="offer", formula="")


FD = _rate("ref.fd_rate", 0.07)
LOW, HIGH, GUAR = _rate("endowment_return", 0.0375), _rate("f_return_high", 0.083), _rate("f_return_guaranteed", 0.0)
CMP = [
    compare_rates("cmp_return_low_vs_fd", "", LOW, FD),
    compare_rates("cmp_return_high_vs_fd", "", HIGH, FD),
    compare_rates("cmp_guaranteed_vs_fd", "", GUAR, FD),
]
CFACTS = [FD, LOW, HIGH, GUAR, *CMP]


def test_compare_rates_directions_and_tolerance():
    assert [c.value_text for c in CMP] == ["lower", "higher", "lower"]
    assert compare_rates("c", "", _rate("a", 0.074), FD).value_text == "about the same"  # +0.4 pp
    assert compare_rates("c", "", _rate("a", 0.076), FD).value_text == "higher"  # +0.6 pp
    assert compare_rates("c", "", _rate("a", None), FD).status == "unknown"


def test_false_comparison_line_dropped():
    text = "Even with the highest bonus rate, your maturity value would be lower"
    assert not check_argument(text, ["q1"], CFACTS, QUOTES).kept
    r = check_argument(text, ["cmp_return_high_vs_fd"], CFACTS, QUOTES)
    assert isinstance(r, Dropped) and "lower" in r.reason


def test_comparison_backed_by_agreeing_cmp_fact_kept():
    assert check_argument("This plan earns less than a fixed deposit.", ["cmp_return_low_vs_fd"], CFACTS, QUOTES).kept
    r = check_argument("At the higher bonus it would be {cmp_return_high_vs_fd} a fixed deposit.", [], CFACTS, QUOTES)
    assert r.kept and r.rendered == "At the higher bonus it would be higher than a fixed deposit."


def test_comparison_with_offer_as_object_flips_direction():
    text = "A fixed deposit earns more than this plan."
    assert check_argument(text, ["cmp_return_low_vs_fd"], CFACTS, QUOTES).kept
    assert not check_argument("A fixed deposit would do better.", ["cmp_return_low_vs_fd"], CFACTS, QUOTES).kept


def test_comparison_word_without_cmp_citation_dropped():
    r = check_argument("This plan returns {endowment_return}, lower than you think.", [], CFACTS, QUOTES)
    assert isinstance(r, Dropped) and "cmp_" in r.reason


def test_comparisons_can_be_switched_off_for_questions():
    assert check_argument("Is there a lower rate?", ["q1"], CFACTS, QUOTES, comparisons=False).kept


def test_ambiguous_display_is_not_auto_replaced():
    # two different values that display the same way: the number is ambiguous, so it is dropped
    facts = [
        Fact(id="term.a", label="", value=15, unit="years", kind="offer", formula=""),
        Fact(id="term.b", label="", value=15.02, unit="years", kind="offer", formula=""),
    ]
    r = check_argument("You pay for 15 years.", ["q1"], facts, QUOTES)
    assert isinstance(r, Dropped) and "raw number" in r.reason


def test_short_id_fix_is_reported():
    facts = [*FACTS, Fact(id="term.sum_assured", label="", value=750_000, unit="INR", kind="offer", formula="")]
    r = check_argument("Only {sum_assured} is guaranteed.", [], facts, QUOTES)
    assert r.fixes == ["short id {sum_assured} -> {term.sum_assured}"]


def test_auto_placeholder_before_punctuation_but_not_inside_longer_numbers():
    from app.engines.fact import Fact

    facts = [Fact(id="emi_share", label="", value=0.168, unit="fraction", kind="personal", formula="")]
    r = check_argument("Your EMIs will be 16.8%, which is a lot.", [], facts, QUOTES)
    assert r.kept and r.cited == ["emi_share"]
    assert not check_argument("It is 116.8% now.", [], facts, QUOTES).kept
    assert not check_argument("It is 16.85% now.", [], facts, QUOTES).kept
