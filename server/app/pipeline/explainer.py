"""Step 12: what the called agents say aloud, and Alfii's verdict sentence. Alfii's opener, budget notes, claim
corrections and next steps are code templates (see run.py / templates.py).

Every line: numbers only as {fact_id} placeholders (filled in by code: digits on screen, Indian number words in
speech), evidence check (no raw digits, known ids, comparison words backed by cmp_* facts), privacy check (numbers AND
personal words in discreet mode) and the speaking-style linter. Failing lines are regenerated once (if the LLM
budget allows). Then an agent falls back to its own checked council argument; if that fails too its turn is dropped,
and if privacy was the reason Alfii says the agent left a note on the screen. An agent line is never a bare fallback
sentence.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from app.engines.fact import Fact
from app.pipeline.consensus import Colour
from app.pipeline.evidence import Dropped, Kept, check_argument, placeholders, raw_number
from app.pipeline.lint import lint
from app.pipeline.privacy import PrivacyMode, speech_allowed
from app.pipeline.schemas import ExplainerOutput, Line, RewriteOutput
from app.pipeline.templates import LANG_NAMES, name, t
from app.prompts import prompts
from app.providers.llm import LLMProvider, current_budget


class CheckedLine(BaseModel):
    speaker: str
    text: str  # spoken form (Indian number words)
    screen_text: str = ""  # screen form (digits)
    cited_ids: list[str] = []
    allowed: bool = True
    blocked_reason: str | None = None
    kind: str = "agent"  # opener | agent | rebuttal | note | claim | conclusion


class LineCheck(BaseModel):
    problem: str | None
    spoken: str
    screen: str
    cited: list[str] = []
    fixes: list[str] = []
    lint: list[str] = []


class Explained(BaseModel):
    agent_lines: list[CheckedLine]
    notes: list[CheckedLine]  # Alfii: "<Agent> has left a note about your budget on your screen."
    verdict: CheckedLine | None  # None -> the caller uses the verdict template
    questions: list[str]
    rewrite_used: bool
    fixes: list[str]
    lint_rejections: list[str]
    dropped_turns: list[str]


def check_line(
    line: Line,
    facts: list[Fact],
    quotes: dict[str, str],
    mode: PrivacyMode,
    *,
    lang: str = "en",
    comparisons: bool = True,
    style: bool = True,
) -> LineCheck:
    spoken = screen = line.text
    cited, fixes = list(line.cited_ids), []
    if placeholders(line.text) or raw_number(line.text) or line.cited_ids or comparisons:
        res = check_argument(line.text, line.cited_ids, facts, quotes, comparisons=comparisons, lang=lang)
        fixes = res.fixes
        if isinstance(res, Dropped):
            if res.reason != "no evidence cited":
                return LineCheck(problem=f"evidence: {res.reason}", spoken=spoken, screen=screen, fixes=fixes)
        elif isinstance(res, Kept):
            spoken, screen, cited = res.spoken, res.rendered, res.cited
    priv = speech_allowed(f"{screen}\n{spoken}", cited, facts, mode)
    if not priv.allowed:
        return LineCheck(problem=f"privacy: {priv.reason}", spoken=spoken, screen=screen, cited=cited, fixes=fixes)  # type: ignore[union-attr]
    rules = lint(spoken, line.text) if style else []
    if rules:
        return LineCheck(
            problem=f"lint: {', '.join(rules)}", spoken=spoken, screen=screen, cited=cited, fixes=fixes, lint=rules
        )
    return LineCheck(problem=None, spoken=spoken, screen=screen, cited=cited, fixes=fixes)


def render_question(
    q: str, facts: list[Fact], quotes: dict[str, str], mode: PrivacyMode, lang: str = "en"
) -> str | None:
    """Questions are said aloud to the seller: same checks, no comparison rule, under 12 words."""
    c = check_line(Line(speaker="alfii", text=q), facts, quotes, mode, lang=lang, comparisons=False, style=False)
    if c.problem or len(c.spoken.split()) >= 12:
        return None
    return c.spoken


def explainer_input(
    colour: Colour | None,
    summary: dict[str, Any],
    agents: list[str],
    kept_args: list[dict[str, Any]],
    facts_table: list[dict[str, Any]],
    quotes: list[dict[str, str]],
    mode: PrivacyMode,
    language: str,
    questions: list[str],
    claims: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "verdict_colour": colour,
        "case": summary,
        "called_agents": agents,
        "arguments": kept_args,
        "facts": facts_table,
        "quotes": quotes,
        "claim_checks": claims or [],
        "privacy_mode": mode.upper(),
        "language": LANG_NAMES.get(language, "English"),
        "candidate_questions": questions,
    }


async def explain(
    llm: LLMProvider,
    payload: dict[str, Any],
    facts: list[Fact],
    quotes: dict[str, str],
    mode: PrivacyMode,
    *,
    agents: list[str],
    kept_args: list[dict[str, Any]],
    lang: str = "en",
) -> Explained:
    out, _ = await llm.chat_json(
        prompts.EXPLAINER, json.dumps(payload, separators=(",", ":"), ensure_ascii=False), ExplainerOutput
    )
    # one line per called agent (first one wins), then the verdict
    by_agent: dict[str, Line] = {}
    for ln in out.agent_lines:
        if ln.speaker in agents and ln.speaker not in by_agent:
            by_agent[ln.speaker] = ln
    slots: list[tuple[str, Line]] = [(a, by_agent[a]) for a in agents if a in by_agent]
    slots.append(("verdict", out.verdict_sentence.model_copy(update={"speaker": "alfii"})))

    fixes: list[str] = []
    lint_rejections: list[str] = []
    results: dict[str, LineCheck] = {}
    first_problem: dict[str, str] = {}
    for key, ln in slots:
        c = check_line(ln, facts, quotes, mode, lang=lang)
        results[key] = c
        fixes += c.fixes
        lint_rejections += c.lint
        if c.problem:
            first_problem[key] = c.problem

    failing = [k for k, _ in slots if results[k].problem]
    rewrite_used = False
    budget = current_budget()
    if failing and (budget is None or budget.used < budget.max_calls):
        rewrite_used = True
        lines = dict(slots)
        req = {
            "privacy_mode": mode.upper(),
            "language": LANG_NAMES.get(lang, "English"),
            "lines": [
                {"index": i, **lines[k].model_dump(), "problem": results[k].problem} for i, k in enumerate(failing)
            ],
            "facts": payload["facts"],
            "quotes": payload["quotes"],
        }
        try:
            fixed, _ = await llm.chat_json(
                prompts.REWRITE, json.dumps(req, separators=(",", ":"), ensure_ascii=False), RewriteOutput
            )
            for k, new in zip(failing, fixed.lines, strict=False):
                new = new.model_copy(update={"speaker": lines[k].speaker})
                c = check_line(new, facts, quotes, mode, lang=lang)
                fixes += c.fixes
                lint_rejections += c.lint
                if c.problem is None:
                    results[k] = c
                else:
                    results[k] = c.model_copy(update={"problem": c.problem})
        except Exception:  # rewrite is best effort
            pass

    agent_lines: list[CheckedLine] = []
    notes: list[CheckedLine] = []
    dropped: list[str] = []
    for a in agents:
        c = results.get(a)
        if c is None or c.problem:
            # fall back to the agent's own council argument, held to the same checks
            arg = next((x for x in kept_args if x["agent"] == a), None)
            fb = (
                check_line(
                    Line(speaker=a, text=arg["text"], cited_ids=arg["cited_ids"]), facts, quotes, mode, lang=lang
                )
                if arg
                else None
            )
            if fb is not None and fb.problem is None:
                c = fb
            else:
                dropped.append(a)
                reasons = [first_problem.get(a, ""), c.problem if c else "", fb.problem if fb else ""]
                if any(r and r.startswith("privacy") for r in reasons):
                    notes.append(
                        CheckedLine(
                            speaker="alfii",
                            text=t(lang, "budget_note", agent=name(lang, a)),
                            kind="note",
                            blocked_reason=next(r for r in reasons if r),
                        )
                    )
                continue
        agent_lines.append(CheckedLine(speaker=a, text=c.spoken, screen_text=c.screen, cited_ids=c.cited))

    v = results["verdict"]
    verdict = (
        None if v.problem else CheckedLine(speaker="alfii", text=v.spoken, screen_text=v.screen, kind="conclusion")
    )
    return Explained(
        agent_lines=agent_lines,
        notes=notes,
        verdict=verdict,
        questions=out.questions,
        rewrite_used=rewrite_used,
        fixes=fixes,
        lint_rejections=lint_rejections,
        dropped_turns=dropped,
    )


def fallback_turns(
    agents: list[str],
    kept_args: list[dict[str, Any]],
    facts: list[Fact],
    quotes: dict[str, str],
    mode: PrivacyMode,
    lang: str = "en",
) -> tuple[list[CheckedLine], list[CheckedLine]]:
    """No-LLM fallback (explainer failed): each agent's own checked argument, or a budget note / nothing."""
    lines, notes = [], []
    for a in agents:
        arg = next((x for x in kept_args if x["agent"] == a), None)
        if arg is None:
            continue
        c = check_line(Line(speaker=a, text=arg["text"], cited_ids=arg["cited_ids"]), facts, quotes, mode, lang=lang)
        if c.problem is None:
            lines.append(CheckedLine(speaker=a, text=c.spoken, screen_text=c.screen, cited_ids=c.cited))
        elif c.problem.startswith("privacy"):
            notes.append(CheckedLine(speaker="alfii", text=t(lang, "budget_note", agent=name(lang, a)), kind="note"))
    return lines, notes
