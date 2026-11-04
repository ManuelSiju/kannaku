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

import hashlib
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
from app.pipeline import questions as questions_mod
from app.pipeline.claims import ClaimCheck, check_claims, mentioned
from app.pipeline.compute import Computed, compute_facts
from app.pipeline.consensus import ConsensusResult, override_inputs_from_facts, run_consensus
from app.pipeline.events import BUS, DONE, EventBus
from app.pipeline.flags import routing_flags
from app.pipeline.ingest import Ingested, Upload, ingest
from app.pipeline.labels import source_label, unverified_label
from app.pipeline.privacy import decide_mode
from app.pipeline.router import route
from app.pipeline.scam_rules import ScamSignal, detect
from app.pipeline.schemas import (
    CaseDraft,
    CaseResult,
    ClaimOut,
    CouncilLine,
    ScreenDetail,
    ShortAnswer,
    SpokenLineOut,
    VerdictOut,
)
from app.pipeline.templates import NOTES, SCAM_SHORT, followups, lang_of, opener, t
from app.pipeline.verify_terms import EvidenceText, VerifiedTerm, verify_terms
from app.prompts import prompts
from app.providers.llm import AskBudget, LLMProvider, LLMStepFailed, use_budget, use_step
from app.providers.stt import STTProvider

log = logging.getLogger(__name__)

ALERT_YELLOW_MIN_COMMITMENT = 25_000
COUNCIL_WORD_BUDGET = 110  # about 45 s of speech at 150 words a minute
WORDS_PER_MINUTE = 150
# A red conclusion must say no plainly: "do not sign without written guarantees" invites signing once the paper comes.
RED_NO = re.compile(r"\b(do not|don't|dont|not go ahead|avoid|stop|never|say no)\b", re.I)
RED_LOOPHOLE = re.compile(r"\b(without|unless|until|carefully|first compare|more facts|more details)\b", re.I)
# Categories a stored paper can pass on to a later question (not "unknown", not out of scope).
DOCUMENT_TYPES = {"insurance_offer", "ulip", "loan_offer", "sip_or_fund_question", "stock_tip", "shares", "ipo",
                  "chit_fund", "scam_or_payment_request"}  # fmt: skip
# The model's own "ask them ..." sentences are removed from Alfii's conclusion: questions come only from the bank.
MODEL_ASK = re.compile(r"\bask(?:s|ed|ing)?\b|\bquestions?\b|ചോദിക്ക|पूछ", re.I)
ACTION_CUES = re.compile(r"\b(ask|wait|talk to|show me|call|do not sign|don't sign|before you)\b", re.I)
CONTEXT_CUES = re.compile(
    r"\b(?:he|she|they) (?:says|said|is saying|is asking|wants)\b|\bthe agent is here\b|\b(?:agent|man|lady|he|she)"
    r" is (?:here|sitting|with me)\b|\bsitting (?:here )?with me\b|\bwith me now\b",
    re.I,
)


class AskInput(BaseModel):
    family_id: int
    text: str | None = None
    audio: Upload | None = None
    files: list[Upload] = []
    earphones: bool = False
    user_says_alone: bool = False
    request_id: str = ""


LLM_STEPS = ("case_builder", "council", "debate", "explainer")


