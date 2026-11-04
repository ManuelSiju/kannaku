"""Family members, the family budget, investment holdings and the 6 owner documents."""

from __future__ import annotations

import asyncio
import json
import shutil
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.config import SERVER_ROOT, get_settings
from app.db.migrate import MIGRATIONS
from app.db.repo import FamilyItem
from app.main import app
from app.mcp_server import tools
from app.pipeline.ingest import Upload, ingest
from app.pipeline.profile_extract import extract_profile
from tests.fakes import FakeSTT
from tests.test_demo_safe_baseline import BASELINE, run_case

DOCS = SERVER_ROOT / "demo_assets" / "owner_docs"
ZEPHYRX_VALUE = 19047  # 150 shares at the last close in the price file, 126.98
needs_ocr = pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract is not installed")


@pytest.fixture
def client(demo_repo):
    app.dependency_overrides[deps.get_repo] = lambda: demo_repo
    app.dependency_overrides[deps.get_stt_provider] = lambda: FakeSTT("")
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def arun(repo) -> int:
    return next(m["id"] for m in repo.members(1) if m["name"] == "Arun")


def salary(repo, *, in_household: bool) -> None:
    repo.set_profile_value(arun(repo), "monthly_income", 52_000, "document", confirmed=True, in_household=in_household)


def facts_of(result: dict) -> dict:
    return result["facts"]


# ---------------------------------------------------------------- migration
def test_migration_keeps_existing_items(tmp_path):
    conn = sqlite3.connect(tmp_path / "old.db")
    for path in sorted(MIGRATIONS.glob("000[1-5]_*.sql")):
        conn.executescript(path.read_text())
    conn.execute("INSERT INTO family (id) VALUES (1)")
    conn.execute(
        "INSERT INTO family_item (family_id, kind, name, amount, frequency, source, confirmed) "
        "VALUES (1, 'loan', 'Scooter loan EMI', 2400, 'monthly', 'voice', 1)"
    )
    conn.executescript((MIGRATIONS / "0006_members_holdings.sql").read_text())
    conn.row_factory = sqlite3.Row
    row = dict(conn.execute("SELECT * FROM family_item").fetchone())
    assert (row["name"], row["amount"], row["in_household"], row["member_id"]) == ("Scooter loan EMI", 2400, 1, None)
    conn.execute(
        "INSERT INTO family_item (family_id, kind, name, amount, frequency, source) "
        "VALUES (1, 'stock_holding', 'ZEPHYRX', 1, 'once', 'document')"
    )


# ---------------------------------------------------------------- family budget golden
@pytest.mark.parametrize("name", ["endowment", "flat_loan", "stock_tip"])
def test_a_salary_outside_the_budget_changes_no_fact(demo_repo, name):
    salary(demo_repo, in_household=False)
    got = run_case(demo_repo, name, "discreet")
    assert facts_of(got) == json.loads(BASELINE.read_text())["discreet"][name]["facts"]


@pytest.mark.parametrize("name", ["endowment", "flat_loan"])
def test_a_salary_in_the_budget_changes_income_and_affordability(demo_repo, name):
    salary(demo_repo, in_household=True)
    facts = facts_of(run_case(demo_repo, name, "discreet"))
    before = json.loads(BASELINE.read_text())["discreet"][name]["facts"]
    assert facts["profile.monthly_income"][0] == 97_000
    assert facts["surplus_after"][0] == before["surplus_after"][0] + 52_000
    assert facts["emi_share"][0] < before["emi_share"][0]


def test_fact_lists_who_contributed(demo_repo):
    salary(demo_repo, in_household=True)
    income = tools.profile_facts(1, demo_repo)[0]
    assert income.inputs["members"] == ["Lakshmi", "Arun"]
    assert "Lakshmi, Arun" in income.formula


def test_items_outside_the_budget_are_not_counted(demo_repo):
    common = {"source": "document", "member_id": arun(demo_repo), "in_household": False}
    demo_repo.save_item(1, FamilyItem(kind="loan", name="L", amount=9000, frequency="monthly", **common), True)
    demo_repo.save_item(1, FamilyItem(kind="sip", name="S", amount=5000, frequency="monthly", **common), True)
    assert tools.existing_emi_fact(1, demo_repo).value == 2400
    assert tools.regular_commitments_fact(1, demo_repo).value == 1000


def test_flag_off_ignores_a_member_outside_the_budget(demo_repo, monkeypatch):
    salary(demo_repo, in_household=False)
    monkeypatch.setenv("FEATURE_MEMBERS", "false")
    get_settings.cache_clear()
    try:
        assert tools.profile_facts(1, demo_repo)[0].value == 45_000
    finally:
        get_settings.cache_clear()


