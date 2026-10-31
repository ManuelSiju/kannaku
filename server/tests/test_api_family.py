import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.main import app
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
