from app.engines.fact import Fact
from app.pipeline.labels import source_label, unverified_label


def F(id, status="known", **inputs):
    return Fact(id=id, label="", value=1 if status == "known" else None, unit="INR", kind="offer", formula="",
                inputs=inputs, status=status)  # fmt: skip


def test_term_labels():
    assert (
        source_label(F("term.premium", source="page_1", photo=True), "insurance_offer")
        == "Brochure page 1 · read twice"
    )
    assert source_label(F("term.premium", source="page_2", photo=False), "loan_offer") == "Loan offer page 2 · checked"
    assert source_label(F("term.flat_rate", source="transcript"), "loan_offer") == "What you said · checked"


def test_profile_and_reference_labels():
    assert source_label(F("profile.monthly_income", source="voice"), "x") == "You told us by voice"
    assert source_label(F("profile.monthly_expenses", source="typed"), "x") == "You typed it"
    assert (
        source_label(F("profile.savings", source="document", source_ref="passbook photo"), "x")
        == "From your passbook photo"
    )
    assert source_label(F("profile.savings", status="unknown"), "x") == "Not told yet"
    assert source_label(F("ref.fd_rate", as_of="2026-10-01"), "x") == "Assumption · as of 1 Oct 2026"
    assert source_label(F("existing_emi"), "x") == "Added up from your saved loans and policies"
    assert source_label(F("fd_value"), "x") == "Worked out by Kanakku"


def test_unverified_label():
    assert (
        unverified_label("page_3", "quote not found", "stock_tip")
        == "Message page 3 · could not check (quote not found)"
    )
