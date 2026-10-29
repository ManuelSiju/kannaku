from decimal import Decimal

import pytest

from app.numbers.indian_number_parser import find_amounts, find_percents, parse_amount, parse_percent

AMOUNTS = [
    ("₹1,50,000", 150000),
    ("1,50,000", 150000),
    ("150000", 150000),
    ("50k", 50000),
    ("50 K", 50000),
    ("1.5 lakh", 150000),
    ("15 lakh", 1500000),
    ("15 lakhs", 1500000),
    ("2 crore", 20000000),
    ("2.5 cr", 25000000),
    ("Rs. 4,500", 4500),
    ("INR 4500", 4500),
    ("₹15,00,000", 1500000),
    ("rs 10,20,000", 1020000),
    ("150,000", 150000),
    ("12 lacs", 1200000),
    ("2 thousand", 2000),
    ("₹5,166.67", Decimal("5166.67")),
    ("1.5 ലക്ഷം", 150000),
    ("2 കോടി", 20000000),
    ("5 ആയിരം", 5000),
    ("3 लाख", 300000),
    ("1 करोड़", 10000000),
    ("4 हज़ार", 4000),
    ("premium of 50,000 every year", 50000),
    ("pay ₹ 12,000/year", 12000),
    ("0.5 lakh", 50000),
    ("Rupees 2,400 a month", 2400),
]


@pytest.mark.parametrize("text,expected", AMOUNTS)
def test_parse_amount(text, expected):
    assert parse_amount(text) == Decimal(str(expected))


@pytest.mark.parametrize("text", ["no numbers here", "", "lakh", "₹"])
def test_parse_amount_none(text):
    assert parse_amount(text) is None


def test_percent_is_not_an_amount():
    assert parse_amount("12% flat") is None
    assert find_amounts("at 7 percent") == []


def test_units_need_word_boundary():
    # "50 km" is not 50 thousand
    assert parse_amount("50 km away") == 50


def test_find_amounts_many():
    vals = [a.value for a in find_amounts("Pay 50,000 a year for 15 years, get 10,20,000 or 15 lakh.")]
    assert vals == [50000, 15, 1020000, 1500000]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("12%", 12),
        ("3.8 %", Decimal("3.8")),
        ("7 percent", 7),
        ("8 per cent bonus", 8),
        ("rate 21.6%", Decimal("21.6")),
    ],
)
def test_parse_percent(text, expected):
    assert parse_percent(text) == Decimal(str(expected))


def test_parse_percent_none():
    assert parse_percent("50,000") is None
    assert [p.value for p in find_percents("4% and 8% bonus")] == [4, 8]
