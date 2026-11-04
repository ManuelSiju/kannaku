import pytest

from app.engines.fact import format_inr
from app.engines.finance import (
    affordability,
    endowment_return,
    fd_value,
    flat_to_effective,
    irr_annual,
    irr_rate,
    reducing_loan,
    sip_value,
)
from tests.calibration.oracle import reducing_emi


def by_id(facts):
    return {f.id: f for f in facts}


# ---- golden values (from the build spec) ----


def test_golden_endowment_return():
    f = endowment_return(premium=50_000, pay_years=15, payout=10_20_000, payout_year=15)
    assert f.id == "endowment_return" and f.unit == "fraction" and f.kind == "offer"
    assert f.value == pytest.approx(0.038, abs=0.002)


def test_golden_fd_value():
    f = fd_value(50_000, 15, 0.07)
    assert f.value == pytest.approx(13.44e5, abs=0.05e5)
    assert f.unit == "INR"


def test_golden_flat_to_effective():
    f = by_id(flat_to_effective(1_00_000, 0.12, 24))
    assert f["loan_emi"].value == pytest.approx(5166.67, abs=0.01)
    assert f["loan_total_interest"].value == pytest.approx(24_000)
    assert f["loan_effective_rate"].value == pytest.approx(0.216, abs=0.003)


def test_golden_affordability_missing_expenses_is_unknown_not_zero():
    f = by_id(affordability(45_000, None, 1_60_000, 2_400, 4_167, regular_commitments=1_000))
    assert f["buffer_months_after"].status == "unknown"
    assert f["buffer_months_after"].value is None
    assert "monthly_expenses" in f["buffer_months_after"].inputs["missing"]
    assert f["surplus_after"].value is None
    assert f["emi_share"].value == pytest.approx((2_400 + 4_167) / 45_000, abs=1e-4)


# ---- behaviour ----


def test_affordability_demo_family():
    f = by_id(affordability(45_000, 28_000, 1_60_000, 2_400, 50_000 / 12, regular_commitments=1_000))
    assert all(x.kind == "personal" for x in f.values())
    assert f["surplus_after"].value == pytest.approx(45_000 - 28_000 - 2_400 - 1_000 - 50_000 / 12, abs=0.01)
    assert f["buffer_months_after"].value == pytest.approx(1_60_000 / (28_000 + 2_400 + 1_000 + 50_000 / 12), abs=0.01)


def test_affordability_zero_income_is_unknown():
    assert by_id(affordability(0, 1, 1, 0, 1, regular_commitments=0))["emi_share"].status == "unknown"


def test_irr_simple_and_no_sign_change():
    assert irr_rate([(0, -100), (1, 110)]) == pytest.approx(0.10, abs=1e-9)
    assert irr_rate([(0, 100), (1, 110)]) is None
    f = irr_annual([(0, 100), (1, 10)])
    assert f.status == "unknown" and f.value is None


def test_irr_negative_return():
    assert irr_rate([(0, -100), (1, 90)]) == pytest.approx(-0.10, abs=1e-9)


def test_fd_and_sip_zero_rate():
    assert fd_value(1000, 3, 0).value == 3000
    assert sip_value(1000, 12, 0).value == 12000


def test_sip_value():
    # 5000/month, 120 months, 12% a year: standard annuity-due SIP formula ~ 11.6 lakh
    assert sip_value(5000, 120, 0.12).value == pytest.approx(11_61_695, rel=1e-3)


def test_prefix_namespaces_ids():
    assert fd_value(1, 1, 0.1, prefix="alt").id == "alt.fd_value"
    assert by_id(flat_to_effective(1000, 0.1, 12, prefix="bike")).keys() == {
        "bike.loan_emi",
        "bike.loan_total_interest",
        "bike.loan_effective_rate",
    }


def test_display():
    assert endowment_return(50_000, 15, 10_20_000, 15).display == "3.8%"
    assert format_inr(1344400) == "₹13,44,400"
    assert format_inr(5166.67) == "₹5,166.67"
    assert format_inr(999) == "₹999"


def test_regular_commitments_count_in_buffer_and_surplus_not_emi_share():
    f = by_id(affordability(45_000, 28_000, 1_60_000, 2_400, 4_000, regular_commitments=1_000))
    assert f["surplus_after"].value == pytest.approx(45_000 - 28_000 - 2_400 - 1_000 - 4_000)
    assert f["buffer_months_after"].value == pytest.approx(1_60_000 / 35_400, abs=0.01)
    assert f["emi_share"].value == pytest.approx(6_400 / 45_000, abs=1e-4)


def test_regular_commitments_unknown_makes_buffer_unknown():
    f = by_id(affordability(45_000, 28_000, 1_60_000, 2_400, 4_000, regular_commitments=None))
    assert f["buffer_months_after"].status == "unknown"
    assert "regular_commitments" in f["surplus_after"].inputs["missing"]
    assert f["emi_share"].status == "known"


def test_reducing_loan_matches_the_independent_formula():
    emi, interest, rate = reducing_loan(80_000, 0.095, 24)
    assert emi.value == pytest.approx(reducing_emi(80_000, 0.095, 24), abs=0.01)
    assert emi.value == pytest.approx(3673.16, abs=0.01)
    assert interest.value == pytest.approx(emi.value * 24 - 80_000, abs=0.01)
    assert rate.value == 0.095
