"""Claim checks (code, no LLM): every seller / relative / forwarded claim becomes supported, contradicted or
cant_verify, with the fact or quote ids that decide it. Contradicted claims must be mentioned to the user."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

from app.engines.fact import Fact
from app.numbers.indian_number_parser import find_amounts, find_percents
from app.pipeline.schemas import SellerClaim

ClaimStatus = Literal["supported", "contradicted", "cant_verify"]
_NOT_GUARANTEED = re.compile(r"[^.\n]*\bnot\s+guaranteed\b[^.\n]*", re.I)
_GUARANTEE = re.compile(r"guarant", re.I)
RETURN_FACT_IDS = ("endowment_return", "f_return_high", "f_return_guaranteed")


class ClaimCheck(BaseModel):
    claim: str
    quote: str = ""
    status: ClaimStatus
    evidence_ids: list[str] = []
    evidence: str = ""  # the words or fact that decide it, quotable to the user
    reason: str = ""


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= 0.01 * max(abs(b), 1.0)


def check_claims(
    claims: list[SellerClaim], facts: list[Fact], quotes: dict[str, dict[str, str]], case_type: str
) -> list[ClaimCheck]:
    by_id = {f.id: f for f in facts}
    not_guaranteed = next(
        (
            (qid, m.group(0).strip())
            for qid, q in quotes.items()
            if q["source"] != "transcript" and (m := _NOT_GUARANTEED.search(q["text"]))
        ),
        None,
    )
    out: list[ClaimCheck] = []
    for c in claims:
        text = f"{c.text} {c.quote}"
        amounts = [float(a.value) for a in find_amounts(text)]
        percents = [float(p.value) for p in find_percents(text)]
        base = {"claim": c.text, "quote": c.quote}
        if _GUARANTEE.search(text):
            guaranteed = by_id.get("term.sum_assured")
            if amounts and guaranteed and guaranteed.value and any(_close(a, guaranteed.value) for a in amounts):
                out.append(ClaimCheck(**base, status="supported", evidence_ids=["term.sum_assured"],
                                      evidence=f"guaranteed sum assured {guaranteed.display}",
                                      reason="the amount is the guaranteed sum assured"))  # fmt: skip
            elif not_guaranteed:
                qid, words = not_guaranteed
                ids = [qid] + [
                    fid for fid in ("term.maturity_high", "term.maturity_low")
                    if fid in by_id and any(_close(a, by_id[fid].value or -1) for a in amounts)
                ]  # fmt: skip
                out.append(ClaimCheck(**base, status="contradicted", evidence_ids=ids, evidence=words,
                                      reason="the document says it is not guaranteed"))  # fmt: skip
            else:
                why = "no one can guarantee a share price" if case_type in ("stock_tip", "shares", "ipo") else ""
                out.append(ClaimCheck(**base, status="cant_verify", reason=why or "nothing in the documents"))
        elif percents:
            returns = [by_id[f] for f in RETURN_FACT_IDS if f in by_id and by_id[f].value is not None]
            if not returns:
                out.append(ClaimCheck(**base, status="cant_verify", reason="no computed return to compare"))
                continue
            best = max(returns, key=lambda f: f.value or 0)
            claimed = max(percents)
            if claimed > (best.value or 0) * 100 + 0.5:
                out.append(ClaimCheck(**base, status="contradicted", evidence_ids=[best.id],
                                      evidence=f"even at best it grows about {best.display} a year",
                                      reason=f"claimed {claimed:g}% but the best case is {best.display}"))  # fmt: skip
            else:
                out.append(ClaimCheck(**base, status="supported", evidence_ids=[best.id], evidence=best.display))
        else:
            out.append(ClaimCheck(**base, status="cant_verify", reason="nothing in the documents to check it against"))
    return out


def mentioned(check: ClaimCheck, spoken: list[str]) -> bool:
    """Does any spoken line already deal with this claim? (key word of the claim, e.g. 'guarantee')."""
    key = "guarant" if _GUARANTEE.search(check.claim + check.quote) else None
    words = [w for w in re.findall(r"[A-Za-z]{5,}", check.claim)][:2]
    needles = [key] if key else words
    return any(n and any(n.lower() in s.lower() for s in spoken) for n in needles)
