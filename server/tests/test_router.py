import pytest

from app.pipeline.router import route

CASES = [
    ("insurance_offer", None, ["dani", "sankz"]),
    ("insurance_offer", {"market_linked": True}, ["dani", "sankz", "vick"]),
    ("insurance_offer", {"market_linked": False}, ["dani", "sankz"]),
    ("ulip", None, ["dani", "sankz", "vick"]),
    ("market_linked_insurance", [], ["dani", "sankz", "vick"]),
    ("loan_offer", None, ["sankz"]),
    ("loan_offer", {"amount_vs_savings": True}, ["sankz"]),
    ("sip_or_fund_question", None, ["dani"]),
    ("sip_or_fund_question", {"amount_vs_savings": True}, ["dani", "sankz"]),
    ("sip_or_fund_question", ["amount_vs_savings"], ["dani", "sankz"]),
    ("stock_tip", None, ["vick"]),
    ("stock_tip", {"amount_large": True}, ["vick", "sankz"]),
    ("stock_tip", {"amount_vs_savings": True}, ["vick", "sankz"]),
    ("shares", None, ["vick"]),
    ("ipo", {"amount_large": True}, ["vick", "sankz"]),
    ("general_money", None, ["sankz", "dani"]),
    ("scam_or_payment_request", None, []),
    ("scam_or_payment_request", {"amount_large": True}, []),
    ("out_of_scope", None, []),
    ("something_new", None, ["sankz", "dani"]),
    ("investment_question", None, ["dani"]),
]


@pytest.mark.parametrize("case_type,flags,agents", CASES)
def test_route(case_type, flags, agents):
    assert route(case_type, flags) == agents


def test_never_more_than_three():
    assert all(len(route(ct, {"market_linked": True, "amount_large": True})) <= 3 for ct, _, _ in CASES)