# ---------------------------------------------------------------- API
def test_member_values_default_out_of_the_budget(client, demo_repo):
    member = arun(demo_repo)
    prop = client.post(
        "/families/1/profile/extract", data={"text": "Net salary Rs 52,000 a month.", "member_id": member}
    ).json()
    assert prop["member_id"] == member and prop["ask_household"] is True
    value = {**prop["values"][0], "confirmed": True}
    profile = client.post("/families/1/profile/confirm", json={"values": [value], "member_id": member}).json()[
        "profile"
    ]
    assert profile["household"]["monthly_income"] == 45_000
    owner = next(m for m in profile["member_values"] if m["name"] == "Arun")
    assert owner["values"] == [
        {"field": "monthly_income", "value": 52000, "source": "typed", "in_household": False},
    ]


def test_member_can_be_counted_when_the_family_says_so(client, demo_repo):
    member = arun(demo_repo)
    value = {"field": "monthly_income", "value": 52000, "source": "typed", "confirmed": True, "in_household": True}
    out = client.post("/families/1/profile/confirm", json={"values": [value], "member_id": member}).json()
    assert out["profile"]["household"]["monthly_income"] == 97_000


def test_primary_is_the_default_and_asks_nothing(client):
    prop = client.post("/families/1/profile/extract", data={"text": "My pension is 50,000 a month."}).json()
    assert prop["ask_household"] is False
    value = {**prop["values"][0], "confirmed": True}
    out = client.post("/families/1/profile/confirm", json={"values": [value]}).json()
    assert out["profile"]["household"]["monthly_income"] == 50_000


def test_a_stranger_is_refused(client):
    r = client.post("/families/1/profile/extract", data={"text": "Salary 5,000.", "member_id": 999})
    assert r.status_code == 422


def test_a_holding_keeps_its_owner_and_details(client, demo_repo):
    member = arun(demo_repo)
    prop = client.post(
        "/families/1/profile/extract",
        data={"text": "Stock holding ZEPHYRX value Rs 19,047 for 150 shares.", "member_id": member},
    ).json()
    item = {**prop["items"][0], "confirmed": True}
    client.post("/families/1/profile/confirm", json={"items": [item], "member_id": member})
    saved = demo_repo.list_items(1, "stock_holding")[0]
    assert (saved.member_id, saved.in_household, saved.symbol, saved.units) == (member, False, "ZEPHYRX", 150)


# ---------------------------------------------------------------- holdings
def holdings(repo) -> None:
    for line in (
        "Mutual fund holding Nila Bharat Index Fund value Rs 1,25,400 for 3210.455 units.",
        "Mutual fund holding Nila Short Term Debt Fund value Rs 48,599 for 1502.110 units.",
        "SIP Rs 5,000 a month into Nila Bharat Index Fund.",
        "Stock holding PERIYARSOFT value Rs 42,300 for 60 shares.",
        "Stock holding MALABARTEA value Rs 18,750 for 250 shares.",
        "Stock holding ZEPHYRX value Rs 19,047 for 150 shares.",
    ):
        (item,) = extract_profile(line, "document").items
        fields = item.model_dump(exclude={"quote", "uncertain", "readback"})
        repo.save_item(1, FamilyItem(**fields, member_id=arun(repo), in_household=False), True)


def test_holdings_facts(demo_repo):
    holdings(demo_repo)
    f = {x.id: x for x in tools.holdings_facts(1, demo_repo)}
    assert f["holdings.mf_value_total"].value == 173_999
    assert f["holdings.equity_mf_value"].value == 125_400
    assert f["holdings.stock_value_total"].value == 80_097
    assert f["holdings.total_value"].value == 254_096
    assert f["holdings.sip_monthly"].value == 5_000
    assert f["holdings.largest_stock_share"].value == pytest.approx(42_300 / 80_097)
    assert all(x.kind == "personal" and "as on statement date" in x.label for x in f.values())


def test_no_holdings_no_facts(demo_repo):
    assert tools.holdings_facts(1, demo_repo) == []
    assert tools.tip_holding_facts(1, "ZEPHYRX", demo_repo) == []


def test_tip_on_a_held_share_adds_personal_facts(demo_repo):
    holdings(demo_repo)
    f = {x.id: x for x in tools.tip_holding_facts(1, "ZEPHYRX LTD", demo_repo)}
    assert f["tip.held_shares"].display == "150 shares"
    assert f["tip.held_value"].value == 19_047
    assert f["tip.held_share_of_stocks"].value == pytest.approx(19_047 / 80_097)
    assert all(x.kind == "personal" for x in f.values())
    assert tools.tip_holding_facts(1, "NOTHELD", demo_repo) == []


def test_holdings_do_not_change_the_budget_or_the_buffer(demo_repo):
    before = facts_of(run_case(demo_repo, "endowment", "discreet"))
    holdings(demo_repo)
    after = facts_of(run_case(demo_repo, "endowment", "discreet"))
    assert after["buffer_months_after"] == before["buffer_months_after"]
    assert after["surplus_after"] == before["surplus_after"]


