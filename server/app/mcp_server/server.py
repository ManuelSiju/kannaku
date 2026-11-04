"""Kanakku MCP server (stdio). Thin wrapper: every tool calls the same function the pipeline uses in-process.

Run: make run-mcp   (or: python -m app.mcp_server.server)
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from app.mcp_server import tools

mcp = FastMCP("kanakku")


@mcp.tool(name="family.get_profile", description="Family money values (known/unknown, with source) as facts.")
def family_get_profile(family_id: int) -> dict[str, Any]:
    return tools.family_get_profile(family_id)


@mcp.tool(name="family.list_items", description="Family's policies, loans, deposits, chits; optional kind filter.")
def family_list_items(family_id: int, kind: str | None = None) -> dict[str, Any]:
    return tools.family_list_items(family_id, kind)


@mcp.tool(name="family.list_documents", description="Papers the family showed, with the category each was given.")
def family_list_documents(family_id: int) -> dict[str, Any]:
    return tools.family_list_documents(family_id)


@mcp.tool(name="family.save_item", description="Save a family item. Refused unless confirmed is true.")
def family_save_item(family_id: int, item: dict[str, Any], confirmed: bool) -> dict[str, Any]:
    return tools.family_save_item(family_id, item, confirmed)


@mcp.tool(name="case.get_terms", description="Terms extracted for a case, with verified flag and quote_id.")
def case_get_terms(case_id: int) -> dict[str, Any]:
    return tools.case_get_terms(case_id)


@mcp.tool(name="case.get_quotes", description="Evidence quotes for a case (quote_id = q<id>).")
def case_get_quotes(case_id: int) -> dict[str, Any]:
    return tools.case_get_quotes(case_id)


@mcp.tool(name="rates.get_reference", description="Reference rates snapshot (assumptions) with as_of date.")
def rates_get_reference() -> dict[str, Any]:
    return tools.rates_get_reference()


@mcp.tool(name="stocks.get_history", description="Daily price/volume history from the local cache.")
def stocks_get_history(symbol: str) -> dict[str, Any]:
    return tools.stocks_get_history(symbol)


@mcp.tool(name="stocks.tip_signals", description="Pump-and-dump signals for a stock tip (never a buy call).")
def stocks_tip_signals(symbol: str) -> dict[str, Any]:
    return tools.stocks_tip_signals(symbol)


@mcp.tool(name="calc.irr", description="Yearly IRR of [[year, amount], ...] cash flows (outflows negative).")
def calc_irr(cashflows: list[list[float]], kind: str = "offer") -> dict[str, Any]:
    return tools.calc_irr(cashflows, kind)


@mcp.tool(name="calc.endowment_return", description="Yearly return of a policy: premiums at start of each year.")
def calc_endowment_return(premium: float, pay_years: int, payout: float, payout_year: float) -> dict[str, Any]:
    return tools.calc_endowment_return(premium, pay_years, payout, payout_year)


@mcp.tool(name="calc.fd_value", description="FD value of a yearly deposit (start of year, yearly compounding).")
def calc_fd_value(yearly_amount: float, years: int, rate: float) -> dict[str, Any]:
    return tools.calc_fd_value(yearly_amount, years, rate)


@mcp.tool(name="calc.sip_value", description="Value of a monthly SIP (start of month, monthly compounding).")
def calc_sip_value(monthly_amount: float, months: int, annual_rate: float) -> dict[str, Any]:
    return tools.calc_sip_value(monthly_amount, months, annual_rate)


@mcp.tool(name="calc.flat_to_effective", description="Flat-rate loan: EMI, total interest, real yearly rate.")
def calc_flat_to_effective(principal: float, flat_rate_annual: float, months: int) -> dict[str, Any]:
    return tools.calc_flat_to_effective(principal, flat_rate_annual, months)


@mcp.tool(
    name="calc.affordability",
    description="EMI share, savings buffer (months), monthly surplus after a new monthly cost (counts EMIs and "
    "regular commitments such as yearly premiums / 12). "
    "Give family_id to fill missing values from the confirmed profile. Missing stays unknown.",
)
def calc_affordability(
    new_monthly_cost: float | None = None,
    family_id: int | None = None,
    monthly_income: float | None = None,
    monthly_expenses: float | None = None,
    savings: float | None = None,
    existing_emi: float | None = None,
    regular_commitments: float | None = None,
) -> dict[str, Any]:
    return tools.calc_affordability(
        monthly_income,
        monthly_expenses,
        savings,
        existing_emi,
        new_monthly_cost,
        family_id,
        regular_commitments=regular_commitments,
    )


def main() -> None:
    mcp.run()  # stdio


if __name__ == "__main__":
    main()
