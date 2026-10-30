"""Steps 7-9: one batched council call, evidence check on every argument, optional debate round.

Never invents a vote: an agent missing from the model's output gets no position; an agent whose arguments
were all dropped abstains (unsure, strength 0) unless the debate round fixes it.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from app.engines.fact import Fact
from app.pipeline.consensus import Position
from app.pipeline.evidence import check_argument
from app.pipeline.schemas import AgentOpinion, CouncilOutput
from app.prompts import prompts
from app.providers.llm import LLMProvider


class CheckedArgument(BaseModel):
    agent: str
    round: int
    text: str
    cited_ids: list[str]
    kept: bool
    drop_reason: str | None = None


class CouncilRound(BaseModel):
    round: int
    positions: list[Position]
    arguments: list[CheckedArgument]
    questions: list[str]
    missing_agents: list[str]  # called but absent from the output: no vote
    abstained: list[str]  # all arguments dropped


def facts_table(facts: list[Fact]) -> list[dict[str, Any]]:
    return [{"id": f.id, "label": f.label, "value": f.display, "kind": f.kind} for f in facts]


def council_input(
    summary: dict[str, Any], facts: list[Fact], quotes: dict[str, dict[str, str]], agents: list[str]
) -> dict[str, Any]:
    return {
        "case": summary,
        "facts": facts_table(facts),
        "quotes": [{"id": qid, "source": q["source"], "text": q["text"]} for qid, q in quotes.items()],
        "agents": [{"agent": a, "role": prompts.ROLE_CARDS[a]} for a in agents],
    }


def check_round(
    output: CouncilOutput, agents: list[str], facts: list[Fact], quote_text: dict[str, str], round: int
) -> CouncilRound:
    by_agent: dict[str, AgentOpinion] = {}
    for op in output.opinions:
        if op.agent in agents and op.agent not in by_agent:
            by_agent[op.agent] = op
    positions, checked, questions, abstained = [], [], [], []
    for agent in agents:
        op = by_agent.get(agent)
        if op is None:
            continue
        kept = 0
        for arg in op.arguments:
            res = check_argument(arg.text, arg.cited_ids, facts, quote_text)
            checked.append(
                CheckedArgument(
                    agent=agent,
                    round=round,
                    text=arg.text,
                    cited_ids=arg.cited_ids,
                    kept=res.kept,
                    drop_reason=None if res.kept else res.reason,
                )
            )  # type: ignore[union-attr]
            kept += int(res.kept)
        if kept:
            positions.append(Position(agent=agent, stance=op.stance, strength=op.strength))
            questions += op.questions_for_seller
        else:
            positions.append(Position(agent=agent, stance="unsure", strength=0.0))
            abstained.append(agent)
    missing = [a for a in agents if a not in by_agent]
    return CouncilRound(
        round=round,
        positions=positions,
        arguments=checked,
        questions=questions,
        missing_agents=missing,
        abstained=abstained,
    )


async def run_council(
    llm: LLMProvider, payload: dict[str, Any], agents: list[str], facts: list[Fact], quote_text: dict[str, str]
) -> tuple[CouncilRound, Any]:
    out, usage = await llm.chat_json(prompts.COUNCIL, json.dumps(payload, separators=(",", ":")), CouncilOutput)
    return check_round(out, agents, facts, quote_text, round=1), usage


async def run_debate(
    llm: LLMProvider,
    payload: dict[str, Any],
    first: CouncilRound,
    agents: list[str],
    facts: list[Fact],
    quote_text: dict[str, str],
) -> tuple[CouncilRound, Any]:
    payload = payload | {
        "round_1": {
            "positions": [p.model_dump() for p in first.positions],
            "kept_arguments": [
                {"agent": a.agent, "text": a.text, "cited_ids": a.cited_ids} for a in first.arguments if a.kept
            ],
            "must_cite_properly": first.abstained,
        }
    }
    out, usage = await llm.chat_json(prompts.DEBATE, json.dumps(payload, separators=(",", ":")), CouncilOutput)
    second = check_round(out, agents, facts, quote_text, round=2)
    # An agent the debate did not answer keeps its round-1 position.
    answered = {p.agent for p in second.positions}
    second.positions += [p for p in first.positions if p.agent not in answered]
    second.missing_agents = [a for a in first.missing_agents if a not in answered]
    return second, usage
