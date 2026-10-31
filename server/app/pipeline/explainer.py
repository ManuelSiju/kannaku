"""Step 12: the agents' spoken lines and Alfii's verdict sentence (Alfii's opener is a code template, see run.py).
Numbers appear only as {fact_id} placeholders, filled in by code. Every line passes the evidence check (no raw
digits, known ids, comparison words backed by cmp_* facts) and then the privacy check on the filled-in text; failing
lines are rewritten once (if the LLM budget allows), then replaced by ON_SCREEN. Templates if the LLM fails."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from app.engines.fact import Fact
from app.pipeline.consensus import Colour
from app.pipeline.evidence import Dropped, Kept, check_argument, placeholders, raw_number
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
    text: str  # what is spoken: placeholders filled in, or ON_SCREEN
    cited_ids: list[str] = []
    allowed: bool = True
    blocked_reason: str | None = None


def opener(agents: list[str]) -> str:
    """Alfii's opener, templated in code (no LLM): "Let me ask Dani and Sankz."."""
    names = [NAMES[a] for a in agents]
    if not names:
        return "Let me look at this."
    who = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    return f"Let me ask {who}."


def check_line(
    line: Line, facts: list[Fact], quotes: dict[str, str], mode: PrivacyMode, *, comparisons: bool = True
) -> tuple[str | None, str, list[str]]:
    """(problem or None, rendered text, fixes). Lines without numbers or comparisons need no citation."""
    rendered, cited, fixes = line.text, list(line.cited_ids), []
    needs_check = placeholders(line.text) or raw_number(line.text) or line.cited_ids or comparisons
    if needs_check:
        res = check_argument(line.text, line.cited_ids, facts, quotes, comparisons=comparisons)
        fixes = res.fixes
        if isinstance(res, Dropped):
            if res.reason != "no evidence cited":
                return f"evidence: {res.reason}", line.text, fixes
        elif isinstance(res, Kept):
            rendered, cited = res.rendered, res.cited
    priv = speech_allowed(rendered, cited, facts, mode)
    return (None if priv.allowed else f"privacy: {priv.reason}"), rendered, fixes  # type: ignore[union-attr]


def render_question(q: str, facts: list[Fact], quotes: dict[str, str], mode: PrivacyMode) -> str | None:
    """Questions are read aloud too (no comparison rule: "is there a lower rate?" is a fair question)."""
    problem, rendered, _ = check_line(Line(speaker="alfii", text=q), facts, quotes, mode, comparisons=False)
    return None if problem else rendered


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
) -> tuple[ExplainerOutput, list[CheckedLine], bool, list[str]]:
    """Returns (raw output, checked lines [agents..., verdict], rewrite_used, fixes)."""
    out, _ = await llm.chat_json(prompts.EXPLAINER, json.dumps(payload, separators=(",", ":")), ExplainerOutput)
    lines = [*out.agent_lines, out.verdict_sentence]
    rendered: dict[int, str] = {}
    problems: dict[int, str] = {}
    all_fixes: list[str] = []
    for i, ln in enumerate(lines):
        p, rendered[i], fixes = check_line(ln, facts, quotes, mode)
        all_fixes += fixes
        if p:
            problems[i] = p
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
                p, text, fixes = check_line(new, facts, quotes, mode)
                all_fixes += fixes
                if p is None:
                    lines[i], rendered[i] = new, text
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
            checked.append(CheckedLine(speaker=ln.speaker, text=rendered[i], cited_ids=ln.cited_ids))
    return out, checked, rewrite_used, all_fixes


def template_lines(
    colour: Colour | None,
    agents: list[str],
    kept_args: list[dict[str, Any]],
    facts: list[Fact],
    quotes: dict[str, str],
    mode: PrivacyMode,
) -> list[CheckedLine]:
    """No-LLM fallback: each agent's first kept argument (re-checked for privacy) and the verdict template."""
    lines = []
    for a in agents:
        arg = next((x for x in kept_args if x["agent"] == a), None)
        if arg is None:
            continue
        ln = Line(speaker=a, text=arg["text"], cited_ids=arg["cited_ids"])
        p, text, _ = check_line(ln, facts, quotes, mode)
        lines.append(
            CheckedLine(
                speaker=a, text=ON_SCREEN if p else text, cited_ids=ln.cited_ids, allowed=p is None, blocked_reason=p
            )
        )
    lines.append(
        CheckedLine(speaker="alfii", text=VERDICT_TEMPLATES.get(colour or "", "Let us look at this together."))
    )
    return lines
