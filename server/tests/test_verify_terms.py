from app.pipeline.schemas import ExtractedTerm
from app.pipeline.verify_terms import EvidenceText, fuzzy_contains, term_fact, verify_term

PAGE = EvidenceText(quote_id="q2", source="page_1", text="Annual premium:  Rs. 50,000\nPolicy term: 15 years")
PHOTO = EvidenceText(quote_id="q3", source="page_2", text="Premium Rs. 50,000", ocr_text="Premium Rs. 50,000")
TRANSCRIPT = EvidenceText(quote_id="q1", source="transcript", text="loan at 12% flat for 24 months")


def T(name, value, quote, source="page_1"):
    return ExtractedTerm(name=name, value_text=value, evidence_quote=quote, source=source)


def test_verified_term_and_fact():
    t = verify_term(T("premium", "Rs. 50,000", "Annual premium: Rs. 50,000"), [PAGE])
    assert t.verified and t.value == 50_000 and t.unit == "INR" and t.quote_id == "q2"
    f = term_fact(t)
    assert f.id == "term.premium" and f.kind == "offer" and f.inputs["quote_id"] == "q2"


def test_units_from_names():
    assert verify_term(T("flat_rate", "12%", "at 12% flat", "transcript"), [TRANSCRIPT]).value == 0.12
    t = verify_term(T("tenure_months", "24 months", "for 24 months", "transcript"), [TRANSCRIPT])
    assert t.verified and t.unit == "months" and t.value == 24


def test_quote_not_in_evidence():
    t = verify_term(T("premium", "Rs. 60,000", "Annual premium: Rs. 60,000 only for you"), [PAGE])
    assert not t.verified and "quote not found" in t.reason and term_fact(t) is None


def test_number_must_be_in_quote():
    t = verify_term(T("premium", "Rs. 55,000", "Annual premium: Rs. 50,000"), [PAGE])
    assert not t.verified and "not in the quoted words" in t.reason


def test_photo_needs_second_reading():
    bad = PHOTO.model_copy(update={"ocr_text": "Premium Rs. 30,000"})
    assert verify_term(T("premium", "50,000", "Premium Rs. 50,000", "page_2"), [PHOTO]).verified
    t = verify_term(T("premium", "50,000", "Premium Rs. 50,000", "page_2"), [bad])
    assert not t.verified and "photo reading" in t.reason


def test_unknown_name_and_unparseable():
    assert "unknown term" in verify_term(T("bonus_magic", "5", "Policy term: 15 years"), [PAGE]).reason
    assert "could not read" in verify_term(T("premium", "fifty thousand", "Annual premium"), [PAGE]).reason


def test_fuzzy_contains_tolerates_ocr_noise():
    assert fuzzy_contains("Annual premium: Rs. 50,000", "Annual  premium : Rs. 50,000") >= 0.9
    assert fuzzy_contains("Sum assured is ten crore guaranteed forever", PAGE.text) < 0.9
