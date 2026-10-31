from app.pipeline.flags import routing_flags
from app.pipeline.schemas import CaseDraft
from app.pipeline.verify_terms import EvidenceText

ENDOW = [EvidenceText(quote_id="q2", source="page_1", text="Annual premium: Rs. 50,000. Sum assured guaranteed.")]
ULIP = [EvidenceText(quote_id="q2", source="page_1", text="Your fund value depends on the NAV of the units you hold.")]


def test_document_words_set_market_linked():
    flags, ct, why = routing_flags(CaseDraft(case_type="insurance_offer"), ULIP)
    assert "market_linked" in flags and ct == "insurance_offer" and "page_1" in why


def test_builder_flag_without_quote_is_ignored_and_ulip_downgraded():
    flags, ct, _ = routing_flags(CaseDraft(case_type="ulip", flags=["market_linked"]), ENDOW)
    assert flags == [] and ct == "insurance_offer"


def test_builder_flag_needs_quote_that_is_in_the_evidence():
    fake = CaseDraft(case_type="insurance_offer", flags=["market_linked"], market_linked_quote="market-linked returns")
    assert routing_flags(fake, ENDOW)[0] == []
    ev = [EvidenceText(quote_id="q3", source="transcript", text="he said it has market-linked returns")]
    assert routing_flags(fake, ev)[0] == ["market_linked"]


def test_transcript_words_alone_do_not_count():
    ev = [EvidenceText(quote_id="q1", source="transcript", text="is this a ULIP?")]
    assert routing_flags(CaseDraft(case_type="insurance_offer"), ev)[0] == []
