from app.engines.finance import affordability, endowment_return, fd_value
from app.pipeline.evidence import Dropped, Kept, check_argument

FACTS = [
    endowment_return(50_000, 15, 10_20_000, 15),  # ~0.0379
    fd_value(50_000, 15, 0.07),  # ~13,44,400
    *affordability(45_000, 28_000, 1_60_000, 2_400, 50_000 / 12),
]
QUOTES = {
    "q1": "Bonus rates are not guaranteed and may change every year.",
    "q2": "Illustrated maturity value at 8% bonus: Rs. 15,00,000",
}


def test_correct_citation_kept():
    r = check_argument("This plan grows your money by only about 4% a year.", ["endowment_return"], FACTS, QUOTES)
    assert isinstance(r, Kept) and r.numbers == ["4%"]


def test_one_decimal_percent_and_lakh_rounding_kept():
    text = "It returns 3.8% a year; an FD would give 13.4 lakh over 15 years."
    assert check_argument(text, ["endowment_return", "fd_value"], FACTS, QUOTES).kept


def test_number_in_cited_quote_kept():
    assert check_argument("The 15 lakh is only at an 8% bonus.", ["q2"], FACTS, QUOTES).kept


def test_invented_percent_dropped():
    r = check_argument("An FD would give you 8% a year.", ["fd_value"], FACTS, QUOTES)
    assert isinstance(r, Dropped) and "8%" in r.reason


def test_number_matching_only_uncited_fact_dropped():
    r = check_argument("An FD would give you ₹13,44,400.", ["endowment_return"], FACTS, QUOTES)
    assert isinstance(r, Dropped) and "fd_value" in r.reason


def test_unknown_citation_dropped():
    r = check_argument("Bonus is not guaranteed.", ["q9"], FACTS, QUOTES)
    assert isinstance(r, Dropped) and "q9" in r.reason


def test_no_citation_dropped():
    assert not check_argument("This is a bad plan.", [], FACTS, QUOTES).kept


def test_text_without_numbers_and_valid_citation_kept():
    assert check_argument("The bonus is not guaranteed.", ["q1"], FACTS, QUOTES).kept


def test_kind_filter_ignores_other_kinds():
    text = "You would have ₹10,433 left each month."
    assert check_argument(text, ["surplus_after"], FACTS, QUOTES).kept
    assert not check_argument(text, ["surplus_after"], FACTS, QUOTES, kind_filter="offer").kept


def test_fraction_fact_needs_percent_form():
    assert not check_argument("returns 0 point 038", ["endowment_return"], FACTS, QUOTES).kept