class _Run:
    def __init__(self, case_id: int, repo: Repo, bus: EventBus, settings: Settings) -> None:
        self.case_id, self.repo, self.bus, self.settings = case_id, repo, bus, settings
        self.degraded_steps: list[str] = []

    @asynccontextmanager
    async def step(self, name: str, **detail: Any) -> AsyncIterator[dict[str, Any]]:
        """Times the step, records the trace, publishes events. LLM/tool failures mark the step degraded and are
        swallowed so later steps still run with what is known."""
        info: dict[str, Any] = dict(detail)
        if self.settings.meta and name in LLM_STEPS:
            info["reasoning_effort"] = self.settings.reasoning_effort(name)
        self.bus.publish(self.case_id, "step_started", step=name)
        t0, outcome = time.perf_counter(), "ok"
        try:
            with use_step(name):
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
    for tm in terms:
        if not tm.verified:
            out.append(
                ScreenDetail(
                    id=f"term.{tm.name}",
                    label=f"Could not check: {tm.name.replace('_', ' ')}",
                    value=tm.value_text,
                    kind="offer",
                    source=unverified_label(tm.source, tm.reason, case_type),
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
    run = _Run(case_id, repo, bus, settings)
    provider = settings.llm_provider
    models = {"text": settings.llm_model, "vision": settings.llm_vision_model or settings.llm_model}
    if not settings.llm_vision_enabled:
        models["vision"] = ""
    repo.add_trace(
        case_id, "request", 0.0, "ok", {"request_id": inp.request_id, "provider": provider, "models": models}
    )
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
    result.provider = "local fallback" if budget.fallback_used else provider
    if budget.replay_at:
        result.provider = f"replay of recorded Meta call {budget.replay_at}"
        repo.add_trace(case_id, "replay", 0.0, "ok", {"provider": result.provider})
    result.local_fallback = budget.fallback_used
    result.request_id = inp.request_id
    if budget.fallback_used or budget.cache_hits or budget.retries:
        repo.add_trace(
            case_id,
            "llm_provider",
            0.0,
            "degraded" if budget.fallback_used else "ok",
            {
                "local_fallback": budget.fallback_used,
                "cache_hits": budget.cache_hits,
                "retries": budget.retries,
                "reason": "Meta daily call cap reached; LLM_FALLBACK=local" if budget.fallback_used else "",
            },
        )
    repo.update_case(case_id, status="done", result_json=result.model_dump_json())
    bus.publish(case_id, DONE, verdict=result.verdict.colour, degraded=result.degraded)
    return result


async def _pipeline(run: _Run, inp: AskInput, *, repo: Repo, llm: LLMProvider, stt: STTProvider | None) -> CaseResult:
    case_id = run.case_id
    prior = repo.get_case(case_id) or {}
    family = repo.get_family(inp.family_id) or {}
    lang = lang_of(family.get("language"))
    guardian = next((m["name"] for m in repo.members(inp.family_id) if m["role"] == "guardian"), None)

    # 1 ingest -------------------------------------------------------------------------------------------
    ing = Ingested(transcript=inp.text or "", language=None, pages=[])
    async with run.step("ingest") as info:
        ing = await ingest(text=inp.text, audio=inp.audio, files=inp.files, stt=stt)
        info.update(pages=len(ing.pages), transcript_chars=len(ing.transcript), problems=ing.problems, stt=ing.stt)
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
    repo.update_case(case_id, privacy_mode=mode, language=lang)
    if inp.audio is not None and not ing.transcript.strip() and not ing.pages:  # silence or noise: no model call
        return _simple_result(run, "unknown", t(lang, "no_speech"), mode, repo, lang)

    # papers this family showed before: this session's and earlier ones (same file = same content hash)
    uploads = [(f.filename, hashlib.sha256(f.data).hexdigest()) for f in inp.files]
    known_docs = repo.family_documents(inp.family_id)
    session_docs = [d for d in known_docs if d["case_id"] == case_id]
    same_files = [d for d in known_docs if d["sha256"] in {h for _, h in uploads}]

    def remember(doc_type: str, terms: dict[str, str] | None = None) -> None:
        for filename, digest in uploads:
            repo.remember_document(inp.family_id, case_id, filename, digest, doc_type, terms)

    # 2 scam rules (fast path) -------------------------------------------------------------------------------
    signals: list[ScamSignal] = []
    async with run.step("scam_rules") as info:
        signals = detect(transcript, ing.doc_text)
        info["signals"] = [s.model_dump() for s in signals]
    if signals:
        remember("scam_or_payment_request")
        return _scam_result(run, signals, mode, repo, inp.family_id, lang)

    # 3 case builder (LLM 1; a failed vision call falls back to the OCR text) --------------------------------
    draft = CaseDraft(case_type="unknown")
    vision_read = False
    async with run.step("case_builder") as info:
        case_input: dict[str, Any] = {
            "question": transcript,
            "pages": [{"source": p.source, "text": p.text} for p in ing.pages],
        }
        if session_docs or same_files:
            case_input["known_documents"] = [
                {"filename": d["filename"], "type": d["doc_type"]} for d in [*session_docs, *same_files]
            ]
        user = _json(case_input)
        images = ing.images if getattr(getattr(llm, "settings", None), "llm_vision_enabled", False) else []
        if images:
            try:
                draft, usage = await llm.chat_json(prompts.CASE_BUILDER, user, CaseDraft, images=images)
                vision_read = True
            except LLMStepFailed as e:
                info["vision_failed"] = str(e)
                info["degraded"] = True  # photos read once (OCR only)
                draft, usage = await llm.chat_json(prompts.CASE_BUILDER, user, CaseDraft)
        else:
            draft, usage = await llm.chat_json(prompts.CASE_BUILDER, user, CaseDraft)
        info.update(
            case_type=draft.case_type,
            terms=len(draft.terms),
            vision_read=vision_read,
            ms_llm=usage.ms,
            tokens=[usage.prompt_tokens, usage.completion_tokens],
        )
    # A paper already categorised keeps its category when the model cannot place the question (a short follow-up, or
    # the same file sent again): the type recorded for it is used instead of asking "is this a loan or a policy?".
    stored = next((d["doc_type"] for d in [*same_files, *session_docs] if d["doc_type"] in DOCUMENT_TYPES), None)
    if stored and draft.case_type in ("unknown", "general_money"):
        repo.add_trace(case_id, "document_type", 0.0, "ok", {"model_said": draft.case_type, "used": stored})
        draft = draft.model_copy(update={"case_type": stored})
    flags, case_type, flag_why = routing_flags(draft, evidence)  # market_linked only with document support
    repo.update_case(case_id, case_type=case_type)
    remember(case_type)

    if case_type == "unknown":  # Alfii asks one clarifying question; no council, no extra LLM call
        return _simple_result(run, case_type, t(lang, "clarify"), mode, repo, lang)
    if case_type == "out_of_scope":
        return _simple_result(
            run, case_type, t(lang, "out_of_scope"), mode, repo, lang, suggested=followups("out_of_scope", lang)
        )
    if case_type == "scam_or_payment_request":
        return _scam_result(run, [], mode, repo, inp.family_id, lang)

    # 4 verify terms -----------------------------------------------------------------------------------------
    terms: list[VerifiedTerm] = []
    async with run.step("verify_terms") as info:
        terms = verify_terms(draft.terms, evidence, vision_read=vision_read)
        for tm in terms:
            ev_id = int(tm.quote_id[1:]) if tm.quote_id else None
            repo.add_term(
                case_id, tm.name, tm.value, tm.unit, evidence_id=ev_id, verified=tm.verified, reason=tm.reason
            )
        info["unverified"] = [tm.name for tm in terms if not tm.verified]
        info["readings"] = {tm.name: tm.reading for tm in terms if tm.verified}

    # 5 compute facts ------------------------------------------------------------------------------------------
    computed = Computed(facts=[], missing_required=[], flags=[], commitment=None)
    async with run.step("compute") as info:
        symbol = _stock_symbol(draft, transcript, ing.doc_text)
        computed = compute_facts(case_type, terms, inp.family_id, repo, stock_symbol=symbol, flags=flags)
        info.update(facts=[f.id for f in computed.facts], missing_required=computed.missing_required)
    facts = computed.facts
    repo.save_facts(case_id, facts)
    remember(case_type, {tm.name: tm.display for tm in terms if tm.verified})
    claims: list[ClaimCheck] = check_claims(draft.seller_claims, facts, quotes, case_type)

    # 6 router ---------------------------------------------------------------------------------------------------
    agents = route(case_type, computed.flags)
    async with run.step("router") as info:
        info.update(
            case_type=case_type,
            flags=computed.flags,
            agents=agents,
            market_linked=flag_why,
            claims=[c.model_dump() for c in claims],
        )
    opening = explainer_mod.CheckedLine(speaker="alfii", text=opener(agents, lang), kind="opener")
    run.bus.publish(case_id, "alfii_opener", text=opening.text)  # spoken while the council works; no LLM
    for a in agents:
        run.bus.publish(case_id, "agent_called", agent=a)

    unverified = sorted({*computed.missing_required, *(tm.name for tm in terms if not tm.verified)})
    summary = {
        "case_type": case_type,
        "question": transcript,
        "family_documents": [
            {"filename": d["filename"], "type": d["doc_type"], "times_seen": d["times_seen"]}
            for d in repo.family_documents(inp.family_id, limit=5)
        ],
        "verified_terms": [
            {"name": tm.name, "value": tm.display, "quote_id": tm.quote_id} for tm in terms if tm.verified
        ],
        "unverified_terms": unverified,
        "seller_claims": [c.model_dump() for c in draft.seller_claims],
        "claim_checks": [c.model_dump(include={"claim", "status", "evidence_ids", "evidence"}) for c in claims],
    }
    # discreet: the council and the explainer never see the family's own figures
    shared_facts = facts if mode == "full" else [f for f in facts if f.kind != "personal"]

    # 7-9 council, evidence, debate ------------------------------------------------------------------------------
    rounds: list[council_mod.CouncilRound] = []
    if agents:
        payload = council_mod.council_input(summary, shared_facts, quotes, agents)
        async with run.step("council", agents=agents) as info:
            first, _ = await council_mod.run_council(llm, payload, agents, shared_facts, quote_text)
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
                    second, _ = await council_mod.run_debate(llm, payload, rounds[0], agents, shared_facts, quote_text)
                    rounds.append(second)
                    info.update(
                        dropped=[a.drop_reason for a in second.arguments if not a.kept],
                        auto_placeholder=[x for a in second.arguments for x in a.fixes],
                    )
    final = rounds[-1] if rounds else None
    for r in rounds:
        for pos in r.positions:
            repo.add_position(case_id, pos.agent, pos.stance, pos.strength, round=r.round)
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
    kept_args = [
        a.model_dump(include={"agent", "text", "cited_ids"}) for a in (final.arguments if final else []) if a.kept
    ]
    if len(rounds) > 1:  # agents the debate did not answer keep their round-1 arguments
        kept_args += [
            a.model_dump(include={"agent", "text", "cited_ids"})
            for a in rounds[0].arguments
            if a.kept and a.agent not in {k["agent"] for k in kept_args}
        ]
    # questions come from the code's bank for this case type: missing terms and contradicted claims first
    bank = questions_mod.candidates(case_type, unverified, claims, lang)
    if any(tm.name == "reducing_rate" and tm.verified for tm in terms):  # it was already told
        bank = [q for q in bank if q.id != "loan_reducing_rate"]
    agent_lines: list[explainer_mod.CheckedLine] = []
    notes: list[explainer_mod.CheckedLine] = []
    conclusion: explainer_mod.CheckedLine | None = None
    model_questions: list[tuple[str, str]] = []
    explained = False
    async with run.step("explainer") as info:
        payload = explainer_mod.explainer_input(
            consensus.verdict,
            summary,
            agents,
            kept_args,
            council_mod.facts_table(shared_facts),
            [{"id": k, **v} for k, v in quotes.items()],
            mode,
            lang,
            [{"id": q.id, "text": q.text} for q in bank],
            claims=summary["claim_checks"],
        )
        ex = await explainer_mod.explain(
            llm, payload, facts, quote_text, mode, agents=agents, kept_args=kept_args, lang=lang
        )
        agent_lines, notes, conclusion, model_questions = ex.agent_lines, ex.notes, ex.verdict, ex.questions
        explained = True
        info.update(
            rewrite_used=ex.rewrite_used,
            auto_placeholder=ex.fixes,
            lint=ex.lint_rejections,
            dropped_turns=ex.dropped_turns,
            notes=[n.text for n in ex.notes],
        )
    if not explained:
        agent_lines, notes = explainer_mod.fallback_turns(agents, kept_args, facts, quote_text, mode, lang)
    if mode == "full":
        agent_lines = _say_held_shares(agent_lines, facts, lang)

    # questions said aloud (the bank only; the model's picks and rewordings are checked) --------------------------
    picked = questions_mod.pick(case_type, bank, model_questions, facts, mode, lang)
    final_questions = [q.text for q in picked.questions]
    async with run.step("questions") as info:
        info.update(
            bank=[q.id for q in bank],
            picked=[q.id for q in picked.questions],
            reworded=picked.reworded,
            rejected=picked.rejected,
        )

    # Alfii's conclusion always ends with one next step ------------------------------------------------------------
    from app.pipeline.lint import sentences

    verdict_text = conclusion.text if conclusion else t(lang, consensus.verdict)
    parts = sentences(verdict_text)
    if (
        consensus.verdict == "red"
        and lang == "en"
        and (not parts or not RED_NO.search(parts[0]) or RED_LOOPHOLE.search(parts[0]))
    ):
        parts = [t(lang, "red"), *parts[1:]]
    parts = parts[:1] + [p for p in parts[1:] if not MODEL_ASK.search(p)]
    verdict_text = " ".join(parts) or t(lang, consensus.verdict)
    if not ACTION_CUES.search(verdict_text):
        verdict_text = f"{verdict_text} {_next_step(consensus.verdict, picked.questions, guardian, lang)}"
    closing = explainer_mod.CheckedLine(speaker="alfii", text=verdict_text, kind="conclusion")

    # contradicted claims must be mentioned (code line if the agents did not) -----------------------------------
    said = [ln.text for ln in agent_lines] + [verdict_text]
    claim_lines = [
        explainer_mod.CheckedLine(speaker="alfii", text=_claim_line(c, case_type, lang), kind="claim")
        for c in claims
        if c.status == "contradicted" and not mentioned(c, said)
    ]

    # rebuttals (only if the debate ran), then the word budget ------------------------------------------------------
    rebuttals = _rebuttals(rounds, agent_lines, facts, quote_text, mode, lang)
    council = _fit_budget([opening, *agent_lines, *rebuttals, *notes, *claim_lines, closing])
    words = sum(len(ln.text.split()) for ln in council)

    # 13 save -----------------------------------------------------------------------------------------------------
    for i, ln in enumerate(council, start=1):
        repo.add_spoken_line(case_id, ln.speaker, i, ln.text, allowed=ln.allowed, blocked_reason=ln.blocked_reason)
    repo.save_verdict(
        case_id,
        consensus.verdict,
        score=consensus.score,
        disagreement=consensus.disagreement,
        overrides=[o.model_dump() for o in consensus.overrides],
        sentence=verdict_text,
        questions=final_questions,
        degraded=bool(run.degraded_steps),
    )
    if consensus.verdict == "red" or (
        consensus.verdict == "yellow" and (computed.commitment or 0) >= ALERT_YELLOW_MIN_COMMITMENT
    ):
        repo.create_alert(
            case_id, inp.family_id, f"{consensus.verdict.upper()}: {case_type.replace('_', ' ')}: {verdict_text}"
        )
    return CaseResult(
        case_id=case_id,
        case_type=case_type,
        verdict=VerdictOut(colour=consensus.verdict, sentence=verdict_text, questions=final_questions),
        called_agents=agents,
        spoken_lines=[SpokenLineOut(speaker=ln.speaker, text=ln.text) for ln in council],
        screen_details=_personal_notes(case_type, facts, lang) + _screen_details(facts, terms, case_type),
        privacy_mode=mode,
        degraded=bool(run.degraded_steps),
        degraded_steps=list(run.degraded_steps),
        llm_calls=0,
        language=lang,
        short_answer=ShortAnswer(
            text=_short(conclusion.text if conclusion else "", consensus.verdict, lang), colour=consensus.verdict
        ),
        council=[CouncilLine(speaker=ln.speaker, text=ln.text, kind=ln.kind) for ln in council],  # type: ignore[arg-type]
        council_words=words,
        council_seconds=round(words / WORDS_PER_MINUTE * 60, 1),
        suggested_followups=followups(case_type, lang),
        claims=[ClaimOut(**c.model_dump(include={"claim", "status", "evidence_ids", "evidence"})) for c in claims],
    )


def _next_step(colour: str, questions: list[questions_mod.Question], guardian: str | None, lang: str) -> str:
    if colour == "red":
        return t(lang, "next_guardian", guardian=guardian) if guardian else t(lang, "next_wait")
    if questions:
        q = questions[0]
        key = {"self": "next_ask_self", "sender": "next_ask_sender"}.get(q.audience, "next_ask")
        return t(lang, key, question=q.text)
    return t(lang, "next_paper") if colour == "yellow" else t(lang, "next_wait")


def _clip(text: str, n: int) -> str:
    words = text.split()
    return " ".join(words[:n]) + ("…" if len(words) > n else "")


def _claim_line(c: ClaimCheck, case_type: str, lang: str) -> str:
    source = t(lang, "claim_source_brochure" if case_type in ("insurance_offer", "ulip") else "claim_source_doc")
    return t(lang, "claim", claim=_clip(c.claim, 8), source=source, evidence=_clip(c.evidence, 12))


def _rebuttals(
    rounds: list[council_mod.CouncilRound],
    agent_lines: list[explainer_mod.CheckedLine],
    facts: list[Fact],
    quote_text: dict[str, str],
    mode: str,
    lang: str,
) -> list[explainer_mod.CheckedLine]:
    """If the debate ran: one round-2 point per agent that says something new, held to every spoken-line check."""
    if len(rounds) < 2:
        return []
    from app.pipeline.schemas import Line

    said = {ln.speaker: ln.screen_text for ln in agent_lines}
    out = []
    for a in dict.fromkeys(x.agent for x in rounds[1].arguments if x.kept):
        arg = next(x for x in rounds[1].arguments if x.kept and x.agent == a)
        if arg.rendered == said.get(a):
            continue
        c = explainer_mod.check_line(
            Line(speaker=a, text=arg.text, cited_ids=arg.cited_ids), facts, quote_text, mode, lang=lang
        )  # type: ignore[arg-type]
        if c.problem is None:
            out.append(explainer_mod.CheckedLine(speaker=a, text=c.spoken, screen_text=c.screen, kind="rebuttal"))
    return out


def _say_held_shares(
    lines: list[explainer_mod.CheckedLine], facts: list[Fact], lang: str
) -> list[explainer_mod.CheckedLine]:
    """Vick always says how many of the tipped shares the family holds. Code writes it when the model left it out,
    first in his turn so that the word budget cannot cut it."""
    from app.pipeline.lint import sentences

    held = next((f for f in facts if f.id == "tip.held_shares"), None)
    if held is None or held.value is None:
        return lines
    n = f"{held.value:g}"
    said = t(lang, "held_shares", n=n)
    vick = next((x for x in lines if x.speaker == "vick"), None)
    if vick is None:
        return [explainer_mod.CheckedLine(speaker="vick", text=said, screen_text=said, cited_ids=[held.id]), *lines]
    if re.search(rf"(?<![\d,.]){n}(?![\d,])", vick.text):
        return lines
    first = sentences(vick.text)[0]
    update = {"text": f"{said} {first}", "screen_text": f"{said} {sentences(vick.screen_text or vick.text)[0]}"}
    update["cited_ids"] = [*vick.cited_ids, held.id]  # type: ignore[assignment]
    return [vick.model_copy(update=update) if x is vick else x for x in lines]


def _fit_budget(lines: list[explainer_mod.CheckedLine]) -> list[explainer_mod.CheckedLine]:
    """Keep the council under COUNCIL_WORD_BUDGET words: drop rebuttals first, then cut agent lines to one sentence.
    The opener, notes, claim corrections and the conclusion always stay."""
    from app.pipeline.lint import sentences

    def words(ls: list[explainer_mod.CheckedLine]) -> int:
        return sum(len(x.text.split()) for x in ls)

    lines = list(lines)
    while words(lines) > COUNCIL_WORD_BUDGET and any(x.kind == "rebuttal" for x in lines):
        idx = max(i for i, x in enumerate(lines) if x.kind == "rebuttal")
        lines.pop(idx)
    if words(lines) > COUNCIL_WORD_BUDGET:
        lines = [x.model_copy(update={"text": sentences(x.text)[0]}) if x.kind == "agent" else x for x in lines]
    return lines


def _short(conclusion: str, colour: str | None, lang: str) -> str:
    """One sentence for the default reply. Red is always the plain template: a red answer must not be conditional."""
    from app.pipeline.lint import sentences

    if colour == "red":
        return t(lang, "short_red")
    first = sentences(conclusion)[0] if conclusion.strip() else ""
    if first and len(first.split()) <= 20:
        return first
    return t(lang, f"short_{colour}") if colour else t(lang, "clarify")


def _personal_notes(case_type: str, facts: list[Fact], lang: str) -> list[ScreenDetail]:
    """Code-written on-screen notes about the family's own money (never spoken in discreet mode)."""
    by_id = {f.id: f for f in facts}
    out = []
    for key, fid in NOTES.get(case_type, []):
        f = by_id.get(fid)
        if f is None or f.value is None:
            continue
        out.append(
            ScreenDetail(
                id=f"note.{fid}",
                label=t(lang, key, **{fid: f.display}),
                value=f.display,
                kind="personal",
                source="Kanakku note · only on your screen",
            )
        )
    return out


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


def _scam_result(
    run: _Run, signals: list[ScamSignal], mode: str, repo: Repo, family_id: int, lang: str = "en"
) -> CaseResult:
    """Calm, three short lines: you did right, why it is a trick, what to do."""
    repo.update_case(run.case_id, case_type="scam_or_payment_request")
    why = SCAM_SHORT[lang_of(lang)].get(signals[0].rule) if signals else None
    texts = [t(lang, "scam_right"), why or t(lang, "scam_generic"), t(lang, "scam_action")]
    for i, text in enumerate(texts, start=1):
        repo.add_spoken_line(run.case_id, "alfii", i, text)
    consensus = run_consensus("scam_or_payment_request", [], override_inputs_from_facts([], scam=True))
    sentence = texts[-1]
    repo.save_verdict(
        run.case_id,
        consensus.verdict,
        score=0,
        disagreement=0,
        overrides=[o.model_dump() for o in consensus.overrides],
        sentence=sentence,
        questions=[],
        degraded=bool(run.degraded_steps),
    )
    repo.create_alert(
        run.case_id, family_id, f"RED: scam warning: {', '.join(s.rule for s in signals) or 'payment request'}"
    )
    kinds = ["opener", "agent", "conclusion"]
    council = [CouncilLine(speaker="alfii", text=x, kind=k) for x, k in zip(texts, kinds, strict=True)]  # type: ignore[arg-type]
    words = sum(len(x.split()) for x in texts)
    return CaseResult(
        case_id=run.case_id,
        case_type="scam_or_payment_request",
        verdict=VerdictOut(colour="red", sentence=sentence, questions=[]),
        called_agents=[],
        spoken_lines=[SpokenLineOut(speaker="alfii", text=x) for x in texts],
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
        privacy_mode=mode,  # type: ignore[arg-type]
        degraded=bool(run.degraded_steps),
        degraded_steps=list(run.degraded_steps),
        llm_calls=0,
        language=lang,
        short_answer=ShortAnswer(text=texts[1], colour="red"),
        council=council,
        council_words=words,
        council_seconds=round(words / WORDS_PER_MINUTE * 60, 1),
        suggested_followups=followups("scam_or_payment_request", lang),
    )


def _simple_result(
    run: _Run,
    case_type: str,
    sentence: str,
    mode: str,
    repo: Repo,
    lang: str = "en",
    suggested: list[str] | None = None,
) -> CaseResult:
    repo.add_spoken_line(run.case_id, "alfii", 1, sentence)
    words = len(sentence.split())
    return CaseResult(
        case_id=run.case_id,
        case_type=case_type,
        verdict=VerdictOut(colour=None, sentence=sentence),
        called_agents=[],
        spoken_lines=[SpokenLineOut(speaker="alfii", text=sentence)],
        screen_details=[],
        privacy_mode=mode,  # type: ignore[arg-type]
        degraded=bool(run.degraded_steps),
        degraded_steps=list(run.degraded_steps),
        llm_calls=0,
        language=lang,
        short_answer=ShortAnswer(text=sentence, colour=None),
        council=[CouncilLine(speaker="alfii", text=sentence, kind="conclusion")],
        council_words=words,
        council_seconds=round(words / WORDS_PER_MINUTE * 60, 1),
        suggested_followups=suggested or [],
    )
