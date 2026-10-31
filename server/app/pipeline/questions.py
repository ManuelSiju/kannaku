"""Questions said aloud at the end of an answer. Code owns them: a fixed bank per case type, ordered by what this
case is missing (unverified terms) and which claims were contradicted. The explainer may only pick ids from the bank
and reword them; a rewording is kept only if it keeps the meaning (every key word, the same digits, under 12 words),
otherwise the bank wording is used. Malayalam / Hindi questions are always the bank wording.

audience: who the question is for. A stock tip has no seller: its questions are for the sender or the user.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

from app.engines.fact import Fact
from app.pipeline.claims import ClaimCheck
from app.pipeline.privacy import PrivacyMode, speech_allowed
from app.pipeline.schemas import TERM_NAMES

Audience = Literal["seller", "sender", "self"]
MAX_QUESTIONS = 3
MAX_WORDS = 11  # "under 12 words"


class BankQuestion(BaseModel):
    id: str
    text: dict[str, str]  # lang -> wording
    keys: list[str]  # lower-case words a rewording must keep (meaning unchanged)
    audience: Audience = "seller"
    terms: list[str] = []  # an unverified / missing term that brings this question to the front
    claim: Literal["guarantee", "rate"] | None = None  # a contradicted claim of this kind brings it to the front


def _q(id: str, en: str, ml: str, hi: str, keys: list[str], **kw: object) -> BankQuestion:
    return BankQuestion(id=id, text={"en": en, "ml": ml, "hi": hi}, keys=keys, **kw)  # type: ignore[arg-type]


BANK: dict[str, list[BankQuestion]] = {
    "insurance": [
        _q("ins_guaranteed", "How much is guaranteed in writing?", "എഴുതി ഉറപ്പുള്ള തുക എത്രയാണ്?",
           "लिखित में कितना पक्का मिलेगा?", ["guarant", "writing"], terms=["sum_assured"], claim="guarantee"),
        _q("ins_lower_bonus", "What do I get at the lower bonus rate?", "കുറഞ്ഞ ബോണസ് നിരക്കിൽ എനിക്ക് എത്ര കിട്ടും?",
           "कम बोनस दर पर मुझे कितना मिलेगा?", ["lower", "bonus"], terms=["maturity_low"]),
        _q("ins_higher_bonus", "What do I get at the higher bonus rate?",
           "കൂടിയ ബോണസ് നിരക്കിൽ എനിക്ക് എത്ര കിട്ടും?", "ज़्यादा बोनस दर पर मुझे कितना मिलेगा?",
           ["higher", "bonus"], terms=["maturity_high"]),
        _q("ins_stop_early", "What do I get if I stop after 3 years?",
           "3 വർഷം കഴിഞ്ഞ് നിർത്തിയാൽ എനിക്ക് എന്ത് കിട്ടും?", "3 साल बाद बंद करूँ तो मुझे क्या मिलेगा?",
           ["stop"], terms=["pay_years", "policy_years"]),
        _q("ins_bonus_rate", "What bonus rate did you assume?", "ഏത് ബോണസ് നിരക്കാണ് നിങ്ങൾ കണക്കാക്കിയത്?",
           "आपने कौन-सी बोनस दर मानी है?", ["bonus", "rate"], terms=["bonus_rate_low", "bonus_rate_high"],
           claim="rate"),
    ],
    "loan": [
        _q("loan_reducing_rate", "What is the reducing-balance interest rate?",
           "കുറയുന്ന ബാക്കിയിൽ പലിശ നിരക്ക് എത്രയാണ്?", "घटती बकाया राशि पर ब्याज दर कितनी है?",
           ["reducing", "rate"], terms=["flat_rate"], claim="rate"),
        _q("loan_charges", "What are the processing and prepayment charges?",
           "പ്രോസസിംഗ്, മുൻകൂർ അടവ് ചാർജുകൾ എത്രയാണ്?", "प्रोसेसिंग और जल्दी चुकाने के चार्ज कितने हैं?",
           ["processing", "prepayment"]),
    ],
    "stock": [
        _q("stock_who", "Who sent this tip, and do they own the stock?",
           "ഈ ടിപ്പ് ആരാണ് അയച്ചത്, അവർക്ക് ഈ ഓഹരി ഉണ്ടോ?", "यह टिप किसने भेजी, और क्या उनके पास यह शेयर है?",
           ["who", "own"], audience="sender", terms=["stock name"]),
        _q("stock_why_rising", "Why is it rising this fast?", "ഇത് എന്തിനാണ് ഇത്ര വേഗം കയറുന്നത്?",
           "यह इतनी तेज़ी से क्यों बढ़ रहा है?", ["why", "rising"], audience="sender", terms=["price history"]),
        _q("stock_lose", "Can you afford to lose this money?", "ഈ പണം നഷ്ടപ്പെട്ടാൽ താങ്ങാനാകുമോ?",
           "क्या आप यह पैसा खोना सह सकते हैं?", ["lose"], audience="self"),
    ],
    "chit_fund": [
        _q("chit_registered", "Is it registered? What is the registration number?",
           "ഇത് രജിസ്റ്റർ ചെയ്തതാണോ? രജിസ്ട്രേഷൻ നമ്പർ എന്താണ്?", "क्या यह रजिस्टर्ड है? रजिस्ट्रेशन नंबर क्या है?",
           ["registration"]),
        _q("chit_foreman_cut", "What is the foreman's cut?", "ഫോർമാന്റെ കമ്മീഷൻ എത്രയാണ്?",
           "फोरमैन का हिस्सा कितना है?", ["foreman"]),
    ],
}  # fmt: skip
GROUP = {
    "insurance_offer": "insurance",
    "ulip": "insurance",
    "loan_offer": "loan",
    "stock_tip": "stock",
    "shares": "stock",
    "ipo": "stock",
    "chit_fund": "chit_fund",
}
# Words that must never appear in a question for this group (a tip has no seller and no "fundamentals" check).
BANNED = {"stock": re.compile(r"fundamental|seller|salesman|agent|company'?s", re.I)}
SHOW_IN_WRITING = {
    "en": "Can you show me the {term} in writing?",
    "ml": "{term} എഴുതി കാണിക്കാമോ?",
    "hi": "क्या आप {term} लिखित में दिखा सकते हैं?",
}
_DIGITS = re.compile(r"\d+")


class Question(BaseModel):
    id: str
    text: str
    audience: Audience = "seller"
    reason: str = "default"  # claim | missing:<term> | default


class Picked(BaseModel):
    questions: list[Question]
    reworded: list[dict[str, str]] = []  # {"id", "from", "to"}
    rejected: list[dict[str, str]] = []  # {"id", "text", "why"}


def group_of(case_type: str) -> str | None:
    return GROUP.get(case_type)


def candidates(case_type: str, unverified: list[str], claims: list[ClaimCheck], lang: str = "en") -> list[Question]:
    """The bank for this case type, most relevant first: contradicted claims, then missing terms, then a
    "show me in writing" question for any other missing document term, then the rest of the bank."""
    group = group_of(case_type)
    if group is None:
        return []
    bank = BANK[group]
    lang = lang if lang in SHOW_IN_WRITING else "en"
    kinds = {_claim_kind(c) for c in claims if c.status == "contradicted"}
    out: list[Question] = []

    def add(b: BankQuestion, reason: str) -> None:
        if all(q.id != b.id for q in out):
            out.append(Question(id=b.id, text=b.text[lang], audience=b.audience, reason=reason))

    for b in bank:
        if b.claim and b.claim in kinds:
            add(b, "claim")
    for term in unverified:
        for b in bank:
            if term in b.terms:
                add(b, f"missing:{term}")
    if group in ("insurance", "loan"):
        covered = {t for b in bank for t in b.terms}
        for term in unverified:
            if term in TERM_NAMES and term not in covered:
                out.append(
                    Question(
                        id=f"show_{term}",
                        text=SHOW_IN_WRITING[lang].format(term=TERM_NAMES[term]),
                        reason=f"missing:{term}",
                    )
                )
    for b in bank:
        add(b, "default")
    return out


def _claim_kind(c: ClaimCheck) -> str:
    return "guarantee" if re.search(r"guarant", f"{c.claim} {c.quote}", re.I) else "rate"


def _allowed(text: str, facts: list[Fact], mode: PrivacyMode) -> bool:
    return speech_allowed(text, [], facts, mode).allowed


def _rewording_ok(original: str, new: str, keys: list[str], group: str) -> str | None:
    """None if the rewording keeps the meaning, else why not."""
    low = new.lower()
    if len(new.split()) > MAX_WORDS:
        return "12 words or more"
    if not new.rstrip().endswith("?"):
        return "not a question"
    if missing := [k for k in keys if k not in low]:
        return f"lost key word(s): {', '.join(missing)}"
    if sorted(_DIGITS.findall(new)) != sorted(_DIGITS.findall(original)):
        return "changed a number"
    if (ban := BANNED.get(group)) and ban.search(new):
        return "banned word for this case type"
    return None


def pick(
    case_type: str,
    bank: list[Question],
    llm_picks: list[tuple[str, str]],
    facts: list[Fact],
    mode: PrivacyMode,
    lang: str = "en",
) -> Picked:
    """llm_picks: (id, reworded text) chosen by the explainer. Unknown ids are ignored. If the model picked nothing
    usable, the first questions of the bank are used. Questions brought forward by a claim or a missing term are
    always kept (within the limit)."""
    group = group_of(case_type) or ""
    by_id = {q.id: q for q in bank}
    keys = {b.id: b.keys for g in BANK.values() for b in g}
    chosen: list[Question] = []
    reworded: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []

    def take(q: Question) -> None:
        if all(c.id != q.id for c in chosen) and _allowed(q.text, facts, mode):
            chosen.append(q)

    for qid, text in llm_picks:
        q = by_id.get(qid)
        if q is None:
            rejected.append({"id": qid, "text": text, "why": "not in the question bank"})
            continue
        text = text.strip()
        if lang == "en" and text and text != q.text:
            why = _rewording_ok(q.text, text, keys.get(qid, []), group)
            if why is None and _allowed(text, facts, mode):
                reworded.append({"id": qid, "from": q.text, "to": text})
                q = q.model_copy(update={"text": text})
            else:
                rejected.append({"id": qid, "text": text, "why": why or "privacy"})
        take(q)
    model_chose = bool(chosen)
    for q in bank:
        if q.reason != "default" or not model_chose:
            take(q)
    chosen.sort(key=lambda q: q.reason == "default")  # stable: claim / missing-term questions first
    return Picked(questions=chosen[:MAX_QUESTIONS], reworded=reworded, rejected=rejected)
