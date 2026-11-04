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


# ---------------------------------------------------------------- flat or reducing: the words decide
def rate_term(quote: str, text: str):
    term = ExtractedTerm(name="flat_rate", value_text="9.5%", evidence_quote=quote)
    return verify_term(term, [EvidenceText(quote_id="q1", source="transcript", text=text)])


def test_a_reducing_rate_is_never_treated_as_flat():
    got = rate_term("9.5%", "A loan of 80,000 at 9.5% a year on reducing balance for 24 months.")
    assert got.verified and got.name == "reducing_rate" and got.value == 0.095


def test_a_flat_rate_stays_flat():
    got = rate_term("9.5% flat", "A loan of 80,000 at 9.5% flat for 24 months.")
    assert got.verified and got.name == "flat_rate"


def test_a_rate_that_is_neither_is_not_assumed_flat():
    got = rate_term("9.5%", "A loan of 80,000 at 9.5% a year for 24 months.")
    assert not got.verified and got.reason == "not written as a flat rate"


# ---------------------------------------------------------------- a photo: the model and Tesseract must agree
def photo_term(value: str, ocr: str, *, vision: bool = True):
    term = ExtractedTerm(
        name="premium", value_text=value, evidence_quote=f"Annual premium: Rs. {value}", source="page_1"
    )
    page = EvidenceText(quote_id="q1", source="page_1", text=f"Annual premium: Rs. {value}", ocr_text=ocr)
    return verify_term(term, [page], vision_read=vision)


def test_a_photo_term_is_read_twice_only_when_both_agree():
    got = photo_term("50,000", "Annual premium: Rs. 50,000")
    assert got.verified and got.reading == "twice"


def test_a_photo_term_is_refused_when_tesseract_disagrees():
    got = photo_term("80,000", "Annual premium: Rs. 50,000")
    assert not got.verified and got.reason == "photo reading did not confirm the number"


def test_without_vision_a_photo_is_only_read_once():
    assert photo_term("50,000", "Annual premium: Rs. 50,000", vision=False).reading == "once"
