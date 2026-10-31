"""Pydantic models for every LLM output and for the API result of one ask."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.pipeline.consensus import Colour

CaseType = Literal[
    "insurance_offer",
    "ulip",
    "loan_offer",
    "sip_or_fund_question",
    "stock_tip",
    "shares",
    "ipo",
    "general_money",
    "scam_or_payment_request",
    "out_of_scope",
    "unknown",
]
AgentName = Literal["sankz", "dani", "vick"]

# Canonical term names the case builder may extract (the prompt lists them).
TERM_NAMES = {
    "premium": "yearly premium",
    "pay_years": "number of years you pay",
    "policy_years": "policy term in years",
    "sum_assured": "guaranteed sum assured",
    "maturity_low": "lowest illustrated maturity amount",
    "maturity_high": "highest illustrated maturity amount",
    "bonus_rate_low": "lower illustrated bonus rate",
    "bonus_rate_high": "higher illustrated bonus rate",
    "loan_amount": "loan amount",
    "flat_rate": "flat interest rate",
    "tenure_months": "loan period in months",
    "monthly_amount": "monthly amount",
    "invest_amount": "amount to invest",
    "years": "number of years",
}


# ---------------------------------------------------------------- LLM call 1: case builder
class ExtractedTerm(BaseModel):
    name: str
    value_text: str  # exactly as written, e.g. "Rs. 50,000"
    evidence_quote: str  # copied word for word from the transcript or a page
    source: str = "transcript"  # "transcript" | "page_N"


class SellerClaim(BaseModel):
    text: str
    quote: str = ""


class CaseDraft(BaseModel):
    case_type: CaseType
    terms: list[ExtractedTerm] = []
    seller_claims: list[SellerClaim] = []
    missing_terms: list[str] = []
    language: str = "en"
    stock_symbol: str | None = None
    flags: list[str] = []  # e.g. "market_linked" (kept only with a supporting quote, see pipeline/flags.py)
    market_linked_quote: str | None = None  # words from the document showing returns depend on the market


# ---------------------------------------------------------------- LLM calls 2-3: council and debate
class Argument(BaseModel):
    text: str
    cited_ids: list[str] = []


class AgentOpinion(BaseModel):
    agent: AgentName
    stance: Literal["for", "against", "unsure"]
    strength: float = Field(ge=0, le=1)
    arguments: list[Argument] = []
    questions_for_seller: list[str] = []

    @field_validator("arguments")
    @classmethod
    def _max_two(cls, v: list[Argument]) -> list[Argument]:
        return v[:2]


class CouncilOutput(BaseModel):
    opinions: list[AgentOpinion]


# ---------------------------------------------------------------- LLM call 4: explainer
class Line(BaseModel):
    speaker: str
    text: str
    cited_ids: list[str] = []


class ExplainerOutput(BaseModel):
    agent_lines: list[Line] = []
    verdict_sentence: Line
    questions: list[str] = []


class RewriteOutput(BaseModel):
    lines: list[Line]


# ---------------------------------------------------------------- API result
class VerdictOut(BaseModel):
    colour: Colour | None  # None for out-of-scope questions
    sentence: str
    questions: list[str] = []


class SpokenLineOut(BaseModel):
    speaker: str
    text: str


class ScreenDetail(BaseModel):
    id: str
    label: str
    value: str
    kind: Literal["offer", "personal"]
    source: str


class ShortAnswer(BaseModel):
    text: str  # one Alfii sentence, at most 20 words (the default reply)
    colour: Colour | None


class CouncilLine(BaseModel):
    speaker: str
    text: str  # spoken form (Indian number words)
    kind: Literal["opener", "agent", "rebuttal", "note", "claim", "conclusion"]


class ClaimOut(BaseModel):
    claim: str
    status: Literal["supported", "contradicted", "cant_verify"]
    evidence_ids: list[str] = []
    evidence: str = ""


class CaseResult(BaseModel):
    case_id: int
    case_type: str
    verdict: VerdictOut
    called_agents: list[str]
    spoken_lines: list[SpokenLineOut]
    screen_details: list[ScreenDetail]
    privacy_mode: Literal["full", "discreet"]
    degraded: bool
    degraded_steps: list[str]
    llm_calls: int
    language: str = "en"
    short_answer: ShortAnswer | None = None
    council: list[CouncilLine] = []  # opener, each called agent once, rebuttals, notes, claims, Alfii's conclusion
    council_words: int = 0
    council_seconds: float = 0.0  # at 150 words a minute
    suggested_followups: list[str] = []
    claims: list[ClaimOut] = []
