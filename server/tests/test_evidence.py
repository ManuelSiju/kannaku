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


def test_raw_digit_is_dropped_even_if_correct():
    r = check_argument("This plan returns about 3.8% a year.", ["endowment_return"], FACTS, QUOTES)
    assert isinstance(r, Dropped) and "raw number" in r.reason and "3.8" in r.reason


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
