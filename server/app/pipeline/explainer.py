"""Step 12: Alfii's spoken lines. Every line passes the evidence check AND the privacy check; failing lines are
rewritten once (if the LLM budget allows), then replaced by ON_SCREEN. Deterministic templates when the LLM fails."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from app.engines.fact import Fact
from app.pipeline.consensus import Colour
from app.pipeline.evidence import check_argument, numbers_in
from app.pipeline.privacy import PrivacyMode, speech_allowed
from app.pipeline.schemas import ExplainerOutput, Line, RewriteOutput
from app.prompts import prompts
from app.providers.llm import LLMProvider, current_budget

ON_SCREEN = "I've put that on your screen."
NAMES = {"alfii": "Alfii", "sankz": "Sankz", "dani": "Dani", "vick": "Vick"}
VERDICT_TEMPLATES: dict[str, str] = {
    "red": "My advice: do not go ahead with this as it is.",
    "yellow": "Be careful: get clear answers to these questions before you decide.",
    "green": "This looks reasonable for your family, but take your time before you sign.",
}


class CheckedLine(BaseModel):
    speaker: str
    text: str
    cited_ids: list[str] = []
    allowed: bool = True
    blocked_reason: str | None = None


def line_problem(line: Line, facts: list[Fact], quotes: dict[str, str], mode: PrivacyMode) -> str | None:
    if numbers_in(line.text):
        res = check_argument(line.text, line.cited_ids, facts, quotes)
        if not res.kept:
            return f"evidence: {res.reason}"  # type: ignore[union-attr]
    elif any(c not in quotes and c not in {f.id for f in facts} for c in line.cited_ids):
        return "evidence: unknown citation id"
    priv = speech_allowed(line.text, line.cited_ids, facts, mode)
    return None if priv.allowed else f"privacy: {priv.reason}"  # type: ignore[union-attr]


def question_ok(q: str, facts: list[Fact], quotes: dict[str, str], mode: PrivacyMode) -> bool:
    """Questions are read aloud: any number must exist in some fact or quote, and nothing personal in discreet."""
    line = Line(speaker="alfii", text=q, cited_ids=[f.id for f in facts] + list(quotes))
    if numbers_in(q) and not check_argument(q, line.cited_ids, facts, quotes).kept:
        return False
    personal_only = Line(speaker="alfii", text=q)
    return speech_allowed(personal_only.text, [], facts, mode).allowed


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
) -> dict[str, Any]:
    return {
        "verdict_colour": colour,
        "case": summary,
        "called_agents": agents,
        "arguments": kept_args,
        "facts": facts_table,
        "quotes": quotes,
        "privacy_mode": mode.upper(),
        "language": language,
        "candidate_questions": questions,
    }


async def explain(
    llm: LLMProvider, payload: dict[str, Any], facts: list[Fact], quotes: dict[str, str], mode: PrivacyMode
) -> tuple[ExplainerOutput, list[CheckedLine], bool]:
    """Returns (raw output, checked lines in order [opener, agents..., verdict], rewrite_used)."""
    out, _ = await llm.chat_json(prompts.EXPLAINER, json.dumps(payload, separators=(",", ":")), ExplainerOutput)
    lines = [out.opener, *out.agent_lines, out.verdict_sentence]
    problems = {i: p for i, ln in enumerate(lines) if (p := line_problem(ln, facts, quotes, mode))}
    rewrite_used = False
    budget = current_budget()
    if problems and (budget is None or budget.used < budget.max_calls):
        rewrite_used = True
        req = {
            "privacy_mode": mode.upper(),
            "lines": [{"index": i, **lines[i].model_dump(), "problem": p} for i, p in problems.items()],
            "facts": payload["facts"],
            "quotes": payload["quotes"],
        }
        try:
            fixed, _ = await llm.chat_json(prompts.REWRITE, json.dumps(req, separators=(",", ":")), RewriteOutput)
            for i, new in zip(list(problems), fixed.lines, strict=False):
                new = new.model_copy(update={"speaker": lines[i].speaker})
                if (p := line_problem(new, facts, quotes, mode)) is None:
                    lines[i] = new
                    problems.pop(i)
                else:
                    problems[i] = p
        except Exception:  # rewrite is best effort; failing lines are replaced below
            pass
    checked = []
    for i, ln in enumerate(lines):
        if i in problems:
            checked.append(CheckedLine(speaker=ln.speaker, text=ON_SCREEN, allowed=False, blocked_reason=problems[i]))
        else:
            checked.append(CheckedLine(speaker=ln.speaker, text=ln.text, cited_ids=ln.cited_ids))
    return out, checked, rewrite_used


def template_lines(
    colour: Colour | None,
    agents: list[str],
    kept_args: list[dict[str, Any]],
    facts: list[Fact],
    quotes: dict[str, str],
    mode: PrivacyMode,
) -> list[CheckedLine]:
    """No-LLM fallback: Alfii's opener, each agent's first kept argument (re-checked for privacy), verdict template."""
    who = " and ".join(NAMES[a] for a in agents) or "the team"
    lines = [CheckedLine(speaker="alfii", text=f"I asked {who} to look at this.")]
    for a in agents:
        arg = next((x for x in kept_args if x["agent"] == a), None)
        if arg is None:
            continue
        ln = Line(speaker=a, text=arg["text"], cited_ids=arg["cited_ids"])
        p = line_problem(ln, facts, quotes, mode)
        lines.append(
            CheckedLine(
                speaker=a, text=ON_SCREEN if p else ln.text, cited_ids=ln.cited_ids, allowed=p is None, blocked_reason=p
            )
        )
    lines.append(
        CheckedLine(speaker="alfii", text=VERDICT_TEMPLATES.get(colour or "", "Let us look at this together."))
    )
    return lines
