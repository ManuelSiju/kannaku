import pytest

from app.engines.fact import Fact
from app.mcp_server import tools
from app.pipeline.evidence import check_argument


def ids(result):
    return {f["id"]: f for f in result["facts"]}


def test_profile_known_and_unknown(demo_repo):
    out = tools.family_get_profile(1, demo_repo)
    f = ids(out)
    assert f["profile.monthly_income"]["value"] == 45_000 and f["profile.monthly_income"]["inputs"]["source"] == "voice"
    assert f["profile.savings"]["inputs"]["source"] == "document"
    assert f["existing_emi"]["value"] == 2_400  # scooter loan only; policy premium is not an EMI
    assert f["regular_commitments"]["value"] == 1_000  # money-back policy 12,000 a year / 12
    assert all(x["kind"] == "personal" for x in out["facts"])
    # facts are unchanged Fact dumps
    assert all(Fact.model_validate(x).model_dump() == x for x in out["facts"])

    empty = tools.family_get_profile(99, demo_repo)
    assert {v["status"] for v in empty["values"]} == {"unknown"}
    assert ids(empty)["profile.savings"]["value"] is None


def test_list_and_save_items(demo_repo):
    out = tools.family_list_items(1, None, demo_repo)
    assert [i["kind"] for i in out["items"]] == ["policy", "loan"]
    assert ids(out)[f"item.{out['items'][0]['id']}.amount"]["value"] == 12_000
    assert [i["name"] for i in tools.family_list_items(1, "loan", demo_repo)["items"]] == ["Scooter loan EMI"]

    item = {"kind": "chit", "name": "Chit fund", "amount": 5_000, "frequency": "monthly", "source": "voice"}
    refused = tools.family_save_item(1, item, False, demo_repo)
    assert refused["saved"] is False and "not confirmed" in refused["reason"]
    saved = tools.family_save_item(1, item, True, demo_repo)
    assert saved["saved"] and len(tools.family_list_items(1, "chit", demo_repo)["items"]) == 1


def test_expired_loan_not_counted(demo_repo):
    from datetime import date

    assert tools.existing_emi_fact(1, demo_repo, today=date(2027, 4, 1)).value == 0


def test_case_terms_and_quotes(demo_repo):
    cid = demo_repo.create_case(1)
    qid = demo_repo.add_evidence(cid, "page_1", "Annual premium: Rs. 50,000")
    demo_repo.add_term(cid, "premium", 50_000, "INR", evidence_id=int(qid[1:]), verified=True)
    assert tools.case_get_quotes(cid, demo_repo)["quotes"] == [
        {"id": qid, "source": "page_1", "text": "Annual premium: Rs. 50,000"}
    ]
    assert tools.case_get_terms(cid, demo_repo)["terms"][0]["quote_id"] == qid


def test_reference_rates():
    out = tools.rates_get_reference()
    assert out["as_of"] == "2026-10-01"
    f = ids(out)
    assert f["ref.fd_rate"]["value"] == 0.07 and f["ref.fd_rate"]["unit"] == "fraction"
    assert "assumption" in f["ref.inflation"]["label"]


def test_stocks():
    hist = tools.stocks_get_history("zephyrx")
    assert hist["found"] and len(hist["rows"]) == 120
    f = ids(tools.stocks_tip_signals("ZEPHYRX"))
    assert f["pump_risk"]["value_text"] == "high"
    assert f["run_up_30d"]["value"] > 0.5
    assert tools.stocks_tip_signals("NOPE") == {"symbol": "NOPE", "found": False, "facts": []}
    assert tools.stocks_get_history("../../etc/passwd")["found"] is False


def test_calculators_match_phase2_golden():
    assert ids(tools.calc_endowment_return(50_000, 15, 10_20_000, 15))["endowment_return"]["value"] == pytest.approx(
        0.038, abs=0.002
    )
    assert ids(tools.calc_fd_value(50_000, 15, 0.07))["fd_value"]["value"] == pytest.approx(13.44e5, abs=5e3)
    loan = ids(tools.calc_flat_to_effective(1_00_000, 0.12, 24))
    assert loan["loan_emi"]["value"] == pytest.approx(5166.67)
    assert loan["loan_effective_rate"]["value"] == pytest.approx(0.216, abs=0.003)
    assert ids(tools.calc_irr([[0, -100], [1, 110]]))["irr"]["value"] == pytest.approx(0.1)
    assert ids(tools.calc_sip_value(5_000, 120, 0.12))["sip_value"]["value"] > 11e5


def test_affordability_from_family(demo_repo):
    f = ids(tools.calc_affordability(new_monthly_cost=50_000 / 12, family_id=1, repo=demo_repo))
    outgo = 28_000 + 2_400 + 1_000 + 50_000 / 12  # expenses + scooter EMI + policy 12,000/12 + new premium
    assert f["buffer_months_after"]["value"] == pytest.approx(1_60_000 / outgo, abs=0.01)
    assert f["surplus_after"]["value"] == pytest.approx(45_000 - outgo, abs=0.01)
    assert f["emi_share"]["value"] == pytest.approx((2_400 + 50_000 / 12) / 45_000, abs=1e-4)
    # unknown stays unknown
    assert (
        ids(tools.calc_affordability(new_monthly_cost=1_000, family_id=99, repo=demo_repo))["surplus_after"]["status"]
        == "unknown"
    )


def test_tool_facts_work_with_evidence_checker(demo_repo):
    facts = [Fact.model_validate(x) for x in tools.calc_fd_value(50_000, 15, 0.07)["facts"]]
    facts += [Fact.model_validate(x) for x in tools.family_get_profile(1, demo_repo)["facts"]]
    assert check_argument("An FD would give 13.4 lakh.", ["fd_value"], facts, {}).kept
    assert check_argument("You have 1,60,000 saved.", ["profile.savings"], facts, {}).kept
    assert not check_argument("You have 1,60,000 saved.", ["fd_value"], facts, {}).kept
