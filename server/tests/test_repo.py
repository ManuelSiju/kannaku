import pytest

from app.db.repo import REDACTED, FamilyItem, NotConfirmed, strip_ids
from app.engines.finance import fd_value


@pytest.mark.parametrize(
    "text,secret",
    [
        ("Aadhaar 2345 6789 0123", "6789"),
        ("aadhaar no 234567890123", "234567890123"),
        ("PAN ABCDE1234F", "ABCDE1234F"),
        ("A/c 001234567890123", "001234567890123"),
        ("acct 123456789", "123456789"),
    ],
)
def test_strip_ids_removes_identity_numbers(text, secret):
    out = strip_ids(text)
    assert REDACTED in out and secret not in out


@pytest.mark.parametrize("text", ["Rs. 10,20,000 at maturity", "premium 50,000 for 15 years", "call 2,400 EMI"])
def test_strip_ids_keeps_amounts(text):
    assert strip_ids(text) == text


def test_profile_unknown_means_no_row(repo):
    fam = repo.create_family()
    m = repo.add_member(fam, "Test", "primary")
    repo.set_profile_value(m, "monthly_income", 30_000, "typed", confirmed=True)
    assert [pv.field for pv in repo.profile_values(fam)] == ["monthly_income"]


def test_profile_requires_confirmation_and_upserts(repo):
    fam = repo.create_family()
    m = repo.add_member(fam, "Test", "primary")
    with pytest.raises(NotConfirmed):
        repo.set_profile_value(m, "savings", 1, "voice", confirmed=False)
    repo.set_profile_value(m, "savings", 100, "voice", confirmed=True)
    repo.set_profile_value(m, "savings", 200, "document", source_ref="passbook", confirmed=True)
    (pv,) = repo.profile_values(fam)
    assert pv.value == 200 and pv.source == "document" and pv.source_ref == "passbook"


def test_items_save_list_delete(repo):
    fam = repo.create_family()
    item = FamilyItem(kind="loan", name="Bike loan", amount=2_000, frequency="monthly", source="typed")
    with pytest.raises(NotConfirmed):
        repo.save_item(fam, item, confirmed=False)
    iid = repo.save_item(fam, item, confirmed=True)
    assert [i.name for i in repo.list_items(fam, "loan")] == ["Bike loan"]
    assert repo.list_items(fam, "policy") == []
    assert repo.delete_item(fam, iid) and repo.list_items(fam) == []


def test_case_round_trip(repo):
    fam = repo.create_family()
    cid = repo.create_case(fam, case_type="insurance_offer", transcript="My PAN is ABCDE1234F, is this plan good?")
    assert "ABCDE1234F" not in repo.get_case(cid)["transcript"]
    qid = repo.add_evidence(cid, "page_3", "Bonus rates are not guaranteed and may change every year.")
    assert qid.startswith("q")
    repo.add_term(cid, "premium", 50_000, "INR", evidence_id=int(qid[1:]), verified=True)
    repo.save_facts(cid, [fd_value(50_000, 15, 0.07)])
    repo.save_facts(cid, [fd_value(50_000, 15, 0.07)])  # upsert, no duplicate
    repo.add_position(cid, "dani", "against", 0.9)
    repo.add_argument(cid, "dani", "FD gives 13.4 lakh.", ["fd_value"], True)
    repo.add_argument(cid, "dani", "It gives 9%.", ["fd_value"], False, drop_reason="number '9%' not supported")
    repo.save_verdict(cid, "red", score=-0.9, sentence="Do not sign yet.", questions=["Is the bonus guaranteed?"])
    repo.add_spoken_line(cid, "alfii", 1, "Let me ask the team.")
    repo.add_trace(cid, "case_builder", 812.5, "ok", {"tokens": 120})
    aid = repo.create_alert(cid, fam, "Red verdict on insurance offer")

    b = repo.case_bundle(cid)
    assert b["quotes"][0]["id"] == qid
    assert b["terms"][0]["quote_id"] == qid and b["terms"][0]["verified"] is True
    assert [f["id"] for f in b["facts"]] == ["fd_value"]
    assert b["facts"][0]["value"] == pytest.approx(13_44_402.68, abs=0.01)
    assert [a["kept"] for a in b["arguments"]] == [1, 0]
    assert b["arguments"][1]["cited_ids"] == ["fd_value"]
    assert b["verdict"]["colour"] == "red" and b["verdict"]["questions"] == ["Is the bonus guaranteed?"]
    assert b["trace"][0]["detail"] == {"tokens": 120}
    assert repo.update_alert(aid, status="handled", note="Called Amma")
    assert repo.list_alerts(fam, "handled")[0]["note"] == "Called Amma"


def test_facts_round_trip_unchanged(repo):
    from app.engines.finance import affordability

    fam = repo.create_family()
    cid = repo.create_case(fam)
    facts = affordability(45_000, None, 1_60_000, 2_400, 4_000, regular_commitments=1_000)
    repo.save_facts(cid, facts)
    assert repo.get_facts(cid) == facts
