import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.main import app
from app.pipeline.profile_extract import extract_profile
from tests.fakes import FakeSTT


@pytest.fixture
def client(demo_repo):
    app.dependency_overrides[deps.get_repo] = lambda: demo_repo
    app.dependency_overrides[deps.get_stt_provider] = lambda: FakeSTT("My salary is 52,000 a month.")
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_get_profile(client):
    body = client.get("/families/1/profile").json()
    vals = {v["field"]: v for v in body["values"]}
    assert vals["monthly_income"]["value"] == 45_000 and vals["savings"]["source"] == "document"
    assert [m["name"] for m in body["members"]] == ["Lakshmi", "Arun"]
    assert client.get("/families/9/profile").status_code == 404


def test_extract_does_not_save_then_confirm_saves_only_confirmed(client):
    prop = client.post(
        "/families/1/profile/extract",
        data={"text": "My income is 50,000. We spend 30,000 a month. Scooter loan EMI 2,400."},
    ).json()
    assert {(v["field"], v["value"]) for v in prop["values"]} == {
        ("monthly_income", 50_000),
        ("monthly_expenses", 30_000),
    }
    assert prop["items"][0]["kind"] == "loan" and "Is that right?" in prop["items"][0]["readback"]
    assert client.get("/families/1/profile").json()["values"][0]["value"] == 45_000  # nothing saved yet

    income, expenses = sorted(prop["values"], key=lambda v: v["field"])[::-1]
    body = {"values": [income | {"confirmed": True}, expenses | {"confirmed": False}], "items": []}
    out = client.post("/families/1/profile/confirm", json=body).json()
    assert out["saved"] == ["monthly_income"] and out["skipped"] == ["monthly_expenses"]
    vals = {v["field"]: v for v in client.get("/families/1/profile").json()["values"]}
    assert vals["monthly_income"]["value"] == 50_000 and vals["monthly_income"]["source"] == "typed"
    assert vals["monthly_expenses"]["value"] == 28_000


def test_extract_onboarding_field_and_voice(client):
    prop = client.post("/families/1/profile/extract", data={"field": "savings", "text": "about 2 lakh"}).json()
    assert prop["values"][0]["field"] == "savings" and prop["values"][0]["value"] == 200_000
    voice = client.post("/families/1/profile/extract", files={"audio": ("a.m4a", b"x", "audio/mp4")}).json()
    assert voice["values"][0]["source"] == "voice" and voice["values"][0]["value"] == 52_000
    assert voice["values"][0]["readback"] == "I heard ₹52,000 a month for your income each month. Is that right?"


def test_set_profile_requires_confirmed(client):
    body = {"field": "savings", "value": 1, "source": "typed", "confirmed": False}
    assert client.post("/families/1/profile", json=body).status_code == 422


def test_items_crud(client):
    item = {"kind": "chit", "name": "Chit", "amount": 5_000, "frequency": "monthly", "source": "voice"}
    assert client.post("/families/1/items", json={"item": item, "confirmed": False}).status_code == 422
    saved = client.post("/families/1/items", json={"item": item, "confirmed": True}).json()
    assert saved["saved"]
    assert len(client.get("/families/1/items", params={"kind": "chit"}).json()["items"]) == 1
    assert client.delete(f"/families/1/items/{saved['item_id']}").json() == {"deleted": True}
    assert client.delete(f"/families/1/items/{saved['item_id']}").status_code == 404


def test_alerts(client, demo_repo):
    cid = demo_repo.create_case(1, case_type="loan_offer")
    demo_repo.save_verdict(cid, "red", sentence="Do not take this loan.")
    aid = demo_repo.create_alert(cid, 1, "RED: loan")
    alerts = client.get("/families/1/alerts").json()
    assert alerts[0]["colour"] == "red" and alerts[0]["case_type"] == "loan_offer"
    assert client.patch(f"/alerts/{aid}", json={"status": "handled", "note": "Called Amma"}).json() == {"updated": True}
    assert client.get("/families/1/alerts", params={"status": "new"}).json() == []
    assert client.patch("/alerts/999", json={"status": "handled"}).status_code == 404


def test_guardian_note_reaches_amma(client, demo_repo):
    cid = demo_repo.create_case(1)
    aid = demo_repo.create_alert(cid, 1, "RED: loan offer: do not sign")
    assert client.patch(f"/v1/alerts/{aid}", json={"note": "Wait for me, I will call."}).status_code == 200
    alert = client.get("/v1/families/1/alerts").json()[0]
    assert alert["note"] == "RED: loan offer: do not sign" and alert["guardian_note"] == "Wait for me, I will call."
    notes = client.get("/v1/families/1/notes").json()
    assert notes[0]["note"] == "Wait for me, I will call." and notes[0]["from"] == "Arun"


# ---------------------------------------------------------------- what a sentence or a paper proposes
@pytest.mark.parametrize(
    "text",
    ["LIC premium 12,000 a year.", "Health policy Rs 12,000 a year.", "Premium on my loan policy Rs 12,000 yearly."],
)
def test_premium_is_always_a_policy(text):
    (item,) = extract_profile(text, "typed").items
    assert (item.kind, item.amount, item.frequency) == ("policy", 12000, "yearly")


@pytest.mark.parametrize(
    "text", ["Gold loan EMI 2,400 a month.", "My emi is 2400.", "Two loans cost Rs 2,400 monthly."]
)
def test_loan_words_are_whole_words(text):
    (item,) = extract_profile(text, "typed").items
    assert (item.kind, item.amount, item.frequency) == ("loan", 2400, "monthly")


@pytest.mark.parametrize(
    "text", ["Net salary: Rs. 36,400.", "Net salary Rs 36,400.", "Net salary ₹36,400.", "Salary Rs.36400/-"]
)
def test_all_rupee_spellings_parse(text):
    (value,) = extract_profile(text, "typed").values
    assert (value.field, value.value, value.uncertain) == ("monthly_income", 36400, False)


@pytest.mark.parametrize(
    ("text", "amount"),
    [
        ("Salary for October 2026 Rs 36,400.", 36400),
        ("Salary paid on 01/10/2026 Rs 36,400.", 36400),
        ("Salary paid 31 Oct 2026 was 36,400.", 36400),
        ("Salary since 2019 is 36,400.", 36400),
        ("I spend 2000 a month.", 2000),
    ],
)
def test_dates_are_not_amounts(text, amount):
    assert [v.value for v in extract_profile(text, "typed").values] == [amount]


def test_a_date_alone_proposes_nothing():
    prop = extract_profile("Salary slip for October 2026", "document")
    assert not prop.values and not prop.items


def test_a_line_ends_a_sentence():
    prop = extract_profile("Sunrise Traders\nNet salary Rs 36,400\nBank balance Rs 1,60,000", "document")
    assert [(v.field, v.value) for v in prop.values] == [("monthly_income", 36400), ("savings", 160000)]


def test_paper_text_stays_out_of_the_proposal():
    text = "Private note about the family.\nHolder PAN ABCDE1234F salary Rs 36,400."
    prop = extract_profile(text, "document", source_ref="slip.pdf")
    assert prop.heard == ""
    assert prop.values[0].quote == "Holder PAN [removed] salary Rs 36,400."


def test_typed_text_is_still_read_back():
    assert extract_profile("My pension is 45,000 a month.", "typed").heard == "My pension is 45,000 a month."