def test_buffer_formula_says_bank_savings_only(demo_repo):
    holdings(demo_repo)
    run_case(demo_repo, "endowment", "discreet")
    case = demo_repo.conn.execute("SELECT MAX(id) FROM cases").fetchone()[0]
    fact = next(f for f in demo_repo.get_facts(case) if f.id == "buffer_months_after")
    assert "bank savings only" in fact.formula


def test_personal_holding_stays_off_the_council_in_discreet_mode(demo_repo):
    holdings(demo_repo)
    res = run_case(demo_repo, "stock_tip", "discreet")
    assert res["facts"]["tip.held_shares"][0] == 150
    assert not any("150" in text for _, text in res["spoken"])


def test_flag_off_reads_no_holdings(monkeypatch):
    monkeypatch.setenv("FEATURE_HOLDINGS", "false")
    get_settings.cache_clear()
    try:
        assert extract_profile("Stock holding ZEPHYRX value Rs 19,047 for 150 shares.", "typed").items == []
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize(
    ("scheme", "category"),
    [("Nila Flexi Cap", "equity"), ("Nila ELSS Saver", "equity"), ("Nila Gilt Fund", "debt"), ("Nila Gold", "other")],
)
def test_category_from_the_scheme_name(scheme, category):
    (item,) = extract_profile(f"Mutual fund holding {scheme} value Rs 1,000 for 10 units.", "typed").items
    assert item.category == category


def test_amounts_in_lakh_on_a_holding_line():
    (item,) = extract_profile("Mutual fund holding Nila Index value ₹1.5 lakh for 2,000.5 units.", "typed").items
    assert (item.amount, item.units) == (150_000, 2000.5)


# ---------------------------------------------------------------- the 6 owner documents, exactly
EXPECTED = {
    "lakshmi_bank_passbook": ([("savings", 185_000)], []),
    "lakshmi_gold_loan_letter": ([], [("loan", 3512, "monthly", None, None)]),
    "lakshmi_health_cover": ([], [("policy", 9600, "yearly", None, None)]),
    "arun_salary_slip": ([("monthly_income", 52_000)], []),
    "arun_mf_statement": (
        [],
        [
            ("mf_holding", 125_400, "once", 3210.455, "equity"),
            ("mf_holding", 48_599, "once", 1502.11, "debt"),
            ("sip", 5000, "monthly", None, "equity"),
        ],
    ),
    "arun_demat_holdings": (
        [],
        [
            ("stock_holding", 42_300, "once", 60, None),
            ("stock_holding", 18_750, "once", 250, None),
            ("stock_holding", ZEPHYRX_VALUE, "once", 150, None),
        ],
    ),
}


@needs_ocr
@pytest.mark.parametrize("extension", ["pdf", "png"])
@pytest.mark.parametrize("name", EXPECTED)
def test_owner_document_reads_exactly(name, extension):
    path = DOCS / f"{name}.{extension}"
    mime = "application/pdf" if extension == "pdf" else "image/png"
    upload = Upload(filename=path.name, data=path.read_bytes(), mime=mime)
    text = asyncio.run(ingest(text=None, audio=None, files=[upload], stt=None)).doc_text
    prop = extract_profile(text, "document", source_ref=path.name)
    assert [(v.field, v.value) for v in prop.values] == EXPECTED[name][0]
    assert [(i.kind, i.amount, i.frequency, i.units, i.category) for i in prop.items] == EXPECTED[name][1]
    assert not any(x.uncertain for x in [*prop.values, *prop.items])


def test_the_mf_statement_names_its_schemes():
    prop = extract_profile("SIP Rs 5,000 a month into Nila Bharat Index Fund.", "document")
    assert prop.items[0].scheme == "Nila Bharat Index Fund"


def test_zephyrx_value_agrees_with_the_price_file():
    last = (SERVER_ROOT / "demo_assets" / "stocks" / "ZEPHYRX.csv").read_text().strip().splitlines()[-1]
    assert round(float(last.split(",")[1]) * 150) == ZEPHYRX_VALUE


# ---------------------------------------------------------------- money snapshot
def test_snapshot_comes_from_the_facts(demo_repo):
    holdings(demo_repo)
    snap = tools.family_snapshot(1, demo_repo)
    assert snap == {
        "savings": 160_000,
        "holdings_total": 254_096,
        "money_in": 45_000,
        "money_out": 28_000 + 2_400 + 1_000,
        "emi_share": 0.0533,  # the engine rounds a share to 4 places
    }


def test_snapshot_keeps_unknown_as_none(repo):
    family = repo.create_family()
    repo.add_member(family, "Asha", "primary")
    snap = tools.family_snapshot(family, repo)
    assert snap["savings"] is None and snap["money_out"] is None and snap["emi_share"] is None


def test_snapshot_flag_off_leaves_it_out(demo_repo, monkeypatch):
    monkeypatch.setenv("FEATURE_SNAPSHOT", "false")
    get_settings.cache_clear()
    try:
        assert "snapshot" not in tools.family_get_profile(1, demo_repo)
    finally:
        get_settings.cache_clear()
