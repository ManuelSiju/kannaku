import pytest

from app.pipeline.scam_rules import detect

CASES = [
    ("otp_pin_request", "Madam please tell me the OTP you just received"),
    ("otp_pin_request", "Share your ATM PIN to verify the account"),
    ("otp_pin_request", "What is the CVV on the back of your card, just read out the CVV"),
    ("otp_pin_request", "ഒടിപി പറയൂ"),
    ("otp_pin_request", "ओटीपी बताओ जल्दी"),
    ("remote_access", "Install AnyDesk so I can help you with the refund"),
    ("remote_access", "Download Team Viewer quick"),
    ("remote_access", "open QuickSupport and give me the code"),
    ("remote_access", "Please start screen sharing on WhatsApp"),
    ("digital_arrest", "You are under digital arrest, stay on the call"),
    ("digital_arrest", "This is CBI, we will arrest your son unless you stay on video call"),
    ("kyc_urgency", "Your KYC has expired, your account will be blocked today"),
    ("kyc_urgency", "Dear customer your account will be suspended, update KYC now"),
    ("pay_to_receive", "You won a lottery prize, pay the processing fee of 5,000 to release it"),
    ("pay_to_receive", "Send 2000 to this UPI ID to receive your refund"),
    ("collect_request", "I have sent a collect request, just approve it"),
    ("collect_request", "Enter your UPI PIN to receive the money"),
]


@pytest.mark.parametrize("rule,text", CASES)
def test_rule_triggers_on_transcript(rule, text):
    signals = detect(text, None)
    assert rule in {s.rule for s in signals}, signals
    assert all(s.source == "transcript" for s in signals)


def test_document_source():
    signals = detect("", "Install AnyDesk and pay the processing fee to receive the bonus")
    assert {s.rule for s in signals} >= {"remote_access", "pay_to_receive"}
    assert {s.source for s in signals} == {"document"}


@pytest.mark.parametrize(
    "text",
    [
        "The bank says never share your OTP with anyone.",
        "I want to know if this insurance plan with 50,000 premium is good for me.",
        "My son pays the scooter loan EMI of 2,400 every month.",
        "I updated my KYC at the branch last year.",
        "Should I put 5,000 a month in a SIP?",
        "Do not tell anyone your PIN.",
    ],
)
def test_innocent_sentences_do_not_trigger(text):
    assert detect(text, text) == []


def test_explanations_are_plain():
    s = detect("tell me the OTP", None)[0]
    assert "OTP" in s.explanation and s.matched_text
