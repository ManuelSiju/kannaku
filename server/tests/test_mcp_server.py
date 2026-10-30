"""Real MCP client over stdio against `python -m app.mcp_server.server`."""

import json
import os
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

SERVER_DIR = Path(__file__).resolve().parents[1]

EXPECTED = {
    "family.get_profile",
    "family.list_items",
    "family.save_item",
    "case.get_terms",
    "case.get_quotes",
    "rates.get_reference",
    "stocks.get_history",
    "stocks.tip_signals",
    "calc.irr",
    "calc.endowment_return",
    "calc.fd_value",
    "calc.sip_value",
    "calc.flat_to_effective",
    "calc.affordability",
}


async def test_list_tools_and_call(tmp_path, demo_repo):
    env = {**os.environ, "DB_PATH": demo_repo.path}
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "app.mcp_server.server"], cwd=str(SERVER_DIR), env=env
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        names = {t.name for t in (await session.list_tools()).tools}
        assert EXPECTED <= names

        res = await session.call_tool("calc.irr", {"cashflows": [[0, -100], [1, 110]]})
        assert not res.isError
        payload = json.loads(res.content[0].text)
        (fact,) = payload["facts"]
        assert fact["id"] == "irr" and abs(fact["value"] - 0.1) < 1e-6

        res = await session.call_tool("family.get_profile", {"family_id": 1})
        facts = {f["id"]: f for f in json.loads(res.content[0].text)["facts"]}
        assert facts["profile.monthly_expenses"]["value"] == 28_000

        res = await session.call_tool(
            "family.save_item",
            {
                "family_id": 1,
                "confirmed": False,
                "item": {"kind": "other", "name": "x", "amount": 1, "frequency": "once", "source": "typed"},
            },
        )
        assert json.loads(res.content[0].text)["saved"] is False
