"""The ask pipeline. One AskBudget per ask (max LLM_MAX_CALLS_PER_ASK calls, timeout per call in the provider).

 1 ingest            audio/images/PDF/DOCX/text -> transcript + pages; evidence rows (ids stripped)
 2 scam_rules        code; any signal -> fast path (no LLM at all), red verdict, Alfii explains
 3 case_builder      LLM call 1 -> case type, terms, seller claims
 4 verify_terms      code; unverified terms excluded from maths, become questions
 5 compute           code; facts via app.mcp_server.tools (same functions as the MCP server)
 6 router            code; an "unknown" case type ends here: Alfii asks one clarifying question (no LLM call)
 7 council           LLM call 2, batched for all called agents
 8 evidence          code; on every argument
 9 debate            LLM call 3, only if disagreement > 0.4
10 consensus         code; weighted vote + safety overrides
11 privacy           code; decide_mode
12 explainer         LLM call 4 (+ one rewrite if budget allows); evidence + privacy check per line.
                    Alfii's opener is a code template, sent as an SSE event right after routing.
13 save              everything incl. dropped arguments, blocked lines, trace; guardian alert
Any failed step -> degraded=true with its name; the answer still returns what is known.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from pydantic import BaseModel

from app.config import Settings, get_settings
from app.db.repo import Repo
from app.engines.fact import Fact
from app.mcp_server import tools
from app.pipeline import council as council_mod
from app.pipeline import explainer as explainer_mod
from app.pipeline.compute import Computed, compute_facts
from app.pipeline.consensus import ConsensusResult, override_inputs_from_facts, run_consensus
from app.pipeline.events import BUS, DONE, EventBus
from app.pipeline.flags import routing_flags
from app.pipeline.ingest import Ingested, Upload, ingest
from app.pipeline.labels import source_label, unverified_label
from app.pipeline.privacy import decide_mode
from app.pipeline.router import route
from app.pipeline.scam_rules import ScamSignal, detect
from app.pipeline.schemas import CaseDraft, CaseResult, ScreenDetail, SpokenLineOut, VerdictOut
from app.pipeline.verify_terms import EvidenceText, VerifiedTerm, term_question, verify_terms
from app.prompts import prompts
from app.providers.llm import AskBudget, LLMProvider, use_budget
from app.providers.stt import STTProvider

log = logging.getLogger(__name__)

ALERT_YELLOW_MIN_COMMITMENT = 25_000
CONTEXT_CUES = re.compile(
    r"\b(?:he|she|they) (?:says|said|is saying|is asking|wants)\b|\bthe agent is here\b|\b(?:agent|man|lady|he|she)"
    r" is (?:here|sitting|with me)\b|\bsitting (?:here )?with me\b|\bwith me now\b",
    re.I,
)
SCAM_SENTENCE = "This looks like a scam. Do not share any code, do not install anything, and do not pay anyone."
CLARIFY = "Is this about a loan, a policy, an investment or a payment?"
OUT_OF_SCOPE = (
    "I help with money questions like loans, insurance, savings and stock tips. What would you like to check?"
)


class AskInput(BaseModel):
    family_id: int
    text: str | None = None
    audio: Upload | None = None
    files: list[Upload] = []
    earphones: bool = False
    user_says_alone: bool = False


class _Run:
    def __init__(self, case_id: int, repo: Repo, bus: EventBus) -> None:
        self.case_id, self.repo, self.bus = case_id, repo, bus
        self.degraded_steps: list[str] = []

    @asynccontextmanager
    async def step(self, name: str, **detail: Any) -> AsyncIterator[dict[str, Any]]:
        """Times the step, records the trace, publishes events. LLM/tool failures mark the step degraded and are
        swallowed so later steps still run with what is known."""
        info: dict[str, Any] = dict(detail)
        self.bus.publish(self.case_id, "step_started", step=name)
        t0, outcome = time.perf_counter(), "ok"
        try:
            yield info
        except Exception as e:
            outcome = "failed"
            info["error"] = f"{type(e).__name__}: {e}"
            self.degraded_steps.append(name)
            log.warning("case %s step %s failed: %s", self.case_id, name, info["error"])
        finally:
            ms = round((time.perf_counter() - t0) * 1000, 1)
            if info.get("degraded") and name not in self.degraded_steps:
                self.degraded_steps.append(name)
                outcome = "degraded"
            self.repo.add_trace(self.case_id, name, ms, outcome, info)
            self.bus.publish(self.case_id, "step_finished", step=name, outcome=outcome, ms=ms)


def _screen_details(facts: list[Fact], terms: list[VerifiedTerm], case_type: str) -> list[ScreenDetail]:
    out = [
        ScreenDetail(id=f.id, label=f.label, value=f.display, kind=f.kind, source=source_label(f, case_type))
        for f in facts
    ]
    for t in terms:
        if not t.verified:
            out.append(
                ScreenDetail(
                    id=f"term.{t.name}",
                    label=f"Could not check: {t.name.replace('_', ' ')}",
                    value=t.value_text,
                    kind="offer",
                    source=unverified_label(t.source, t.reason, case_type),
                )
            )
    return out


def _guarantee_unbacked(draft: CaseDraft, ing: Ingested) -> bool:
    claimed = any("guarant" in (c.text + " " + c.quote).lower() for c in draft.seller_claims)
    claimed = claimed or "guarantee" in ing.transcript.lower()
    return claimed and "not guaranteed" in ing.doc_text.lower()


async def run_pipeline(
    case_id: int,
    inp: AskInput,
    *,
    repo: Repo,
    llm: LLMProvider,
    stt: STTProvider | None,
    settings: Settings | None = None,
    bus: EventBus = BUS,
) -> CaseResult:
    settings = settings or get_settings()
    budget = AskBudget(settings.llm_max_calls_per_ask)
    run = _Run(case_id, repo, bus)
    with use_budget(budget):
        try:
            result = await _pipeline(run, inp, repo=repo, llm=llm, stt=stt)
        except Exception as e:  # last resort: never crash the request
            log.exception("case %s pipeline crashed", case_id)
            run.degraded_steps.append("pipeline")
            result = CaseResult(
                case_id=case_id,
                case_type="unknown",
                verdict=VerdictOut(
                    colour="yellow",
                    sentence=f"Something went wrong ({type(e).__name__}). Please try again or call your guardian.",
                ),
                called_agents=[],
                spoken_lines=[],
                screen_details=[],
                privacy_mode="discreet",
                degraded=True,
                degraded_steps=run.degraded_steps,
                llm_calls=budget.used,
            )
    result.llm_calls = budget.used
    repo.update_case(case_id, status="done", result_json=result.model_dump_json())
    bus.publish(case_id, DONE, verdict=result.verdict.colour, degraded=result.degraded)
    return result


async def _pipeline(run: _Run, inp: AskInput, *, repo: Repo, llm: LLMProvider, stt: STTProvider | None) -> CaseResult:
    case_id = run.case_id
    prior = repo.get_case(case_id) or {}

    # 1 ingest -------------------------------------------------------------------------------------------
    ing = Ingested(transcript=inp.text or "", language=None, pages=[])
    async with run.step("ingest") as info:
        ing = await ingest(text=inp.text, audio=inp.audio, files=inp.files, stt=stt)
        info.update(pages=len(ing.pages), transcript_chars=len(ing.transcript), problems=ing.problems)
        if ing.problems:
            info["degraded"] = True
    transcript = " ".join(x for x in (prior.get("transcript"), ing.transcript) if x).strip()
    repo.update_case(case_id, transcript=transcript, status="running")
    evidence: list[EvidenceText] = [
        EvidenceText(quote_id=q.id, source=q.source, text=q.text) for q in repo.get_quotes(case_id)
    ]  # follow-up: earlier evidence still counts
    if ing.transcript:
        evidence.append(
            EvidenceText(
                quote_id=repo.add_evidence(case_id, "transcript", ing.transcript),
                source="transcript",
                text=ing.transcript,
            )
        )
    for page in ing.pages:
        if page.text:
            qid = repo.add_evidence(case_id, page.source, page.text)
            evidence.append(EvidenceText(quote_id=qid, source=page.source, text=page.text, ocr_text=page.ocr_text))
    quotes = {q.id: {"source": q.source, "text": q.text} for q in repo.get_quotes(case_id)}  # stored = ids stripped
    quote_text = {k: v["text"] for k, v in quotes.items()}
    context_cue = bool(CONTEXT_CUES.search(transcript))
    mode = decide_mode(inp.earphones, inp.user_says_alone, None, context_cue)
    repo.update_case(case_id, privacy_mode=mode)

    # 2 scam rules (fast path) -------------------------------------------------------------------------------
    signals: list[ScamSignal] = []
    async with run.step("scam_rules") as info:
        signals = detect(transcript, ing.doc_text)
        info["signals"] = [s.model_dump() for s in signals]
    if signals:
        return _scam_result(run, signals, mode, repo, inp.family_id)

    # 3 case builder (LLM 1) ------------------------------------------------------------------------------
    draft = CaseDraft(case_type="unknown")
    async with run.step("case_builder") as info:
        user = {"question": transcript, "pages": [{"source": p.source, "text": p.text} for p in ing.pages]}
        draft, usage = await llm.chat_json(prompts.CASE_BUILDER, _json(user), CaseDraft, images=ing.images)
        info.update(
            case_type=draft.case_type,
            terms=len(draft.terms),
            ms_llm=usage.ms,
            tokens=[usage.prompt_tokens, usage.completion_tokens],
        )
    flags, case_type, flag_why = routing_flags(draft, evidence)  # market_linked only with document support
    repo.update_case(case_id, case_type=case_type, language=draft.language)

    if case_type == "unknown":  # Alfii asks one clarifying question; no extra LLM call
        return _simple_result(run, case_type, None, CLARIFY, mode, repo)
    if case_type == "out_of_scope":
        return _simple_result(run, case_type, None, OUT_OF_SCOPE, mode, repo)
    if case_type == "scam_or_payment_request":
        return _scam_result(run, [], mode, repo, inp.family_id)

    # 4 verify terms -----------------------------------------------------------------------------------------
    terms: list[VerifiedTerm] = []
    async with run.step("verify_terms") as info:
        terms = verify_terms(draft.terms, evidence)
        for t in terms:
            ev_id = int(t.quote_id[1:]) if t.quote_id else None
            repo.add_term(case_id, t.name, t.value, t.unit, evidence_id=ev_id, verified=t.verified, reason=t.reason)
        info["unverified"] = [t.name for t in terms if not t.verified]

    # 5 compute facts ------------------------------------------------------------------------------------------
    computed = Computed(facts=[], missing_required=[], flags=[], commitment=None)
    async with run.step("compute") as info:
        symbol = _stock_symbol(draft, transcript, ing.doc_text)
        computed = compute_facts(case_type, terms, inp.family_id, repo, stock_symbol=symbol, flags=flags)
        info.update(facts=[f.id for f in computed.facts], missing_required=computed.missing_required)
    facts = computed.facts
    repo.save_facts(case_id, facts)

    # 6 router ---------------------------------------------------------------------------------------------------
    agents = route(case_type, computed.flags)
    async with run.step("router") as info:
        info.update(case_type=case_type, flags=computed.flags, agents=agents, market_linked=flag_why)
    opening = explainer_mod.CheckedLine(speaker="alfii", text=explainer_mod.opener(agents))
    run.bus.publish(case_id, "alfii_opener", text=opening.text)  # spoken while the council works; no LLM
    for a in agents:
        run.bus.publish(case_id, "agent_called", agent=a)

    unverified = sorted({*computed.missing_required, *(t.name for t in terms if not t.verified)})
    summary = {
        "case_type": case_type,
        "question": transcript,
        "verified_terms": [{"name": t.name, "value": t.display, "quote_id": t.quote_id} for t in terms if t.verified],
        "unverified_terms": unverified,
        "seller_claims": [c.model_dump() for c in draft.seller_claims],
    }

    # 7-9 council, evidence, debate ------------------------------------------------------------------------------
    rounds: list[council_mod.CouncilRound] = []
    if agents:
        payload = council_mod.council_input(summary, facts, quotes, agents)
        async with run.step("council", agents=agents) as info:
            first, _ = await council_mod.run_council(llm, payload, agents, facts, quote_text)
            rounds.append(first)
            info.update(
                dropped=[a.drop_reason for a in first.arguments if not a.kept],
                auto_placeholder=[x for a in first.arguments for x in a.fixes],
                missing_agents=first.missing_agents,
                abstained=first.abstained,
            )
            if first.missing_agents:
                info["degraded"] = True
        if rounds:
            for a in agents:
                if a not in rounds[0].missing_agents:
                    run.bus.publish(case_id, "agent_done", agent=a, round=1)
            _, disagreement = _vote(case_type, rounds[0])
            if disagreement > 0.4:
                async with run.step("debate", disagreement=disagreement) as info:
                    second, _ = await council_mod.run_debate(llm, payload, rounds[0], agents, facts, quote_text)
                    rounds.append(second)
                    info.update(
                        dropped=[a.drop_reason for a in second.arguments if not a.kept],
                        auto_placeholder=[x for a in second.arguments for x in a.fixes],
                    )
    final = rounds[-1] if rounds else None
    for r in rounds:
        for p in r.positions:
            repo.add_position(case_id, p.agent, p.stance, p.strength, round=r.round)
        for a in r.arguments:
            repo.add_argument(
                case_id, a.agent, a.rendered or a.text, a.cited_ids, a.kept, drop_reason=a.drop_reason, round=r.round
            )

    # 10 consensus + overrides ---------------------------------------------------------------------------------------
    overrides = override_inputs_from_facts(
        facts, guaranteed_claim_unbacked=_guarantee_unbacked(draft, ing), unverified_required_terms=unverified
    )
    consensus: ConsensusResult = run_consensus(case_type, final.positions if final else [], overrides)
    async with run.step("consensus") as info:
        info.update(consensus.model_dump())

    # 11 privacy -------------------------------------------------------------------------------------------------------
    async with run.step("privacy") as info:
        info.update(mode=mode, earphones=inp.earphones, user_says_alone=inp.user_says_alone, context_cue=context_cue)

    # 12 explainer ---------------------------------------------------------------------------------------------------
    kept_args = [a.model_dump(include={"agent", "text", "cited_ids"}) for r in rounds for a in r.arguments if a.kept]
    candidate_qs = [term_question(n) for n in unverified] + (final.questions if final else [])
    lines: list[explainer_mod.CheckedLine] = []
    questions: list[str] = []
    async with run.step("explainer") as info:
        payload = explainer_mod.explainer_input(
            consensus.verdict,
            summary,
            agents,
            kept_args,
            # discreet: the explainer never even sees personal facts, so it cannot speak them
            council_mod.facts_table(facts, include_personal=mode == "full"),
            [{"id": k, **v} for k, v in quotes.items()],
            mode,
            draft.language,
            candidate_qs,
        )
        out, lines, rewrite_used, fixes = await explainer_mod.explain(llm, payload, facts, quote_text, mode)
        questions = out.questions
        info.update(
            rewrite_used=rewrite_used,
            blocked=[ln.blocked_reason for ln in lines if not ln.allowed],
            auto_placeholder=fixes,
        )
    if not lines:
        lines = explainer_mod.template_lines(consensus.verdict, agents, kept_args, facts, quote_text, mode)
    if not lines[-1].allowed:  # the verdict sentence must always be heard
        lines[-1] = explainer_mod.CheckedLine(
            speaker="alfii",
            text=explainer_mod.VERDICT_TEMPLATES[consensus.verdict],
            blocked_reason=lines[-1].blocked_reason,
        )
    pool = [r for q in [*questions, *candidate_qs] if (r := explainer_mod.render_question(q, facts, quote_text, mode))]
    final_questions = list(dict.fromkeys(pool))[:3]

    # 13 save -----------------------------------------------------------------------------------------------------
    lines = [opening, *lines]
    for i, ln in enumerate(lines, start=1):
        repo.add_spoken_line(case_id, ln.speaker, i, ln.text, allowed=ln.allowed, blocked_reason=ln.blocked_reason)
    sentence = lines[-1].text
    repo.save_verdict(
        case_id,
        consensus.verdict,
        score=consensus.score,
        disagreement=consensus.disagreement,
        overrides=[o.model_dump() for o in consensus.overrides],
        sentence=sentence,
        questions=final_questions,
        degraded=bool(run.degraded_steps),
    )
    if consensus.verdict == "red" or (
        consensus.verdict == "yellow" and (computed.commitment or 0) >= ALERT_YELLOW_MIN_COMMITMENT
    ):
        repo.create_alert(
            case_id, inp.family_id, f"{consensus.verdict.upper()}: {case_type.replace('_', ' ')}: {sentence}"
        )
    return CaseResult(
        case_id=case_id,
        case_type=case_type,
        verdict=VerdictOut(colour=consensus.verdict, sentence=sentence, questions=final_questions),
        called_agents=agents,
        spoken_lines=[SpokenLineOut(speaker=ln.speaker, text=ln.text) for ln in lines],
        screen_details=_screen_details(facts, terms, case_type),
        privacy_mode=mode,
        degraded=bool(run.degraded_steps),
        degraded_steps=list(run.degraded_steps),
        llm_calls=0,
    )


def _stock_symbol(draft: CaseDraft, transcript: str, doc_text: str) -> str | None:
    """The builder's ticker if we have its history; else a known ticker named in the question or documents."""
    if draft.stock_symbol and tools.stocks_get_history(draft.stock_symbol)["found"]:
        return draft.stock_symbol
    return tools.find_known_symbol(f"{transcript}\n{doc_text}") or draft.stock_symbol


def _vote(case_type: str, rnd: council_mod.CouncilRound) -> tuple[float, float]:
    c = run_consensus(case_type, rnd.positions)
    return c.score, c.disagreement


def _json(obj: Any) -> str:
    import json

    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def _scam_result(run: _Run, signals: list[ScamSignal], mode: str, repo: Repo, family_id: int) -> CaseResult:
    repo.update_case(run.case_id, case_type="scam_or_payment_request")
    lines = [("alfii", "Stop. Please do not do what this person is asking.")]
    lines += [("alfii", s.explanation) for s in signals[:2]]
    lines.append(("alfii", SCAM_SENTENCE))
    for i, (speaker, text) in enumerate(lines, start=1):
        repo.add_spoken_line(run.case_id, speaker, i, text)
    consensus = run_consensus("scam_or_payment_request", [], override_inputs_from_facts([], scam=True))
    questions = ["Hang up and call the number printed on your bank card or passbook."]
    repo.save_verdict(
        run.case_id,
        consensus.verdict,
        score=0,
        disagreement=0,
        overrides=[o.model_dump() for o in consensus.overrides],
        sentence=SCAM_SENTENCE,
        questions=questions,
        degraded=bool(run.degraded_steps),
    )
    repo.create_alert(
        run.case_id, family_id, f"RED: scam warning: {', '.join(s.rule for s in signals) or 'payment request'}"
    )
    return CaseResult(
        case_id=run.case_id,
        case_type="scam_or_payment_request",
        verdict=VerdictOut(colour="red", sentence=SCAM_SENTENCE, questions=questions),
        called_agents=[],
        spoken_lines=[SpokenLineOut(speaker=s, text=t) for s, t in lines],
        screen_details=[
            ScreenDetail(
                id=f"scam.{s.rule}",
                label=s.explanation,
                value=s.matched_text,
                kind="offer",
                source="Warning sign in " + ("what you said" if s.source == "transcript" else "the document"),
            )
            for s in signals
        ],
        privacy_mode=mode,
        degraded=bool(run.degraded_steps),
        degraded_steps=list(run.degraded_steps),
        llm_calls=0,
    )  # type: ignore[arg-type]


def _simple_result(run: _Run, case_type: str, colour: Any, sentence: str, mode: str, repo: Repo) -> CaseResult:
    repo.add_spoken_line(run.case_id, "alfii", 1, sentence)
    return CaseResult(
        case_id=run.case_id,
        case_type=case_type,
        verdict=VerdictOut(colour=colour, sentence=sentence),
        called_agents=[],
        spoken_lines=[SpokenLineOut(speaker="alfii", text=sentence)],
        screen_details=[],
        privacy_mode=mode,
        degraded=bool(run.degraded_steps),
        degraded_steps=list(run.degraded_steps),
        llm_calls=0,
    )  # type: ignore[arg-type]
